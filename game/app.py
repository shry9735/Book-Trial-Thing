#!/usr/bin/env python3
"""
app.py — Ignite Academy game server.

Three account roles:

    student  → classroom → lessons → quiz → trinkets
    parent   → plain-language progress, no digging required
    teacher  → same view as parent, plus group management

State lives in Postgres (see db.py).  Configuration comes from the
environment (see config.py).  Nothing durable is written to local disk,
so the process is disposable and can be run N-up behind a load balancer.

Usage:
    pip install -r ../requirements.txt
    export DATABASE_URL=postgresql://ignite:ignite@localhost:5432/ignite
    python app.py                     # development server
    python app.py --migrate-only      # apply schema, then exit
    gunicorn -c ../gunicorn.conf.py wsgi:app     # production

See ../DEPLOY.md for a real deployment.

──────────────────────────────────────────────────────
ORGANISATIONS ARE THE PRIVACY BOUNDARY
──────────────────────────────────────────────────────
Every account belongs to exactly one organisation.  A teacher sees the
students in their own organisation; a parent sees only the children
linked to them by link code.  No screen ever enumerates across that line
— see db.visible_students(), which is the single place the rule lives.

Signing up as a teacher creates an organisation and a join code.
Students and parents join an existing one with that code.

──────────────────────────────────────────────────────
LESSONS ARE SELF-CONTAINED PACKAGES
──────────────────────────────────────────────────────
Every lesson is one folder under lessons/.  Drop a folder in, it appears
in the game — nothing to register.

    lessons/circuits-03/
    ├── lesson.json      manifest: title, quiz, reward
    ├── index.html       the lesson itself (interactive types)
    └── anything else    its own js/css/assets, namespaced to this folder

Interactive lessons render in an IFRAME.  That is deliberate and is the
whole isolation strategy: each lesson gets its own JavaScript context,
its own global scope and its own CSS scope, enforced by the browser.  A
lesson can define `window.player`, throw on load, or capture every key
event, and no other lesson can observe it.  There is no shared bundle to
break and no load order to get wrong.

The catalog is read from disk once and cached — see load_lessons().  It
used to be re-scanned and re-parsed on every single request, including
once per answered quiz question.

──────────────────────────────────────────────────────
GRAPHICS ARE SHARED, CODE IS NOT
──────────────────────────────────────────────────────
Isolated code would normally mean duplicated art.  It doesn't here,
because art lives in one namespace any lesson can reach:

    /art/<name>        e.g. <img src="/art/characters/spark">

That route resolves the extension server-side (.webp .png .jpg .gif .svg)
and falls back to a labelled placeholder.  Lessons never hardcode a file
path, so re-exporting spark.png as spark.webp updates every lesson at
once.  Pair it with static/kit/lesson-kit.css for shared fonts, colours,
buttons and panels — visual consistency without shared JavaScript.

──────────────────────────────────────────────────────
BOOK ↔ WEB CROSSOVER
──────────────────────────────────────────────────────
Reading lessons keep their prose in content/ as Markdown, which is valid
make_epub.py input.  One source file serves the game, the EPUB and the
RAG index:

    python ../make_epub.py content/ -t "Ignite Academy" -o ignite.epub
"""

from __future__ import annotations

import argparse
import functools
import json
import logging
import os
import random
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from flask import (
        Flask, abort, flash, g, jsonify, redirect, render_template,
        request, send_from_directory, session, url_for,
    )
    from werkzeug.exceptions import HTTPException
    from werkzeug.security import check_password_hash, generate_password_hash
    import psycopg
except ImportError as exc:
    sys.exit(f"Missing dependency ({exc.name}): run  pip install -r ../requirements.txt")

import billing
import db
import emailer
import security
from config import validate as load_config
from logsetup import configure_logging


BASE_DIR    = Path(__file__).parent
ART_DIR     = BASE_DIR / "static" / "art"
LESSONS_DIR = BASE_DIR / "lessons"    # one folder per lesson
CONTENT_DIR = BASE_DIR / "content"    # Markdown prose — also make_epub.py input
DATA_DIR    = BASE_DIR / "data"       # content only: item and classroom catalogs

ITEMS_FILE     = DATA_DIR / "items.json"
CLASSROOM_FILE = DATA_DIR / "classroom.json"

ART_EXTS = (".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg")

# Flash-style fixed stage.  Everything scales to fit the viewport.
STAGE_W = 960
STAGE_H = 600

# A student is "quiet" after this many days with no activity
QUIET_DAYS = 5

log = logging.getLogger("ignite.app")

cfg = load_config()
configure_logging(cfg)

app = Flask(__name__)
app.secret_key = cfg.SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,          # JavaScript can never read it
    SESSION_COOKIE_SECURE=cfg.COOKIE_SECURE,
    # Lax, not Strict: a student clicking the emailed verification link
    # should land signed in.  Lax still withholds the cookie from every
    # cross-site POST, which is what CSRF needs.
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_NAME="ignite_session",
    PERMANENT_SESSION_LIFETIME=timedelta(days=cfg.SESSION_DAYS),
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,    # no request body needs to be bigger
    SEND_FILE_MAX_AGE_DEFAULT=cfg.STATIC_MAX_AGE,
    JSON_SORT_KEYS=False,
    TRAP_HTTP_EXCEPTIONS=False,
)


# ── Read-only content catalogs (files, not state) ───────────────────────────────
#
# Lessons, items and the classroom layout are content: they ship with the
# code and change on deploy, not at runtime.  They are read once and held
# in memory behind a lock, because the previous version re-scanned the
# lessons directory and re-parsed every manifest on every request — once
# per answered quiz question, among others.

_catalog_lock = threading.Lock()
_catalog: dict[str, object] = {}


def _read_json_file(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        log.exception("could not parse %s, using default", path.name)
        return default


def _build_lessons() -> list[dict]:
    """
    Scan lessons/*/lesson.json.  The folder name is the lesson id, so
    adding a lesson is dropping a folder in — nothing to register.

    Sorted by the manifest's "order" field, then by id.
    """
    found: list[dict] = []
    if not LESSONS_DIR.is_dir():
        return found

    for folder in sorted(LESSONS_DIR.iterdir()):
        manifest = folder / "lesson.json"
        if not folder.is_dir() or not manifest.is_file():
            continue
        data = _read_json_file(manifest, None)
        if not isinstance(data, dict):
            log.warning("skipping %s — unreadable lesson.json", folder.name)
            continue
        data["id"] = folder.name
        data.setdefault("title",    folder.name)
        data.setdefault("subject",  "General")
        data.setdefault("type",     "interactive")
        data.setdefault("order",    999)
        data.setdefault("quiz",     [])
        data.setdefault("examples", [])
        data.setdefault("thumb",    f"lessons/{folder.name}")
        # Resolved once here rather than in each template: "access" carries
        # the back-compat with the older "free" boolean, and "kit" gets
        # normalised from either `true` or an object.
        data["access"] = billing.lesson_access(data)
        data["kit"] = billing.lesson_kit(data)
        found.append(data)

    return sorted(found, key=lambda l: (l["order"], l["id"]))


def refresh_catalog() -> None:
    """Re-read every content file.  Called at boot and by --reload-catalog."""
    lessons = _build_lessons()
    with _catalog_lock:
        _catalog["lessons"] = lessons
        _catalog["by_id"] = {l["id"]: l for l in lessons}
        _catalog["question_counts"] = {l["id"]: len(l.get("quiz", [])) for l in lessons}
        # Two parallel lists of every (lesson, question) pair still in the
        # catalog.  Postgres unnests them to filter answers to questions
        # that actually exist — see db.unresolved_counts().
        pairs = [(l["id"], q["id"]) for l in lessons for q in l.get("quiz", [])]
        _catalog["valid_pairs"] = ([p[0] for p in pairs], [p[1] for p in pairs])
        _catalog["items"] = _read_json_file(ITEMS_FILE, {})
        _catalog["classroom"] = _read_json_file(
            CLASSROOM_FILE, {"background": "backgrounds/classroom", "hotspots": []})


def load_lessons() -> list[dict]:
    return _catalog["lessons"]


def get_lesson(lesson_id: str) -> dict | None:
    return _catalog["by_id"].get(lesson_id)


def load_items() -> dict:
    return _catalog["items"]


def load_classroom() -> dict:
    return _catalog["classroom"]


def assigned_lessons(student_id: int, catalog: list[dict]) -> list[dict]:
    """
    A teacher or parent can narrow a student's lesson menu (see
    /grownup/student/<username>/assign).  No assignment row means nothing
    has been restricted yet, so everything is available.
    """
    assigned = db.assigned_lesson_ids(student_id)
    if assigned is None:
        return catalog
    allowed = set(assigned)
    return [l for l in catalog if l["id"] in allowed]


# ── Static asset routes ─────────────────────────────────────────────────────────

def _cached(response):
    """Content-addressed enough for a long max-age; it only changes on deploy."""
    response.headers["Cache-Control"] = f"public, max-age={cfg.STATIC_MAX_AGE}"
    return response


@app.route("/kit/<path:filename>")
def kit_asset(filename: str):
    """
    Short, stable URL for the shared lesson kit, so every lesson writes
    the same two lines regardless of where it lives:

        <link rel="stylesheet" href="/kit/lesson-kit.css">
        <script src="/kit/lesson-kit.js"></script>
    """
    return _cached(send_from_directory(BASE_DIR / "static" / "kit", filename))


@app.route("/lessons/<lesson_id>/<path:filename>")
def lesson_asset(lesson_id: str, filename: str):
    """
    Serve a lesson package's own files.  Each lesson is sandboxed to its
    own folder, so one lesson cannot reach into another's assets.
    """
    if not get_lesson(lesson_id):
        abort(404)
    return _cached(send_from_directory(LESSONS_DIR / lesson_id, filename))


def find_art(name: str) -> str | None:
    for ext in ART_EXTS:
        if (ART_DIR / f"{name}{ext}").is_file():
            return f"art/{name}{ext}"
    return None


def static_url(filename: str) -> str:
    """Route static files through the CDN when one is configured."""
    if cfg.CDN_URL:
        return f"{cfg.CDN_URL}/static/{filename}"
    return url_for("static", filename=filename)


def art(name: str) -> str:
    found = find_art(name)
    if found:
        return static_url(found)
    return url_for("art_placeholder", name=name)


def art_exists(name: str) -> bool:
    return find_art(name) is not None


def media(source: str) -> str:
    if source.startswith(("http://", "https://", "//", "/")):
        return source
    return art(source)


app.jinja_env.globals.update(
    art=art, art_exists=art_exists, media=media, static_url=static_url,
    csrf_token=security.csrf_token,
    STAGE_W=STAGE_W, STAGE_H=STAGE_H,
)


@app.route("/art/<path:name>")
def art_url(name: str):
    """
    Stable art URL for lesson packages: <img src="/art/characters/spark">

    Resolves the extension server-side, so lessons never hardcode one.
    Re-exporting a .png as .webp updates every lesson that references it
    without touching a single lesson's code.
    """
    found = find_art(name)
    if found:
        return redirect(static_url(found))
    return redirect(url_for("art_placeholder", name=name))


@app.route("/art-placeholder/<path:name>")
def art_placeholder(name: str):
    """
    SVG placeholder naming the exact file path to create.

    Built server-side, so it cannot read the CSS custom properties. These
    literals have to be kept in step with static/kit/brand.css by hand —
    they are the only brand colours in the codebase that a re-skin will
    not reach on its own.
    """
    label = f"static/art/{name}.png"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500">
  <defs>
    <pattern id="p" width="40" height="40" patternUnits="userSpaceOnUse">
      <rect width="40" height="40" fill="#fdf1f7"/>
      <path d="M0 40 L40 0" stroke="#f6d0e5" stroke-width="2"/>
    </pattern>
  </defs>
  <rect width="800" height="500" fill="url(#p)"/>
  <rect x="10" y="10" width="780" height="480" fill="none"
        stroke="#d81b84" stroke-width="4" stroke-dasharray="14 10" rx="8"/>
  <text x="400" y="228" text-anchor="middle"
        font-family="Trebuchet MS, Verdana, sans-serif" font-size="30"
        font-weight="bold" fill="#d81b84">Drop a graphic here</text>
  <text x="400" y="278" text-anchor="middle"
        font-family="Consolas, Menlo, monospace" font-size="21" fill="#444c56">{label}</text>
  <text x="400" y="316" text-anchor="middle"
        font-family="Trebuchet MS, Verdana, sans-serif" font-size="15" fill="#6b7684">
    .webp .png .jpg .gif or .svg — any of these work
  </text>
</svg>"""
    response = app.response_class(svg, mimetype="image/svg+xml")
    return _cached(response)


# ── Reading content (shared with make_epub.py) ──────────────────────────────────

def render_content(source: str) -> str:
    """Render a content/ file to HTML.  Same file is make_epub.py input."""
    path = CONTENT_DIR / source
    try:
        path.resolve().relative_to(CONTENT_DIR.resolve())
    except ValueError:
        return "<p>Invalid content path.</p>"

    if not path.is_file():
        return (f'<p class="content-missing">No content file yet — create '
                f'<code>game/content/{source}</code>.</p>')

    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in (".html", ".htm"):
        return raw
    try:
        import markdown
    except ImportError:
        return f"<pre>{raw}</pre>"
    return markdown.markdown(raw, extensions=["extra", "tables"])


# ── Request lifecycle ───────────────────────────────────────────────────────────

@app.before_request
def _guard():
    # Hand the resolved view over so a route can declare itself exempt,
    # rather than the check guessing from the URL.
    security.check_csrf(app.view_functions.get(request.endpoint or ""))


@app.after_request
def _headers(response):
    return security.apply_headers(response, cfg)


@app.teardown_appcontext
def _teardown(exception=None):
    g.pop("_user", None)
    g.pop("_entitlement", None)


@app.route("/healthz")
def healthz():
    """
    Liveness plus readiness.  A load balancer that only checks whether the
    port answers will happily route traffic to a process that has lost its
    database, so this actually round-trips a query.
    """
    ok = db.healthy()
    return jsonify({"status": "ok" if ok else "degraded", "database": ok}), (200 if ok else 503)


# ── Auth ────────────────────────────────────────────────────────────────────────

def current_user() -> dict | None:
    """
    The signed-in account, or None.

    The session carries the user id and the session epoch it was issued
    under.  Changing a password bumps the epoch in the database, which
    retroactively invalidates every cookie issued before it — so a
    password reset actually kicks an attacker out instead of leaving their
    stolen cookie valid for a fortnight.
    """
    if "_user" in g:
        return g._user

    g._user = None
    uid = session.get("uid")
    if uid:
        try:
            user = db.user_by_id(uid)
        except Exception:
            log.exception("could not load session user")
            return None
        if user and user["session_epoch"] == session.get("epoch"):
            g._user = user
        else:
            session.clear()
    return g._user


def start_session(user: dict) -> None:
    session.clear()
    session["uid"] = user["id"]
    session["epoch"] = user["session_epoch"]
    session.permanent = True
    security.rotate_csrf_token()


def login_required(*roles: str):
    """Require a session, and optionally membership of one of `roles`."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*fargs, **fkwargs):
            user = current_user()
            if not user:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Not signed in."}), 401
                return redirect(url_for("login", next=request.full_path.rstrip("?")))
            if roles and user["role"] not in roles:
                return redirect(url_for("home"))
            return fn(*fargs, **fkwargs)
        return wrapper
    return decorator


def membership_required(fn):
    """
    Hold a pending member at the door.

    They have a real account and can sign in — they just cannot reach any
    classroom until an org admin lets them through. Bouncing them to a
    holding page rather than a 403 keeps it obvious that nothing is broken.
    """
    @functools.wraps(fn)
    def wrapper(*fargs, **fkwargs):
        user = current_user()
        if user and user["membership_status"] == "pending":
            if request.path.startswith("/api/"):
                return jsonify({"error": "Your place hasn't been approved yet."}), 403
            return redirect(url_for("pending"))
        return fn(*fargs, **fkwargs)
    return wrapper


def org_admin_required(fn):
    """Admin teachers only: the roster and the money."""
    @functools.wraps(fn)
    def wrapper(*fargs, **fkwargs):
        user = current_user()
        if not user:
            return redirect(url_for("login", next=request.path))
        if user["role"] != "teacher" or not user["org_admin"]:
            abort(404)
        return fn(*fargs, **fkwargs)
    return wrapper


def entitlement() -> dict:
    """This request's entitlement, resolved once and cached on g."""
    if "_entitlement" not in g:
        user = current_user()
        g._entitlement = billing.entitlement_for(cfg, user) if user else billing.NO_ENTITLEMENT
    return g._entitlement


@app.route("/pending")
@login_required()
def pending():
    user = current_user()
    if user["membership_status"] != "pending":
        return redirect(url_for("home"))
    return render_template("pending.html", org=db.org_by_id(user["org_id"]))


@app.context_processor
def inject_user():
    user = current_user()
    return {
        "user": user,
        "config": cfg,
        "entitlement": entitlement() if user else billing.NO_ENTITLEMENT,
        "billing_enabled": billing.enabled(cfg),
        "store_url": cfg.STORE_URL,
    }


@app.route("/")
def home():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if user["role"] in ("teacher", "parent"):
        return redirect(url_for("grownup_home"))
    return redirect(url_for("classroom"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method != "POST":
        if current_user():
            return redirect(url_for("home"))
        return render_template("login.html", role_tab=request.args.get("role", "student"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role_tab = request.form.get("role_tab", "student")
    ip = security.client_ip(cfg.TRUSTED_PROXIES)

    def refuse(message: str, status: int = 200):
        flash(message, "error")
        return render_template("login.html", role_tab=role_tab, username=username), status

    # Two independent buckets: one stops a single account being ground
    # down, the other stops one host spraying many accounts.
    if (security.over_limit("login_user", username, cfg.RL_LOGIN_USER, cfg.RL_WINDOW)
            or security.over_limit("login_ip", ip, cfg.RL_LOGIN_IP, cfg.RL_WINDOW)):
        log.warning("login rate limited", extra={"username": username})
        return refuse("Too many attempts. Wait a few minutes and try again.", 429)

    user = db.user_by_username(username)

    # The password is checked even when the username is unknown, against a
    # throwaway hash, so a wrong username and a wrong password take the
    # same time and the response cannot be used to enumerate accounts.
    stored = user["password_hash"] if user else _DUMMY_HASH
    ok = check_password_hash(stored, password)

    if not user or not ok:
        security.record_attempt("login_user", username)
        security.record_attempt("login_ip", ip)
        log.info("login failed", extra={"username": username})
        return refuse("That username and password don't match.")

    if cfg.REQUIRE_EMAIL_VERIFICATION and not user["email_verified"]:
        return refuse("Confirm your email address first — check your inbox "
                      "for the link, or request a new one below.")

    security.clear_attempts("login_user", username)
    start_session(user)
    db.touch_login(user["id"])
    log.info("login ok", extra={"username": user["username"], "role": user["role"]})
    return redirect(security.safe_next(request.args.get("next"), url_for("home")))


# Compared against when the username does not exist, purely so the timing
# of a failed login does not reveal which of the two was wrong.
_DUMMY_HASH = generate_password_hash("timing-equalizer-not-a-real-password")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Signup ──────────────────────────────────────────────────────────────────────

@app.route("/signup", methods=["GET", "POST"])
def signup():
    """
    Self-serve registration for all three roles.

    A teacher signing up creates an organisation and receives its join
    code.  Students and parents must present that code, so an account
    cannot appear inside a school nobody invited it to.
    """
    role = (request.values.get("role") or "student").strip().lower()
    if role not in ("student", "parent", "teacher"):
        role = "student"

    if request.method != "POST":
        if current_user():
            return redirect(url_for("home"))
        return render_template("signup.html", role=role, form={})

    form = {k: request.form.get(k, "").strip() for k in
            ("name", "username", "email", "join_code", "org_name")}
    password = request.form.get("password", "")
    confirm = request.form.get("password_confirm", "")
    ip = security.client_ip(cfg.TRUSTED_PROXIES)

    def refuse(message: str, status: int = 200):
        flash(message, "error")
        return render_template("signup.html", role=role, form=form), status

    if security.over_limit("signup_ip", ip, cfg.RL_SIGNUP_IP, cfg.RL_WINDOW):
        return refuse("Too many sign-ups from this connection. Try again later.", 429)

    if not form["name"]:
        return refuse("Enter the name you'd like shown.")
    for problem in (security.username_problem(form["username"]),
                    security.email_problem(form["email"]),
                    security.password_problem(password, confirm)):
        if problem:
            return refuse(problem)

    # The age gate. Under 13, US COPPA applies to a service collecting
    # this kind of data and this app is not built to meet it — see
    # DEPLOY.md. The attestation and its timestamp are what we keep.
    if role == "student" and not request.form.get("age_ok"):
        return refuse(f"Confirm you are {cfg.MIN_AGE} or older to create a student account.")
    if not request.form.get("terms_ok"):
        return refuse("Accept the terms to continue.")

    if role == "teacher":
        if not form["org_name"]:
            return refuse("Name your school, club or class.")
        org = None
    else:
        org = db.org_by_join_code(form["join_code"])
        if not org:
            return refuse("That join code doesn't match any class. Check it with your teacher.")

    # Checked up front for a friendly message; the unique indexes below are
    # what actually prevent a duplicate when two people race.
    if db.username_taken(form["username"]):
        return refuse("That username is taken.")
    if db.email_taken(form["email"]):
        return refuse("There's already an account with that email. Try signing in.")

    verified = not cfg.REQUIRE_EMAIL_VERIFICATION
    # On an approval-gated org, a correct join code buys a place in the
    # queue rather than a seat. The teacher who creates an org is always
    # its first admin.
    membership = "active"
    if role != "teacher" and org.get("join_policy") == "approval":
        membership = "pending"

    try:
        with db.write() as cur:
            if role == "teacher":
                org = db.create_org(cur, form["org_name"])
            user = db.create_user(
                cur,
                org_id=org["id"],
                username=form["username"],
                email=form["email"],
                password_hash=generate_password_hash(password),
                role=role,
                name=form["name"],
                avatar=f"characters/avatar-{role}",
                email_verified=verified,
                age_confirmed=(role == "student"),
                terms_accepted=True,
                org_admin=(role == "teacher"),
                membership_status=membership,
            )
            raw_token, token_hash = security.new_token()
            db.store_token(cur, token_hash, user["id"], "verify", cfg.TOKEN_HOURS)
    except psycopg.errors.UniqueViolation:
        return refuse("That username or email was just taken. Try another.")

    security.record_attempt("signup_ip", ip)
    emailer.send_verification(
        cfg, form["email"], form["name"],
        f"{cfg.BASE_URL}{url_for('verify_email', token=raw_token)}")
    log.info("signup", extra={"username": user["username"], "role": role, "org_id": org["id"]})

    if role == "teacher":
        flash(f"Class created. Your join code is {org['join_code']} — "
              "students and parents need it to sign up.", "success")
    elif membership == "pending":
        flash("Account created. A teacher has to let you in before you can "
              "start — you'll be able to sign in once they do.", "success")

    if cfg.REQUIRE_EMAIL_VERIFICATION:
        flash("Check your email for a confirmation link.", "success")
        return redirect(url_for("login", role=role))

    start_session(user)
    return redirect(url_for("home"))


@app.route("/verify/<token>")
def verify_email(token: str):
    user = db.consume_token(security.hash_token(token), "verify")
    if not user:
        flash("That confirmation link has expired or already been used.", "error")
        return redirect(url_for("login"))

    with db.write() as cur:
        db.mark_verified(cur, user["id"])

    start_session(user)
    flash("Email confirmed — you're all set.", "success")
    return redirect(url_for("home"))


@app.route("/verify/resend", methods=["POST"])
def resend_verification():
    email = request.form.get("email", "").strip()
    ip = security.client_ip(cfg.TRUSTED_PROXIES)

    if not security.over_limit("resend_ip", ip, cfg.RL_RESET_IP, cfg.RL_WINDOW):
        security.record_attempt("resend_ip", ip)
        user = db.user_by_email(email)
        if user and not user["email_verified"]:
            with db.write() as cur:
                db.invalidate_tokens(cur, user["id"], "verify")
                raw_token, token_hash = security.new_token()
                db.store_token(cur, token_hash, user["id"], "verify", cfg.TOKEN_HOURS)
            emailer.send_verification(
                cfg, user["email"], user["name"],
                f"{cfg.BASE_URL}{url_for('verify_email', token=raw_token)}")

    # Same answer either way — see forgot_password().
    flash("If that address needs confirming, a new link is on its way.", "success")
    return redirect(url_for("login"))


# ── Password reset ──────────────────────────────────────────────────────────────

@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method != "POST":
        return render_template("forgot.html")

    email = request.form.get("email", "").strip()
    ip = security.client_ip(cfg.TRUSTED_PROXIES)

    if not security.over_limit("reset_ip", ip, cfg.RL_RESET_IP, cfg.RL_WINDOW):
        security.record_attempt("reset_ip", ip)
        user = db.user_by_email(email)
        if user:
            with db.write() as cur:
                # Asking again retires the previous link, so a forwarded or
                # cached old email cannot be used later.
                db.invalidate_tokens(cur, user["id"], "reset")
                raw_token, token_hash = security.new_token()
                db.store_token(cur, token_hash, user["id"], "reset", cfg.TOKEN_HOURS)
            emailer.send_reset(
                cfg, user["email"], user["name"],
                f"{cfg.BASE_URL}{url_for('reset_password', token=raw_token)}")
            log.info("password reset requested", extra={"username": user["username"]})

    # Deliberately identical whether or not the address exists: a
    # different message here turns this form into a way to test which
    # email addresses have accounts.
    flash("If that address has an account, a reset link is on its way.", "success")
    return redirect(url_for("login"))


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    if request.method != "POST":
        # Not consumed yet — that happens on submit, so landing on the page
        # (or a mail client prefetching it) does not burn the link.
        return render_template("reset.html", token=token)

    password = request.form.get("password", "")
    confirm = request.form.get("password_confirm", "")
    problem = security.password_problem(password, confirm)
    if problem:
        flash(problem, "error")
        return render_template("reset.html", token=token)

    user = db.consume_token(security.hash_token(token), "reset")
    if not user:
        flash("That reset link has expired or already been used. Ask for a new one.", "error")
        return redirect(url_for("forgot_password"))

    # Bumps session_epoch, so every existing session for this account —
    # including whoever prompted the reset — stops working immediately.
    db.set_password(user["id"], generate_password_hash(password))
    security.clear_attempts("login_user", user["username"])
    log.info("password reset completed", extra={"username": user["username"]})

    flash("Password updated. Sign in with your new one.", "success")
    return redirect(url_for("login"))


# ── Progress helpers ────────────────────────────────────────────────────────────

def quiz_score(lesson: dict, entry: dict) -> int | None:
    """Percent of questions answered correctly on the first try."""
    questions = lesson.get("quiz", [])
    if not questions:
        return None
    answers = entry.get("quiz", {})
    if not answers:
        return None
    first_try = sum(1 for q in questions if answers.get(q["id"], {}).get("first_try"))
    return round(first_try / len(questions) * 100)


def summarise(student_id: int) -> dict:
    """One student's headline numbers."""
    return summarise_many([student_id])[student_id]


def summarise_many(student_ids: list[int]) -> dict[int, dict]:
    """
    Headline numbers for any number of students in a fixed number of
    queries.  The dashboard used to call a per-student function that
    re-read the whole progress file, several times over, per student.
    """
    lessons = load_lessons()
    total = len(lessons)
    rows = db.summaries_for(student_ids, _catalog["question_counts"])

    for row in rows.values():
        row["total"] = total
        row["percent"] = round(row["completed"] / total * 100) if total else 0
    return rows


def days_since(stamp: datetime | None) -> int | None:
    if not stamp:
        return None
    return (datetime.now(timezone.utc) - stamp).days


def sticking_points(student_id: int, entries: dict[str, dict] | None = None) -> list[dict]:
    """
    Questions this student got wrong, newest first, with the topic and the
    right answer spelled out.  This is what a parent reads instead of
    interpreting a score.
    """
    entries = entries if entries is not None else db.lesson_entries(student_id)
    out: list[dict] = []

    for lesson in load_lessons():
        answers = entries.get(lesson["id"], {}).get("quiz", {})
        if not answers:
            continue
        for question in lesson.get("quiz", []):
            a = answers.get(question["id"])
            if not a or a.get("tries", 0) == 0:
                continue
            missed = a.get("tries", 0) > 1 or not a.get("correct")
            if not missed:
                continue
            choices = question.get("choices", [])
            chosen = a.get("chosen")
            out.append({
                "lesson":       lesson["title"],
                "lesson_id":    lesson["id"],
                "subject":      lesson.get("subject", ""),
                "prompt":       question["prompt"],
                "their_answer": choices[chosen] if isinstance(chosen, int) and 0 <= chosen < len(choices) else "—",
                "right_answer": choices[question["answer"]] if choices else "—",
                "tries":        a.get("tries", 0),
                "resolved":     bool(a.get("correct")),
                "explain":      question.get("explain", ""),
            })

    return sorted(out, key=lambda s: (s["resolved"], -s["tries"]))


def practice_examples(student_id: int, entries: dict[str, dict] | None = None) -> list[dict]:
    """
    Every practice example a student has answered, right or wrong. These
    are never graded back to the student — see /api/example — so this
    grown-up view is the only place the right answer ever surfaces.
    """
    entries = entries if entries is not None else db.lesson_entries(student_id)
    out: list[dict] = []

    for lesson in load_lessons():
        answers = entries.get(lesson["id"], {}).get("examples", {})
        if not answers:
            continue
        for example in lesson.get("examples", []):
            a = answers.get(example["id"])
            if not a:
                continue
            choices = example.get("choices", [])
            chosen = a.get("chosen")
            out.append({
                "lesson":       lesson["title"],
                "prompt":       example["prompt"],
                "their_answer": choices[chosen] if isinstance(chosen, int) and 0 <= chosen < len(choices) else "—",
                "right_answer": choices[example["answer"]] if choices else "—",
                "correct":      bool(a.get("correct")),
                "updated":      a.get("updated") or "",
            })

    return sorted(out, key=lambda r: r["updated"], reverse=True)


def headline(summary: dict, stuck: int) -> dict:
    """
    One sentence a parent can read in two seconds, plus a tone for colour.
    Ordered by what most needs saying.

    Takes the numbers rather than fetching them, so a dashboard of 200
    students computes them once instead of once per card.
    """
    quiet = days_since(summary["last_active"])

    if summary["completed"] == 0 and summary["in_progress"] == 0:
        return {"tone": "idle", "icon": "🌱",
                "text": "Hasn't started yet — the first lesson is ready when they are."}

    if quiet is not None and quiet >= QUIET_DAYS:
        return {"tone": "warn", "icon": "💤",
                "text": f"No practice in {quiet} days — a nudge would help."}

    if stuck:
        return {"tone": "warn", "icon": "🤔",
                "text": f"Stuck on {stuck} question{'' if stuck == 1 else 's'} — worth a look."}

    if summary["completed"] == summary["total"] and summary["total"]:
        return {"tone": "good", "icon": "🎉",
                "text": "Finished every lesson. Time for new material!"}

    if summary["avg_score"] is not None and summary["avg_score"] >= 80:
        return {"tone": "good", "icon": "⭐",
                "text": f"Doing great — {summary['completed']} lessons done, {summary['avg_score']}% on quizzes."}

    return {"tone": "ok", "icon": "👍",
            "text": f"On track — {summary['completed']} of {summary['total']} lessons done."}


def recent_activity(entries: dict[str, dict], limit: int = 8) -> list[dict]:
    """Newest-first timeline of what actually happened."""
    rows = []
    for lesson in load_lessons():
        e = entries.get(lesson["id"])
        if not e or not e.get("updated"):
            continue
        rows.append({
            "when":   e["updated"],
            "title":  lesson["title"],
            "status": e.get("status", "in_progress"),
            "score":  quiz_score(lesson, e),
        })
    return sorted(rows, key=lambda r: r["when"], reverse=True)[:limit]


# ── Student screens ─────────────────────────────────────────────────────────────

# DUDE_Ad's classroom greeting — robot Mr. T, but a few words tops.
DUDE_LINES = [
    "Let's build somethin'!",
    "I pity the bug!",
    "Quit jibber-jabbin'!",
    "Circuits, fool!",
    "Time to spark up!",
    "No shortcuts, fool!",
    "Let's get buzzin'!",
    "I got the power!",
    "Suit up, spark up!",
    "Chains on, brain on!",
    "Ready to roll, kid!",
    "Volts up, let's go!",
]


@app.route("/classroom")
@login_required("student")
@membership_required
def classroom():
    user = current_user()
    return render_template("classroom.html",
                           layout=load_classroom(),
                           summary=summarise(user["id"]),
                           dude_line=random.choice(DUDE_LINES))


@app.route("/lessons")
@login_required("student")
@membership_required
def lessons():
    user = current_user()
    entries = db.lesson_entries(user["id"])
    paid_ok = entitlement()["active"]
    catalog = [{**l,
                "progress": entries.get(l["id"], {"status": "not_started"}),
                "locked": not (billing.lesson_is_free(l) or paid_ok)}
               for l in assigned_lessons(user["id"], load_lessons())]

    # Kits are informational and never gate anything, so this is only a
    # count for the "some of these have kits" note on the menu.
    kit_count = sum(1 for l in catalog if l.get("kit"))

    # Grouped by subject, in the order each subject first appears in the
    # (already order-sorted) catalog — so a lesson's own "order" in its
    # manifest decides both its place in its category and which category
    # shows up first. No separate category config to keep in sync.
    categories: dict[str, list] = {}
    for item in catalog:
        categories.setdefault(item.get("subject", "General"), []).append(item)

    return render_template("lessons.html", categories=categories,
                           kit_count=kit_count,
                           summary=summarise(user["id"]))


@app.route("/lesson/<lesson_id>")
@login_required("student")
@membership_required
def lesson(lesson_id: str):
    user = current_user()
    found = get_lesson(lesson_id)
    if not found:
        abort(404)
    assigned = db.assigned_lesson_ids(user["id"])
    if assigned is not None and lesson_id not in assigned:
        abort(403)

    # Paid lessons need a live subscription somewhere — the school's or a
    # parent's. Free lessons stay open, so a lapsed account still has
    # something to come back to.
    if not billing.lesson_is_free(found) and not entitlement()["active"]:
        return redirect(url_for("locked", lesson_id=lesson_id))

    entry = db.lesson_entries(user["id"]).get(lesson_id, {})
    if entry.get("status") != "completed":
        db.set_lesson_status(user["id"], lesson_id, "in_progress")

    body = render_content(found["content"]) if found["type"] == "reading" else None

    # Never ship the answer key to the client — questions are stripped and
    # answers checked server-side in /api/quiz.
    quiz = [{"id": q["id"], "prompt": q["prompt"], "choices": q.get("choices", []),
             "diagram": q.get("diagram")}
            for q in found.get("quiz", [])]

    return render_template("lesson.html", lesson=found, entry=entry,
                           body=body, quiz=quiz,
                           summary=summarise(user["id"]))


@app.route("/satchel")
@login_required("student")
@membership_required
def satchel():
    user = current_user()
    catalog = load_items()
    earned = set(db.inventory(user["id"]))

    items = [{**info, "id": iid, "earned": iid in earned}
             for iid, info in catalog.items()]
    items.sort(key=lambda i: (not i["earned"], i.get("name", "")))

    return render_template("satchel.html", items=items,
                           earned_count=len(earned & set(catalog)),
                           summary=summarise(user["id"]))


# ── Student APIs ────────────────────────────────────────────────────────────────

@app.route("/api/progress", methods=["POST"])
@login_required("student")
def api_progress():
    """Called by the lesson player, and by lessons via the kit's postMessage."""
    user = current_user()
    body = request.get_json(silent=True) or {}

    lesson_id = body.get("lesson_id")
    status = body.get("status", "in_progress")
    found = get_lesson(lesson_id) if lesson_id else None

    if not found:
        return jsonify({"error": "Unknown lesson."}), 400
    if status not in ("in_progress", "completed"):
        return jsonify({"error": "Invalid status."}), 400
    if not billing.lesson_is_free(found) and not entitlement()["active"]:
        return jsonify({"error": "That lesson needs an active subscription."}), 402

    try:
        score = None if body.get("score") is None else max(0, min(int(body["score"]), 100))
    except (TypeError, ValueError):
        score = None

    db.set_lesson_status(user["id"], lesson_id, status, score,
                         reward=found.get("reward"))
    return jsonify({"ok": True, "summary": summarise(user["id"])})


@app.route("/api/quiz", methods=["POST"])
@login_required("student")
def api_quiz():
    """
    Check one answer and record the attempt.  The answer key never leaves
    the server, so it cannot be read out of the page source.
    """
    user = current_user()
    body = request.get_json(silent=True) or {}

    found = get_lesson(body.get("lesson_id", ""))
    if not found:
        return jsonify({"error": "Unknown lesson."}), 400
    if not billing.lesson_is_free(found) and not entitlement()["active"]:
        return jsonify({"error": "That lesson needs an active subscription."}), 402

    question = next((q for q in found.get("quiz", []) if q["id"] == body.get("question_id")), None)
    if not question:
        return jsonify({"error": "Unknown question."}), 400

    try:
        chosen = int(body.get("chosen"))
    except (TypeError, ValueError):
        return jsonify({"error": "No answer given."}), 400

    correct = chosen == question["answer"]
    db.record_answer(user["id"], found["id"], question["id"], chosen, correct)

    return jsonify({
        "correct": correct,
        "answer":  question["answer"],
        "explain": question.get("explain", ""),
    })


@app.route("/api/examples/<lesson_id>")
@login_required("student")
def api_examples(lesson_id: str):
    """
    Prompts and choices for a lesson's practice examples, answer key
    stripped — the same treatment the quiz gets. A lesson's own iframe
    fetches this to render its practice questions.
    """
    found = get_lesson(lesson_id)
    if not found:
        abort(404)
    if not billing.lesson_is_free(found) and not entitlement()["active"]:
        return jsonify({"error": "That lesson needs an active subscription."}), 402
    stripped = [{"id": e["id"], "prompt": e["prompt"], "choices": e.get("choices", [])}
                for e in found.get("examples", [])]
    return jsonify(stripped)


@app.route("/api/example", methods=["POST"])
@login_required("student")
def api_example():
    """
    Record one practice-example answer and hand back the same
    correct/explain shape /api/quiz gives — Spark uses it to confirm or
    explain right there in the lesson. Recorded separately from the
    graded quiz, for the grown-up view only — see practice_examples().
    """
    user = current_user()
    body = request.get_json(silent=True) or {}

    found = get_lesson(body.get("lesson_id", ""))
    if not found:
        return jsonify({"error": "Unknown lesson."}), 400
    if not billing.lesson_is_free(found) and not entitlement()["active"]:
        return jsonify({"error": "That lesson needs an active subscription."}), 402

    example = next((e for e in found.get("examples", []) if e["id"] == body.get("example_id")), None)
    if not example:
        return jsonify({"error": "Unknown example."}), 400

    try:
        chosen = int(body.get("chosen"))
    except (TypeError, ValueError):
        return jsonify({"error": "No answer given."}), 400

    correct = chosen == example["answer"]
    db.record_example(user["id"], found["id"], example["id"], chosen, correct)

    return jsonify({
        "correct": correct,
        "answer":  example["answer"],
        "explain": example.get("explain", ""),
    })


@app.route("/api/quiz/finish", methods=["POST"])
@login_required("student")
def api_quiz_finish():
    """Score the quiz, complete the lesson, and hand back any reward earned."""
    user = current_user()
    body = request.get_json(silent=True) or {}

    found = get_lesson(body.get("lesson_id", ""))
    if not found:
        return jsonify({"error": "Unknown lesson."}), 400
    if not billing.lesson_is_free(found) and not entitlement()["active"]:
        return jsonify({"error": "That lesson needs an active subscription."}), 402

    entry = db.lesson_entries(user["id"]).get(found["id"], {})
    score = quiz_score(found, entry)

    try:
        quiz_seconds = max(0, min(int(body.get("quiz_seconds")), 4 * 3600))
    except (TypeError, ValueError):
        quiz_seconds = None

    # The insert itself reports which items were newly granted, so there is
    # no read-compare-read around it and a double submit cannot award twice.
    new_ids = db.set_lesson_status(user["id"], found["id"], "completed",
                                   score, quiz_seconds, reward=found.get("reward"))
    catalog = load_items()
    rewards = [{**catalog[i], "id": i} for i in new_ids if i in catalog]

    return jsonify({
        "ok":      True,
        "score":   score,
        "rewards": rewards,
        "summary": summarise(user["id"]),
    })


# ── Grown-up screens (parent + teacher) ─────────────────────────────────────────

@app.route("/grownup")
@login_required("teacher", "parent")
@membership_required
def grownup_home():
    """
    Answers "is my kid doing the work?" without any digging: a headline
    per student, and anything needing attention pulled to the top.

    Every number on this page comes from a fixed number of queries no
    matter how many students there are.
    """
    user = current_user()
    students = db.visible_students(user)
    ids = [s["id"] for s in students]

    summaries = summarise_many(ids)
    stuck_counts = db.unresolved_counts(ids, _catalog["valid_pairs"])

    cards = []
    for student in students:
        summary = summaries[student["id"]]
        stuck = stuck_counts.get(student["id"], 0)
        cards.append({
            "username": student["username"],
            "name":     student["name"],
            "avatar":   student["avatar"],
            "headline": headline(summary, stuck),
            "stuck":    stuck,
            "quiet":    days_since(summary["last_active"]),
            **summary,
        })

    order = {"warn": 0, "idle": 1, "ok": 2, "good": 3}
    cards.sort(key=lambda c: (order.get(c["headline"]["tone"], 9), c["name"].lower()))
    needs_attention = [c for c in cards if c["headline"]["tone"] in ("warn", "idle")]

    org = db.org_by_id(user["org_id"])
    return render_template("grownup.html",
                           cards=cards,
                           needs_attention=needs_attention,
                           is_teacher=user["role"] == "teacher",
                           org=org,
                           lesson_count=len(load_lessons()))


def _visible_student_or_404(user: dict, username: str) -> dict:
    """
    Resolve a username from the URL to a student this account may see.

    Ordering matters: an account that is not visible gets 404, not 403, so
    the response cannot be used to discover which usernames exist in
    another organisation.
    """
    student = db.user_by_username(username)
    if not student or student["role"] != "student":
        abort(404)
    if not db.can_see_student(user, student["id"]):
        abort(404)
    return student


@app.route("/grownup/student/<username>")
@login_required("teacher", "parent")
def student_detail(username: str):
    user = current_user()
    student = _visible_student_or_404(user, username)

    entries = db.lesson_entries(student["id"])
    assigned_ids = db.assigned_lesson_ids(student["id"])
    summary = summarise(student["id"])

    rows = []
    for item in load_lessons():
        entry = entries.get(item["id"], {"status": "not_started"})
        rows.append({
            **item,
            "progress": entry,
            "score":    quiz_score(item, entry),
            "assigned": assigned_ids is None or item["id"] in assigned_ids,
        })

    sticking = sticking_points(student["id"], entries)
    unresolved = len([s for s in sticking if not s["resolved"]])

    return render_template("student.html",
                           student=student,
                           rows=rows,
                           summary=summary,
                           headline=headline(summary, unresolved),
                           sticking=sticking,
                           practice=practice_examples(student["id"], entries),
                           activity=recent_activity(entries),
                           quiet=days_since(summary["last_active"]),
                           is_teacher=user["role"] == "teacher",
                           custom_assignment=assigned_ids is not None)


@app.route("/grownup/student/<username>/assign", methods=["POST"])
@login_required("teacher", "parent")
def student_assign(username: str):
    """Narrow (or re-widen) which lessons show up on one student's menu."""
    user = current_user()
    student = _visible_student_or_404(user, username)

    valid_ids = {l["id"] for l in load_lessons()}
    checked = [i for i in request.form.getlist("lesson_id") if i in valid_ids]

    # Everything is checked — that's the unrestricted default, so drop the
    # row rather than storing a list that just says "all of them".
    db.set_assignment(student["id"],
                      None if len(checked) == len(valid_ids) else checked,
                      user["id"])

    flash(f"Updated {student['name']}'s lesson menu.", "success")
    return redirect(url_for("student_detail", username=username))


@app.route("/grownup/link", methods=["POST"])
@login_required("parent")
def link_child():
    """
    A parent attaches themselves to a student with the student's link
    code.  The code is scoped to the parent's own organisation, so a
    guessed code cannot reach across schools.
    """
    user = current_user()
    student = db.student_by_link_code(request.form.get("link_code", ""))

    if not student or student["org_id"] != user["org_id"]:
        flash("That student code didn't match anyone in your class.", "error")
        return redirect(url_for("grownup_home"))

    db.link_parent(user["id"], student["id"])
    flash(f"Linked to {student['name']}.", "success")
    return redirect(url_for("grownup_home"))


# ── Groups (teacher only) ───────────────────────────────────────────────────────

@app.route("/groups")
@login_required("teacher")
def groups_home():
    user = current_user()
    students = db.visible_students(user)
    rows = db.group_summary_rows(user["org_id"])

    # One pass over every student in the org, then group membership is
    # matched against it in memory — rather than a query per group.
    ids = [s["id"] for s in students]
    summaries = summarise_many(ids)
    stuck_counts = db.unresolved_counts(ids, _catalog["valid_pairs"])

    cards = []
    for row in rows:
        members = [m["id"] for m in db.group_members(row["id"])]
        stats = [summaries[m] for m in members if m in summaries]
        cards.append({
            "id":      row["id"],
            "name":    row["name"],
            "members": len(members),
            "avg":     round(sum(s["percent"] for s in stats) / len(stats)) if stats else 0,
            "stuck":   sum(stuck_counts.get(m, 0) for m in members),
        })

    return render_template("groups.html",
                           groups=cards,
                           student_count=len(students),
                           lesson_count=len(load_lessons()))


@app.route("/groups/new", methods=["POST"])
@login_required("teacher")
def group_create():
    user = current_user()
    name = request.form.get("name", "").strip()
    if not name:
        flash("Give the group a name.", "error")
        return redirect(url_for("groups_home"))

    gid = db.create_group(user["org_id"], name[:120], user["id"])
    flash(f"Created “{name}”.", "success")
    return redirect(url_for("group_detail", gid=gid))


def _group_or_404(user: dict, gid: int) -> dict:
    group = db.group_in_org(gid, user["org_id"])
    if not group:
        abort(404)
    return group


@app.route("/groups/<int:gid>")
@login_required("teacher")
def group_detail(gid: int):
    user = current_user()
    group = _group_or_404(user, gid)

    member_rows = db.group_members(gid)
    ids = [m["id"] for m in member_rows]
    summaries = summarise_many(ids)
    stuck_counts = db.unresolved_counts(ids, _catalog["valid_pairs"])

    members = []
    for row in member_rows:
        summary = summaries[row["id"]]
        members.append({
            "username": row["username"],
            "name":     row["name"],
            "headline": headline(summary, stuck_counts.get(row["id"], 0)),
            "stuck":    stuck_counts.get(row["id"], 0),
            **summary,
        })

    in_group = set(ids)
    available = [{"username": s["username"], "name": s["name"]}
                 for s in db.visible_students(user) if s["id"] not in in_group]

    return render_template("group.html", gid=gid, group=group,
                           members=members, available=available)


@app.route("/groups/<int:gid>/add", methods=["POST"])
@login_required("teacher")
def group_add_member(gid: int):
    user = current_user()
    _group_or_404(user, gid)
    student = _visible_student_or_404(user, request.form.get("username", ""))

    db.add_group_member(gid, student["id"])
    flash(f"Added {student['name']}.", "success")
    return redirect(url_for("group_detail", gid=gid))


@app.route("/groups/<int:gid>/remove", methods=["POST"])
@login_required("teacher")
def group_remove_member(gid: int):
    user = current_user()
    _group_or_404(user, gid)
    student = _visible_student_or_404(user, request.form.get("username", ""))

    db.remove_group_member(gid, student["id"])
    flash("Removed from group.", "success")
    return redirect(url_for("group_detail", gid=gid))


@app.route("/groups/<int:gid>/delete", methods=["POST"])
@login_required("teacher")
def group_delete(gid: int):
    user = current_user()
    name = db.delete_group(gid, user["org_id"])
    if name:
        flash(f"Deleted “{name}”.", "success")
    return redirect(url_for("groups_home"))


# ── Locked lesson ───────────────────────────────────────────────────────────────

@app.route("/locked")
@login_required()
def locked():
    """
    Where a student lands on a lesson their account does not cover.

    Deliberately not a 402 page with a Buy button: a 13-year-old is not
    the payer, so this tells them who to ask rather than selling to them.
    """
    lesson = get_lesson(request.args.get("lesson_id", "")) or None
    return render_template("locked.html", lesson=lesson,
                           entitlement=entitlement()), 402


# ── Org administration (admin teachers only) ────────────────────────────────────

@app.route("/org")
@org_admin_required
def org_home():
    user = current_user()
    org = db.org_by_id(user["org_id"])
    subscription = db.subscription_for_org(org["id"])

    return render_template("org.html",
                           org=org,
                           members=db.org_members(org["id"]),
                           pending=db.pending_members(org["id"]),
                           seats=db.count_billable_seats(org["id"]),
                           subscription=subscription,
                           entitlement=entitlement(),
                           admin_count=db.count_org_admins(org["id"]))


def _member_or_404(user: dict, raw_id: str) -> dict:
    """
    Resolve a member id from a form to someone in the admin's own org.

    Scoping the lookup by org_id is what stops an admin posting another
    org's user id and editing a roster they cannot see.
    """
    try:
        member_id = int(raw_id)
    except (TypeError, ValueError):
        abort(404)
    member = db.member_in_org(member_id, user["org_id"])
    if not member:
        abort(404)
    return member


@app.route("/org/join-policy", methods=["POST"])
@org_admin_required
def org_join_policy():
    user = current_user()
    policy = request.form.get("join_policy", "open")
    if policy not in ("open", "approval"):
        abort(400, "Unknown join policy.")

    db.set_join_policy(user["org_id"], policy)
    flash("New sign-ups need approval." if policy == "approval"
          else "Anyone with the join code can sign up.", "success")
    return redirect(url_for("org_home"))


@app.route("/org/rotate-code", methods=["POST"])
@org_admin_required
def org_rotate_code():
    user = current_user()
    code = db.rotate_join_code(user["org_id"])
    flash(f"New join code: {code}. The old one no longer works.", "success")
    return redirect(url_for("org_home"))


@app.route("/org/members/<member_id>/approve", methods=["POST"])
@org_admin_required
def org_approve_member(member_id: str):
    user = current_user()
    member = _member_or_404(user, member_id)

    db.set_membership_status(member["id"], user["org_id"], "active")
    _resize_org_seats(user["org_id"])
    flash(f"{member['name']} is in.", "success")
    return redirect(url_for("org_home"))


@app.route("/org/members/<member_id>/remove", methods=["POST"])
@org_admin_required
def org_remove_member(member_id: str):
    user = current_user()
    member = _member_or_404(user, member_id)

    if member["id"] == user["id"]:
        flash("You can't remove yourself.", "error")
        return redirect(url_for("org_home"))
    # Removing the last admin would leave the org with nobody who can
    # approve members or pay the bill.
    if member["org_admin"] and db.count_org_admins(user["org_id"]) <= 1:
        flash("Make someone else an admin first — an org needs one.", "error")
        return redirect(url_for("org_home"))

    db.set_membership_status(member["id"], user["org_id"], "removed")
    _resize_org_seats(user["org_id"])
    flash(f"Removed {member['name']}. Their work is kept.", "success")
    return redirect(url_for("org_home"))


@app.route("/org/members/<member_id>/admin", methods=["POST"])
@org_admin_required
def org_set_admin(member_id: str):
    user = current_user()
    member = _member_or_404(user, member_id)
    make_admin = request.form.get("admin") == "1"

    if not make_admin and member["org_admin"] and db.count_org_admins(user["org_id"]) <= 1:
        flash("An org needs at least one admin.", "error")
        return redirect(url_for("org_home"))

    if not db.set_org_admin(member["id"], user["org_id"], make_admin):
        flash("Only teacher accounts can be admins.", "error")
        return redirect(url_for("org_home"))

    flash(f"{member['name']} is {'now an admin' if make_admin else 'no longer an admin'}.",
          "success")
    return redirect(url_for("org_home"))


def _resize_org_seats(org_id: int) -> None:
    """
    Keep the Stripe quantity in step with the roster.

    Best-effort on purpose: a Stripe outage must not stop a teacher
    approving a student. The nightly `manage.py sync-seats` reconciles
    anything that failed here.
    """
    if not billing.enabled(cfg):
        return
    subscription = db.subscription_for_org(org_id)
    if not subscription or not subscription.get("stripe_subscription_id"):
        return
    try:
        billing.update_seats(cfg,
                             stripe_subscription_id=subscription["stripe_subscription_id"],
                             quantity=db.count_billable_seats(org_id))
    except Exception:
        log.exception("could not resize seats for org %s", org_id)


# ── Billing ─────────────────────────────────────────────────────────────────────

def _billing_context(user: dict) -> dict:
    """
    Who is the payer for this account, and what are they paying with?

    An org admin manages the school's subscription; a parent manages their
    own. Nobody else sees a billing page at all.
    """
    if user["role"] == "teacher" and user["org_admin"]:
        org = db.org_by_id(user["org_id"])
        subscription = db.subscription_for_org(org["id"])
        return {
            "kind": "org",
            "org": org,
            "subscription": subscription,
            "seats": db.count_billable_seats(org["id"]),
            "price_key": cfg.PRICE_ORG_SEAT,
            "metadata": {"account_kind": "org", "org_id": org["id"], "ref": f"org:{org['id']}"},
        }
    if user["role"] == "parent":
        subscription = db.subscription_for_parent(user["id"])
        return {
            "kind": "parent",
            "org": None,
            "subscription": subscription,
            "seats": max(1, len(db.visible_students(user))),
            "price_key": cfg.PRICE_FAMILY,
            "metadata": {"account_kind": "parent", "user_id": user["id"],
                         "ref": f"parent:{user['id']}"},
        }
    return {}


@app.route("/billing")
@login_required("teacher", "parent")
@membership_required
def billing_home():
    user = current_user()
    context = _billing_context(user)
    if not context:
        abort(404)

    subscription = context["subscription"]
    return render_template("billing.html",
                           ctx=context,
                           subscription=subscription,
                           entitlement=entitlement(),
                           invoices=db.invoices_for(subscription["id"]) if subscription else [],
                           trial_days=cfg.TRIAL_DAYS,
                           due_days=cfg.INVOICE_DUE_DAYS)


@app.route("/billing/subscribe", methods=["POST"])
@login_required("teacher", "parent")
@membership_required
def billing_subscribe():
    """Send the payer to Stripe's hosted Checkout. No card touches us."""
    user = current_user()
    context = _billing_context(user)
    if not context:
        abort(404)
    if not billing.enabled(cfg):
        flash("Payments aren't switched on yet.", "error")
        return redirect(url_for("billing_home"))

    existing = context["subscription"]
    try:
        customer_id = billing.ensure_customer(
            cfg,
            existing_id=existing["stripe_customer_id"] if existing else None,
            email=(context["org"]["billing_email"] if context["kind"] == "org" and context["org"]["billing_email"]
                   else user["email"]),
            name=context["org"]["name"] if context["kind"] == "org" else user["name"],
            metadata=context["metadata"],
        )
        url = billing.checkout_session(
            cfg,
            customer_id=customer_id,
            price_lookup_key=context["price_key"],
            quantity=context["seats"],
            success_url=f"{cfg.BASE_URL}{url_for('billing_return')}",
            cancel_url=f"{cfg.BASE_URL}{url_for('billing_home')}",
            metadata=context["metadata"],
            trial_days=cfg.TRIAL_DAYS if not existing else None,
        )
    except billing.BillingUnavailable as exc:
        log.error("checkout unavailable: %s", exc)
        flash("Payments aren't available right now. Try again shortly.", "error")
        return redirect(url_for("billing_home"))
    except Exception:
        log.exception("could not start checkout")
        flash("Something went wrong starting checkout.", "error")
        return redirect(url_for("billing_home"))

    return redirect(url, code=303)


@app.route("/billing/portal", methods=["POST"])
@login_required("teacher", "parent")
@membership_required
def billing_portal():
    """
    Stripe's hosted account page: change card, cancel, download invoices.

    Everything a payer wants to do to their own billing, on Stripe's
    domain, with no billing UI of ours in the way.
    """
    user = current_user()
    context = _billing_context(user)
    if not context or not context["subscription"]:
        abort(404)

    try:
        url = billing.portal_session(
            cfg,
            customer_id=context["subscription"]["stripe_customer_id"],
            return_url=f"{cfg.BASE_URL}{url_for('billing_home')}",
        )
    except Exception:
        log.exception("could not open the customer portal")
        flash("Couldn't open the billing portal. Try again shortly.", "error")
        return redirect(url_for("billing_home"))

    return redirect(url, code=303)


@app.route("/billing/return")
@login_required("teacher", "parent")
def billing_return():
    """
    Where Stripe sends the browser after Checkout.

    It grants nothing. Anyone can visit this URL, so entitlement changes
    only when the signed webhook arrives — this page just says so politely
    while that happens.
    """
    return render_template("billing_return.html", entitlement=entitlement())


@app.route("/billing/invoice-request", methods=["POST"])
@org_admin_required
def billing_invoice_request():
    """
    Ask to be billed by invoice on terms instead of by card.

    This records the request; it does not grant it. Net 30 is unsecured
    credit, and a school district is worth extending it to in a way an
    anonymous signup is not — a human approves it with
    `manage.py approve-invoice`.
    """
    user = current_user()
    org = db.org_by_id(user["org_id"])

    billing_email = request.form.get("billing_email", "").strip()
    problem = security.email_problem(billing_email)
    if problem:
        flash(problem, "error")
        return redirect(url_for("billing_home"))

    db.set_billing_profile(
        org["id"],
        billing_email=billing_email,
        po_number=request.form.get("po_number", "").strip() or None,
        tax_exempt=request.form.get("tax_exempt") == "1",
        requested=True,
    )
    log.info("invoice terms requested", extra={"org_id": org["id"], "org": org["name"]})

    emailer.send(cfg, cfg.EMAIL_FROM, "Invoice billing requested",
                 f"""{org['name']} has asked to be billed by invoice.

  Org id:        {org['id']}
  Billing email: {billing_email}
  PO number:     {request.form.get('po_number', '') or '—'}
  Tax exempt:    {'yes' if request.form.get('tax_exempt') == '1' else 'no'}
  Seats:         {db.count_billable_seats(org['id'])}

Approve with:  python game/manage.py approve-invoice {org['id']}
""")

    flash("Request received. We'll confirm by email, usually within a "
          "business day, and then send the first invoice.", "success")
    return redirect(url_for("billing_home"))


# ── Stripe webhook ──────────────────────────────────────────────────────────────
#
# Deliberately outside /api/, which would have exempted it from CSRF as a
# side effect of that prefix requiring JSON. The exemption here is
# explicit and justified: the Stripe-Signature header IS this endpoint's
# authentication, and it is checked before anything else happens.

@app.route("/stripe/webhook", methods=["POST"])
@security.csrf_exempt
def stripe_webhook():
    if not billing.enabled(cfg):
        abort(404)

    # The signature is computed over the exact bytes Stripe sent. Anything
    # that re-encodes the body invalidates it.
    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature")

    try:
        event = billing.verify_webhook(cfg, payload, signature)
    except Exception as exc:
        # 400, not 500: the request is malformed or forged, and Stripe
        # should not retry it.
        log.warning("rejected webhook: %s", exc)
        return jsonify({"error": "invalid signature"}), 400

    event_id, event_type = event["id"], event["type"]

    if event_type not in billing.HANDLED_EVENTS:
        # Acknowledged, not acted on. Returning non-2xx for events we do
        # not care about would have Stripe retry them until it disables
        # the endpoint.
        return jsonify({"ok": True, "ignored": event_type})

    if not db.claim_event(event_id, event_type):
        # Already handled. Stripe retries and delivers out of order, so
        # this is normal traffic, not an error.
        return jsonify({"ok": True, "duplicate": True})

    try:
        outcome = billing.handle_event(cfg, event)
    except Exception:
        log.exception("webhook %s (%s) failed", event_id, event_type)
        # Hand the claim back so the retry can try again, and ask for one.
        db.release_event(event_id)
        return jsonify({"error": "handler failed"}), 500

    db.finish_event(event_id)
    log.info("webhook handled", extra={"event": event_type, "outcome": outcome})
    return jsonify({"ok": True})


# ── Errors ──────────────────────────────────────────────────────────────────────

@app.errorhandler(HTTPException)
def _http_error(err):
    """
    Every deliberate HTTP status — 404, 405, 413, 415, 429 and the rest.

    This has to be registered separately from the catch-all below:
    a handler for Exception also catches HTTPException, which turned an
    ordinary 405 into a 500 with a stack trace in the log.
    """
    if request.path.startswith("/api/"):
        return jsonify({"error": err.description or "Request rejected."}), err.code
    return render_template("error.html", code=err.code,
                           message=err.description or ""), err.code


@app.errorhandler(Exception)
def _server_error(err):
    # Genuinely unexpected. Never let a stack trace or a database message
    # reach a browser.
    log.exception("unhandled error on %s", request.path)
    if request.path.startswith("/api/"):
        return jsonify({"error": "Something went wrong."}), 500
    return render_template("error.html", code=500, message=""), 500


# ── Boot ────────────────────────────────────────────────────────────────────────

def init_app() -> None:
    """
    Prepare this process to serve.  Called once per gunicorn worker and
    once by the development server.

    Migrations take a Postgres advisory lock, so several workers or
    containers starting at the same moment cannot apply them twice.
    """
    db.init_pool(cfg)
    if os.environ.get("RUN_MIGRATIONS", "1") == "1":
        applied = db.migrate()
        if applied:
            log.info("applied %d migration(s)", applied)
    refresh_catalog()
    log.info("catalog loaded: %d lesson(s)", len(load_lessons()))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ignite Academy game server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug reloader.")
    parser.add_argument("--migrate-only", action="store_true",
                        help="Apply database migrations and exit.")
    args = parser.parse_args()

    if args.migrate_only:
        db.init_pool(cfg)
        applied = db.migrate()
        print(f"  Migrations applied: {applied}")
        db.close_pool()
        return

    init_app()

    print(f"  Lessons discovered: {len(load_lessons())}")
    for item in load_lessons():
        print(f"    {item['id']:16} {item['type']:12} {len(item.get('quiz', []))} question(s)")

    if not art_exists("backgrounds/classroom"):
        print("  Classroom art not found — placeholder will be shown:")
        print("    static/art/backgrounds/classroom.png")

    print(f"\n  Serving at  http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
