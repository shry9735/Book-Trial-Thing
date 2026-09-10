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
ORGANISATIONS AND CLASSROOMS ARE THE PRIVACY BOUNDARY
──────────────────────────────────────────────────────
Every account belongs to exactly one organisation, and within it a
teacher is assigned to classrooms.  Three answers to "who can this
account see", all decided in db.visible_students() and its single-student
twin db.can_see_student():

    org admin   every student in the organisation, including any nobody
                has placed in a classroom yet
    teacher     only the students in the classrooms they are assigned to
    parent      only the children linked to them by link code

No screen ever enumerates across those lines.  Signing up as a teacher
creates an organisation and a join code; students and parents join an
existing one with that code, and an admin then places them.

LESSONS ARE STAGED BY TRACK
──────────────────────────────────────────────────────
A track is an ordered run of lessons (see tracks.py).  A track marked
sequential releases them one at a time — the next opens when the one
before it is finished.  That gate is pedagogy and is kept entirely
separate from the subscription gate in billing.py, because "you haven't
got there yet" and "this needs a subscription" have different remedies.

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
import csv
import functools
import io
import json
import logging
import os
import random
import re
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from flask import (
        Flask, abort, flash, g, jsonify, make_response, redirect,
        render_template, request, send_from_directory, session, url_for,
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
import standards
import tracks
from config import validate as load_config
from logsetup import configure_logging


BASE_DIR    = Path(__file__).parent
ART_DIR     = BASE_DIR / "static" / "art"
LESSONS_DIR = BASE_DIR / "lessons"    # one folder per lesson
TRACKS_DIR  = BASE_DIR / "tracks"     # one folder per track
STANDARDS_DIR = BASE_DIR / "standards"  # one JSON per curriculum framework
# Grown-up material: parent guides, answer keys, worksheets. Deliberately
# NOT under static/ and NOT inside a lesson folder — both of those are
# served to anyone who asks. See the resource routes for the long version.
RESOURCES_DIR = BASE_DIR / "resources"
CONTENT_DIR = BASE_DIR / "content"    # Markdown prose — also make_epub.py input
DATA_DIR    = BASE_DIR / "data"       # content only: item and classroom catalogs

ITEMS_FILE     = DATA_DIR / "items.json"
# The student's game room layout, not a class roster — see /classrooms
# for those. Same word, two different things.
ROOM_FILE      = DATA_DIR / "classroom.json"

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
    """
    Re-read every content file.

    Called once at boot, and by the test suites between fixtures. There is
    deliberately no way to trigger it over HTTP: content ships in the image,
    so "reload the content" is a deploy.

    The lock is held across the whole swap so a reader cannot see half of
    one catalog and half of another. Readers below do NOT take it: a single
    dict lookup is atomic under the GIL, so the worst a concurrent reader
    can get is the previous value of one key — never a torn one — and
    nothing writes here while requests are being served anyway.
    """
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
        _catalog["room"] = _read_json_file(
            ROOM_FILE, {"background": "backgrounds/classroom", "hotspots": []})
        # Tracks are content too: built once here from the lesson catalog
        # plus tracks/*/track.json, never queried per request.
        built = tracks.build(TRACKS_DIR, lessons)
        _catalog["tracks"] = built
        _catalog["track_by_id"] = {t["id"]: t for t in built}
        _catalog["track_of_lesson"] = {
            lesson_id: t for t in built for lesson_id in t["lesson_ids"]}
        # Standards are content too. Loaded here so a lesson pointing at a
        # code that does not exist gets reported at boot — that failure is
        # invisible in the UI, where the lesson just silently stops counting
        # towards anything, which is exactly why it is worth shouting about.
        frameworks = standards.load(STANDARDS_DIR)
        _catalog["frameworks"] = frameworks
        _catalog["standard_by_code"] = standards.index(frameworks)
        for lesson_id, code in standards.unknown_codes(
                lessons, _catalog["standard_by_code"]):
            log.warning("lesson %s claims unknown standard %s", lesson_id, code)
        # A requirement naming something that does not exist is ignored at
        # runtime rather than enforced, precisely so a typo cannot lock
        # content permanently — which means the only way anyone finds out
        # is if it is said out loud here.
        for problem in tracks.check_requirements(built):
            log.warning("content: %s", problem)


def load_lessons() -> list[dict]:
    return _catalog["lessons"]


def get_lesson(lesson_id: str) -> dict | None:
    return _catalog["by_id"].get(lesson_id)


def load_items() -> dict:
    return _catalog["items"]


def load_room() -> dict:
    """The student's game-room layout. Not a class roster — see /classrooms."""
    return _catalog["room"]


def load_tracks() -> list[dict]:
    return _catalog["tracks"]


def _without_resources(lesson: dict) -> dict:
    """
    A copy of a lesson with the grown-up material taken out.

    Belt and braces. The download routes are the real boundary — they
    require a parent or teacher session and serve only whitelisted files —
    and tracks.visible_resources() is the second check. This is the third:
    a student's template context simply never contains the list at all, so
    there is nothing for a future template, partial or serialiser to leak.
    """
    return {k: v for k, v in lesson.items() if k != "resources"}


def load_frameworks() -> list[dict]:
    return _catalog["frameworks"]


def standard_by_code() -> dict[str, dict]:
    return _catalog["standard_by_code"]


def track_of(lesson_id: str) -> dict | None:
    return _catalog["track_of_lesson"].get(lesson_id)


def prerequisite_block(student_id: int, lesson: dict) -> dict | None:
    """
    What is standing between this student and the lesson they asked for, or
    None if nothing is.

    Three kinds of block live here, all pedagogy and none of them payment:

      unassigned    a grown-up has to hand this one out
      prerequisite  a track or lesson somewhere else is unfinished
      sequence      the lesson before this one, in this same track

    Reported in that order, worst-remedy-last. "Ask your teacher" is
    actionable today; "finish Basic Electricity" is a week's work; "finish
    the lesson before this" is the smallest of the three, so it goes last
    when several are true at once.

    Staging is per-student, so this reads their progress and their own
    assigned menu. Every route that opens a lesson goes through here — the
    menu hides locked cards, but a bookmark or a guessed URL does not pass
    through the menu.
    """
    track = track_of(lesson["id"])
    by_track = {t["id"]: t for t in load_tracks()}
    by_lesson = {l["id"]: l for l in load_lessons()}

    # Both the lesson's own requirements and its track's apply. A track-level
    # requirement holds every lesson in it, which is the point of putting it
    # on the track.
    gated = [lesson] + ([track] if track else [])
    needed = tracks.required_lesson_ids(gated, by_track)
    if track and track.get("sequential"):
        needed.update(track["lesson_ids"])

    assigned = db.assigned_lesson_ids(student_id)
    assigned_ids = None if assigned is None else set(assigned)
    # The student's own menu. A lesson a teacher has hidden must not be
    # able to block anything — see the note on requirement_block.
    available_ids = assigned_ids

    # One query for every status any of the checks below could want, rather
    # than one per requirement: this runs on /api/quiz, once per answered
    # question.
    statuses = db.lesson_statuses(student_id, sorted(needed)) if needed else {}
    entries = {lesson_id: {"status": status} for lesson_id, status in statuses.items()}

    for item in gated:
        block = tracks.requirement_block(item, entries, by_track, by_lesson,
                                         assigned_ids, available_ids)
        if block:
            return {"track": track, "after": block["title"],
                    "reason": block["reason"], "remedy": block["remedy"]}

    if not track or not track.get("sequential"):
        return None

    available_ids = (set(track["lesson_ids"]) if assigned_ids is None
                     else set(track["lesson_ids"]) & assigned_ids)

    state = tracks.gate(track, entries, available_ids).get(lesson["id"])
    if not state or not state["locked"]:
        return None
    return {"track": track, "after": state["after"],
            "reason": tracks.BLOCK_SEQUENCE,
            "remedy": f"Finish “{state['after']}” first."}


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
    """
    A long, PUBLIC max-age. Only for responses that are the same for
    everybody: static kit files, lesson assets, generated placeholders.

    A page whose body depends on who is looking must not use this — `public`
    lets a shared cache serve one visitor's copy to another. Set
    `private` (and `Vary: Cookie`) on those instead; /legal is the worked
    example.
    """
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
    return render_markdown(raw)


def render_markdown(raw: str) -> str:
    """
    Markdown to HTML, with the same extensions everywhere.

    Shared by lesson prose and the legal pages so the two cannot render
    differently — the tables in the privacy notice need the same `tables`
    extension a lesson does, and finding that out the hard way is a
    published page full of pipe characters.
    """
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


# Endpoints an account with must_change_password set may still reach.
# Everything else bounces to the change form. Static and asset endpoints are
# in here so a half-rendered page still loads its stylesheet, and so the
# gate never costs a database lookup on a file request.
_PASSWORD_CHANGE_EXEMPT = frozenset({
    "static", "livez", "healthz", "logout", "login", "signup",
    "art_url", "art_placeholder", "kit_asset", "lesson_asset",
    "first_password", "verify_email", "forgot_password", "reset_password",
    # Somebody held on the first-password page can still read what they
    # agreed to. Blocking that would be a strange thing to do.
    "legal",
})


@app.before_request
def _force_password_change():
    """
    Hold an account on the change-password page until it has one of its own.

    Set when somebody else chose the password: a teacher provisioning a
    student, or resetting one who forgot. The password is on a printout by
    then, possibly on the floor of a classroom, so it is worth exactly one
    sign-in. Enforcing it here rather than in each view means a route added
    later is covered by default — the failure mode of forgetting to add it
    to the exempt set is a redirect, not a hole.
    """
    if request.endpoint in _PASSWORD_CHANGE_EXEMPT or not session.get("uid"):
        return None
    user = current_user()
    if not user or not user["must_change_password"]:
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Set a new password before continuing."}), 403
    return redirect(url_for("first_password"))


@app.after_request
def _headers(response):
    return security.apply_headers(response, cfg)


@app.teardown_appcontext
def _teardown(exception=None):
    g.pop("_user", None)
    g.pop("_entitlement", None)


@app.route("/livez")
def livez():
    """
    Liveness: is this process alive and able to answer?

    Touches nothing — no database, no catalog. Point the load balancer and
    the container health check HERE.

    The distinction matters more than it looks. /healthz reports 503 when
    the database is away, and pointing an ALB at that means every task in
    the service goes unhealthy at the same instant during a failover, so
    the whole service gets replaced. The pool reconnects on its own in
    about two seconds, so killing the processes is precisely the wrong
    response to a blip they would otherwise have ridden out.
    """
    return jsonify({"status": "ok"}), 200


@app.route("/healthz")
def healthz():
    """
    Readiness: can this process actually do its job right now?

    Round-trips a real query, so it reports degraded when the database is
    unreachable. Use it for dashboards, alerts and deploy verification —
    not as a load balancer's health check, which should be /livez. See the
    note there.
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
    """Sign this account in.

    Clears anything already in the session first, then records the user id
    together with the session epoch it was issued under, which is what
    lets a password change invalidate every existing cookie. Rotates the
    CSRF token so a token issued before sign-in cannot be replayed after
    it.
    """
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

    This belongs on EVERY authenticated route except the handful that are
    about the account itself (settings, password, billing) or about the
    holding pen (/pending, /locked). It was missing from eight of them —
    including /grownup/link, which let a parent an admin had not approved
    attach themselves to a child with that child's link code and then read
    the child's progress. On an approval-gated organisation that is the
    exact thing approval exists to prevent.

    selftest.t_membership_gate_is_complete() walks the route table and
    fails on any authenticated route that neither carries this nor is on
    its documented exemption list, so the next one cannot be forgotten
    quietly.
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
    """Holding page for a member an admin has not let in yet.

    They have a real account and can sign in; they just cannot reach a
    classroom. Bouncing them here rather than showing a 403 makes it clear
    nothing is broken and somebody just has to approve them.
    """
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
    """Send each role to the screen it actually wants.

    Students land in the classroom, grown-ups on the progress dashboard.
    The login form has role tabs, but they only restyle the panel — this
    is what decides where you end up, so picking the wrong tab is
    harmless.
    """
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if user["role"] in ("teacher", "parent"):
        return redirect(url_for("grownup_home"))
    return redirect(url_for("classroom"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Sign in, without telling an attacker anything they did not already know.

    The order of what follows is deliberate. Rate limiting comes before the
    password check so a locked-out attacker learns nothing from timing. The
    password is then verified even when the username does not exist, against
    a throwaway hash, so a wrong username and a wrong password cost the same
    and the response cannot be used to enumerate accounts. Only after both
    is the account's own state — verification, and later the forced password
    change — allowed to produce a different message.
    """
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

    # Verification gates accounts that HAVE an address. A teacher-provisioned
    # student has email NULL and no inbox to check, so there is nothing to
    # verify and this must not lock them out — the teacher vouched for them
    # by creating the account, which is the whole point of that flow.
    if cfg.REQUIRE_EMAIL_VERIFICATION and user["email"] and not user["email_verified"]:
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
    """
    Send another confirmation link, and say nothing about who has an account.

    Like /forgot below, the response is identical whether or not the address
    exists. A different message here would turn this form into a way to test
    which email addresses have accounts — and this one is reachable without
    signing in, so that list would be free to anybody.
    """
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
    """
    Start a password reset.

    The rate limit wraps the lookup rather than sitting after it, so a
    throttled request does no database work and takes the same path whether
    the address exists or not. Asking again retires any previous link, and
    the flash at the end is identical either way — see the note there.
    """
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


# ── Legal pages ─────────────────────────────────────────────────────────────────
#
# Signup requires ticking a box that says "I agree to the terms". These are
# the pages behind it. They ship as boilerplate — drafted for this product's
# actual shape, but not by a lawyer — and say so in a banner until
# LEGAL_REVIEWED is set.

LEGAL_PAGES = {
    "terms":   ("Terms of Service", "legal/terms.md"),
    "privacy": ("Privacy Notice",   "legal/privacy.md"),
}


def _legal_tokens() -> dict[str, str]:
    """
    The values substituted into the legal Markdown.

    Kept in one place because several of them are numbers that also drive
    behaviour — the grace periods and the invoice due date are read from
    the same config the billing code uses, so the page cannot drift away
    from what the software actually does. That is the whole reason these
    are tokens rather than typed into the prose.
    """
    return {
        "ENTITY":       cfg.LEGAL_ENTITY or "[YOUR COMPANY NAME]",
        "EMAIL":        cfg.LEGAL_EMAIL or "[YOUR CONTACT EMAIL]",
        "ADDRESS":      cfg.LEGAL_ADDRESS or "[YOUR POSTAL ADDRESS]",
        "JURISDICTION": cfg.LEGAL_JURISDICTION or "[YOUR STATE / COUNTRY]",
        "EFFECTIVE":    cfg.LEGAL_EFFECTIVE or "[NOT YET PUBLISHED]",
        "MIN_AGE":            str(cfg.MIN_AGE),
        "INVOICE_DUE_DAYS":   str(cfg.INVOICE_DUE_DAYS),
        "GRACE_DAYS_CARD":    str(cfg.GRACE_DAYS_CARD),
        "GRACE_DAYS_INVOICE": str(cfg.GRACE_DAYS_INVOICE),
    }


def _fill_tokens(markdown_source: str) -> str:
    """
    Replace {{TOKEN}} in the legal Markdown.

    Done before rendering rather than after, so a substituted value cannot
    inject markup — whatever comes out of config is escaped by the Markdown
    renderer along with the rest of the prose.
    """
    for name, value in _legal_tokens().items():
        markdown_source = markdown_source.replace("{{" + name + "}}", value)
    return markdown_source


@app.route("/legal/<page>")
def legal(page: str):
    """
    Terms and Privacy. Public, and readable without an account.

    They have to be: somebody deciding whether to sign up needs to read
    them before they have anywhere to sign in to. That is also why this is
    in _PASSWORD_CHANGE_EXEMPT — a student held on the first-password page
    can still read what they are agreeing to.
    """
    if page not in LEGAL_PAGES:
        abort(404)
    title, source = LEGAL_PAGES[page]

    path = CONTENT_DIR / source
    if not path.is_file():
        log.error("legal page %s is missing from content/", source)
        abort(404)

    body = render_markdown(_fill_tokens(path.read_text(encoding="utf-8")))
    response = make_response(render_template(
        "legal.html", title=title, body=body, page=page,
        reviewed=cfg.LEGAL_REVIEWED))
    # NOT _cached(). The content only changes on deploy, but the page shows
    # "Back" to somebody signed in and "Sign in" to somebody who is not, so
    # it varies by session — and _cached() says `public`, which invites a
    # shared cache to hand one visitor's copy to another. Nothing in front
    # of this app caches today, so that is latent rather than live; it is
    # still the wrong header, and it would become a real leak the first
    # time anyone puts a name on this page.
    response.headers["Cache-Control"] = f"private, max-age={cfg.STATIC_MAX_AGE}"
    response.headers["Vary"] = "Cookie"
    return response


# ── Account settings ────────────────────────────────────────────────────────────

def _settings_template(user: dict) -> str:
    """Students get the game chrome, grown-ups the dashboard chrome.

    Two base templates exist because the two audiences see completely
    different furniture; the settings page is the one screen both reach,
    so it picks its wrapper from the role rather than having two copies.
    """
    return "settings_student.html" if user["role"] == "student" else "settings.html"


@app.route("/settings")
@login_required()
def settings_home():
    """Change your own password, or delete your own account."""
    user = current_user()
    blocker = _deletion_blocker(user)
    return render_template(_settings_template(user),
                           deletable=blocker is None,
                           delete_blocked_reason=blocker)


@app.route("/settings/password", methods=["POST"])
@login_required()
def change_password():
    """
    Change your own password, proving you know the current one first.

    Requiring the old password is what stops a borrowed unlocked laptop
    from becoming a permanent account takeover. db.set_password bumps the
    session epoch, which signs out every other device — including the one
    an attacker might be holding — so this session has to be re-established
    immediately afterwards or the person changing their password would be
    logged out by their own action.
    """
    user = current_user()
    current = request.form.get("current_password", "")
    password = request.form.get("password", "")
    confirm = request.form.get("password_confirm", "")

    def refuse(message: str, status: int = 200):
        flash(message, "error")
        blocker = _deletion_blocker(user)
        return render_template(_settings_template(user),
                               deletable=blocker is None,
                               delete_blocked_reason=blocker), status

    ip = security.client_ip(cfg.TRUSTED_PROXIES)
    if security.over_limit("pwchange_ip", ip, cfg.RL_LOGIN_IP, cfg.RL_WINDOW):
        return refuse("Too many attempts. Wait a few minutes and try again.", 429)

    if not check_password_hash(user["password_hash"], current):
        security.record_attempt("pwchange_ip", ip)
        log.warning("password change refused", extra={"username": user["username"]})
        return refuse("That isn't your current password.")

    problem = security.password_problem(password, confirm)
    if problem:
        return refuse(problem)
    if password == current:
        return refuse("That's the password you already have. Pick a different one.")

    db.set_password(user["id"], generate_password_hash(password))
    # Re-read: set_password moved the epoch, so the row in hand is stale
    # and start_session would store an epoch that no longer validates.
    g.pop("_user", None)
    start_session(db.user_by_id(user["id"]))
    log.info("password changed", extra={"username": user["username"]})
    flash("Password changed. Any other device you were signed in on has been signed out.",
          "success")
    return redirect(url_for("settings_home"))


@app.route("/settings/first-password", methods=["GET", "POST"])
@login_required()
def first_password():
    """
    The one page an account with must_change_password can reach.

    No current-password field: they typed it to get here, and asking a
    ten-year-old to re-enter a code off a printout twice is how you get a
    queue at the teacher's desk. The forced flag is cleared by
    db.set_password writing it false, so completing this is what opens the
    rest of the site.
    """
    user = current_user()
    if not user["must_change_password"]:
        return redirect(url_for("home"))

    if request.method != "POST":
        return render_template("first_password.html")

    password = request.form.get("password", "")
    confirm = request.form.get("password_confirm", "")
    problem = security.password_problem(password, confirm)
    if problem:
        flash(problem, "error")
        return render_template("first_password.html")

    db.set_password(user["id"], generate_password_hash(password))
    g.pop("_user", None)
    start_session(db.user_by_id(user["id"]))
    log.info("first password set", extra={"username": user["username"]})
    flash("You're all set. That's your password now — don't share it.", "success")
    return redirect(url_for("home"))


def _deletion_blocker(user: dict) -> str | None:
    """Why this account cannot delete itself yet, or None if it can.

    Two blockers, both about leaving something stranded rather than about
    the data itself. The last admin of an organisation holds the only keys
    to its roster and its billing, so they have to hand those over before
    they go. A parent with a live subscription would keep being charged
    for a seat nobody holds — deleting our row does not cancel anything at
    Stripe, so the only honest answer is to send them to the portal first.
    """
    if user["role"] == "teacher" and user["org_admin"]:
        if db.count_org_admins(user["org_id"]) <= 1:
            return ("You're the only admin of your organisation. Make another "
                    "teacher an admin first, otherwise nobody can manage the "
                    "roster or the billing after you go.")
    if db.active_paid_subscription_for(user["id"]):
        return ("You have a subscription that's still running. Cancel it in "
                "the billing portal first — deleting your account here would "
                "not stop the charges.")
    return None


@app.route("/settings/delete", methods=["POST"])
@login_required()
def delete_own_account():
    """
    Erase your own account and everything attached to it.

    Guarded three ways, because it is irreversible: the current password,
    typing the word DELETE, and _deletion_blocker() refusing to strand an
    organisation or a live subscription. What actually goes is documented
    on db.delete_user — in short, everything except the invoice rows,
    which are financial records and stay.
    """
    user = current_user()
    blocker = _deletion_blocker(user)
    if blocker:
        flash(blocker, "error")
        return redirect(url_for("settings_home"))

    if not check_password_hash(user["password_hash"], request.form.get("password", "")):
        log.warning("account deletion refused", extra={"username": user["username"]})
        flash("That isn't your current password.", "error")
        return redirect(url_for("settings_home"))

    if request.form.get("confirm", "").strip().upper() != "DELETE":
        flash("Type DELETE in the box to confirm.", "error")
        return redirect(url_for("settings_home"))

    db.delete_user(user["id"])
    session.clear()
    log.info("account deleted", extra={"username": user["username"], "role": user["role"]})
    flash("Your account and everything in it has been deleted.", "success")
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
                           layout=load_room(),
                           summary=summarise(user["id"]),
                           dude_line=random.choice(DUDE_LINES))


@app.route("/lessons")
@login_required("student")
@membership_required
def lessons():
    """
    The lesson menu, organised by track.

    Two independent kinds of gate decide whether a card is open, and they
    are kept apart all the way to the template because they mean different
    things to a student. A paywalled lesson needs a grown-up to buy
    something. A blocked one needs work doing — and which work depends on
    the reason, so the card carries the sentence rather than the template
    guessing from a boolean.

    db.lesson_entries() already returns the student's whole history in one
    query, which is what lets the cross-track requirement checks below cost
    nothing extra: every status they could ask about is already in hand.
    """
    user = current_user()
    entries = db.lesson_entries(user["id"])
    paid_ok = entitlement()["active"]

    available = assigned_lessons(user["id"], load_lessons())
    available_ids = {l["id"] for l in available}

    assigned = db.assigned_lesson_ids(user["id"])
    assigned_ids = None if assigned is None else set(assigned)

    all_tracks = load_tracks()
    by_track = {t["id"]: t for t in all_tracks}
    by_lesson = {l["id"]: l for l in load_lessons()}

    rows = []
    for track in all_tracks:
        # gate() is given the student's own menu, so a lesson a teacher has
        # hidden cannot become an impassable gate mid-track.
        gates = tracks.gate(track, entries, available_ids)
        # A requirement on the track holds every lesson in it, so it is
        # evaluated once here rather than per card.
        track_block = tracks.requirement_block(
            track, entries, by_track, by_lesson, assigned_ids, available_ids)

        cards = []
        for lesson in track["lessons"]:
            if lesson["id"] not in available_ids:
                continue

            block = track_block or tracks.requirement_block(
                lesson, entries, by_track, by_lesson, assigned_ids, available_ids)
            if not block:
                prereq = gates.get(lesson["id"], {"locked": False, "after": None})
                if prereq["locked"]:
                    block = {"reason": tracks.BLOCK_SEQUENCE,
                             "title": prereq["after"],
                             "remedy": f"Finish “{prereq['after']}” first."}

            cards.append({
                **_without_resources(lesson),
                "progress":     entries.get(lesson["id"], {"status": "not_started"}),
                "locked":       not (billing.lesson_is_free(lesson) or paid_ok),
                "prereq_locked": bool(block),
                "prereq_after":  block["title"] if block else None,
                "block_reason":  block["reason"] if block else None,
                "block_remedy":  block["remedy"] if block else None,
            })

        if not cards:
            continue
        rows.append({
            **track,
            "cards":    cards,
            "blocked":  track_block,
            "progress": tracks.progress({**track, "lessons": [c for c in cards]}, entries),
        })

    # Kits are informational and never gate anything, so this is only the
    # count behind the "some of these have kits" note.
    kit_count = sum(1 for t in rows for c in t["cards"] if c.get("kit"))

    return render_template("lessons.html", tracks=rows,
                           kit_count=kit_count,
                           summary=summarise(user["id"]))


@app.route("/lesson/<lesson_id>")
@login_required("student")
@membership_required
def lesson(lesson_id: str):
    """Open one lesson, if this student may.

    Four checks, in order, each with its own remedy:

      unknown lesson      404
      not assigned        403 — a teacher narrowed this student's menu
      needs a subscription  -> /locked, which explains who can buy one
      not reached yet     -> /locked, which names the lesson that opens it

    The menu hides cards that fail these, but the menu can be skipped
    entirely, so this is the check that counts.
    """
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
        return redirect(url_for("locked", lesson_id=lesson_id, why="subscription"))

    # Staged tracks release their lessons in order. Checked here as well as
    # on the menu, because a bookmarked or guessed URL skips the menu.
    blocked_by = prerequisite_block(user["id"], found)
    if blocked_by:
        return redirect(url_for("locked", lesson_id=lesson_id, why="prerequisite"))

    entry = db.lesson_entries(user["id"]).get(lesson_id, {})
    if entry.get("status") != "completed":
        db.set_lesson_status(user["id"], lesson_id, "in_progress")

    body = render_content(found["content"]) if found["type"] == "reading" else None

    # Never ship the answer key to the client — questions are stripped and
    # answers checked server-side in /api/quiz.
    quiz = [{"id": q["id"], "prompt": q["prompt"], "choices": q.get("choices", []),
             "diagram": q.get("diagram")}
            for q in found.get("quiz", [])]

    # Strip the grown-up material before the lesson reaches a student's
    # template. Nothing in lesson.html renders it today, so this changes
    # nothing on screen — it is here so that adding a debug dump, a JSON
    # endpoint or a new partial cannot quietly put an answer key in front of
    # the child it is an answer key for.
    return render_template("lesson.html", lesson=_without_resources(found),
                           entry=entry, body=body, quiz=quiz,
                           summary=summarise(user["id"]))


@app.route("/satchel")
@login_required("student")
@membership_required
def satchel():
    """The student's trinket collection.

    Shows the whole catalogue with the earned ones marked, rather than
    only what they have — the empty slots are the point.
    """
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
@membership_required
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
    if prerequisite_block(user["id"], found):
        return jsonify({"error": "Finish the lesson before this one first."}), 403

    try:
        score = None if body.get("score") is None else max(0, min(int(body["score"]), 100))
    except (TypeError, ValueError):
        score = None

    db.set_lesson_status(user["id"], lesson_id, status, score,
                         reward=found.get("reward"))
    return jsonify({"ok": True, "summary": summarise(user["id"])})


@app.route("/api/quiz", methods=["POST"])
@login_required("student")
@membership_required
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
    if prerequisite_block(user["id"], found):
        return jsonify({"error": "Finish the lesson before this one first."}), 403

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
@membership_required
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
    if prerequisite_block(current_user()["id"], found):
        return jsonify({"error": "Finish the lesson before this one first."}), 403
    stripped = [{"id": e["id"], "prompt": e["prompt"], "choices": e.get("choices", [])}
                for e in found.get("examples", [])]
    return jsonify(stripped)


@app.route("/api/example", methods=["POST"])
@login_required("student")
@membership_required
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
    if prerequisite_block(user["id"], found):
        return jsonify({"error": "Finish the lesson before this one first."}), 403

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
@membership_required
def api_quiz_finish():
    """Score the quiz, complete the lesson, and hand back any reward earned."""
    user = current_user()
    body = request.get_json(silent=True) or {}

    found = get_lesson(body.get("lesson_id", ""))
    if not found:
        return jsonify({"error": "Unknown lesson."}), 400
    if not billing.lesson_is_free(found) and not entitlement()["active"]:
        return jsonify({"error": "That lesson needs an active subscription."}), 402
    if prerequisite_block(user["id"], found):
        return jsonify({"error": "Finish the lesson before this one first."}), 403

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
@membership_required
def student_detail(username: str):
    """One student's full progress, for a grown-up.

    _visible_student_or_404() is the gate: a teacher only reaches students
    in their own classrooms, a parent only their linked children, and
    anyone else gets a 404 rather than a 403 so the response cannot be
    used to discover which usernames exist.
    """
    user = current_user()
    student = _visible_student_or_404(user, username)

    entries = db.lesson_entries(student["id"])
    assigned = db.assigned_lesson_ids(student["id"])
    assigned_ids = None if assigned is None else set(assigned)
    summary = summarise(student["id"])

    grade, grade_source = _grade_for(student, request.args.get("grade"))
    lessons = load_lessons()
    all_tracks = load_tracks()
    by_track = {t["id"]: t for t in all_tracks}
    by_lesson = {l["id"]: l for l in lessons}

    rows = []
    for track in all_tracks:
        track_block = tracks.requirement_block(
            track, entries, by_track, by_lesson, assigned_ids, assigned_ids)
        gates = tracks.gate(track, entries, assigned_ids)
        for item in track["lessons"]:
            entry = entries.get(item["id"], {"status": "not_started"})
            block = track_block or tracks.requirement_block(
                item, entries, by_track, by_lesson, assigned_ids, assigned_ids)
            if not block:
                state = gates.get(item["id"], {"locked": False, "after": None})
                if state["locked"]:
                    block = {"reason": tracks.BLOCK_SEQUENCE, "title": state["after"],
                             "remedy": f"Finish “{state['after']}” first."}
            rows.append({
                **item,
                # Filtered by who is looking: a resource marked for home is
                # not shown to a teacher.
                "resources": tracks.visible_resources(
                    item.get("resources") or [], user["role"]),
                "track_title": track["title"],
                "progress": entry,
                "score":    quiz_score(item, entry),
                "assigned": assigned_ids is None or item["id"] in assigned_ids,
                "block":    block,
                # Where this sits relative to the grade being viewed, which
                # is what the grown-up page groups on.
                "fit": _fit(item.get("band"), grade),
            })

    sticking = sticking_points(student["id"], entries)
    unresolved = len([s for s in sticking if not s["resolved"]])

    # The tracker's own numbers, so the page can lead with where this child
    # stands against their grade rather than with a list of our lessons.
    statuses = {r["id"]: r["progress"].get("status", "not_started") for r in rows}
    report = standards.report(load_frameworks(), lessons, grade, statuses)

    return render_template("student.html",
                           student=student,
                           rows=rows,
                           groups=_group_by_fit(rows),
                           report=report,
                           grade=grade,
                           grade_source=grade_source,
                           grade_label=standards.grade_label,
                           grades=list(range(0, standards.LAST_GRADE + 1)),
                           summary=summary,
                           headline=headline(summary, unresolved),
                           sticking=sticking,
                           practice=practice_examples(student["id"], entries),
                           activity=recent_activity(entries),
                           quiet=days_since(summary["last_active"]),
                           is_teacher=user["role"] == "teacher",
                           custom_assignment=assigned_ids is not None)


# How a lesson's age band sits against the grade being looked at. The
# grown-up view groups on this, because "what should my child be doing now"
# is the question they came with — and a lesson three years ahead is not a
# gap, it is next year.
FIT_ON = "on"          # this grade is inside the lesson's band
FIT_BELOW = "below"    # the band ends before this grade: revision
FIT_ABOVE = "above"    # the band starts after it: later
FIT_UNKNOWN = "unknown"  # no band stated, so we say nothing

_FIT_ORDER = [FIT_ON, FIT_ABOVE, FIT_BELOW, FIT_UNKNOWN]
_FIT_TITLES = {
    FIT_ON:      "At this grade",
    FIT_ABOVE:   "Ahead of this grade",
    FIT_BELOW:   "Below this grade",
    FIT_UNKNOWN: "No age given",
}


def _fit(band: dict | None, grade: int) -> str:
    """
    Where a lesson's age band sits relative to the grade being viewed.

    "Above" means the lesson is aimed HIGHER than this grade — it is ahead
    of them, not beneath them — which is the opposite of what the word
    suggests if you read it as a position in a list. No band at all is
    FIT_UNKNOWN rather than a guess, so the page can say nothing instead of
    filing the lesson under a grade nobody chose for it.
    """
    if not band or not band.get("grades"):
        return FIT_UNKNOWN
    grades = band["grades"]
    if grade in grades:
        return FIT_ON
    return FIT_ABOVE if grade < grades[0] else FIT_BELOW


def _group_by_fit(rows: list[dict]) -> list[dict]:
    """Lesson rows bucketed by how they sit against the grade on screen."""
    buckets: dict[str, list[dict]] = {}
    for row in rows:
        buckets.setdefault(row["fit"], []).append(row)
    return [{"fit": fit, "title": _FIT_TITLES[fit], "rows": buckets[fit]}
            for fit in _FIT_ORDER if buckets.get(fit)]


# ── Grown-up resources ──────────────────────────────────────────────────────────
#
# Downloadable material attached to a lesson or a track — a parent guide, an
# answer key, a worksheet — that a student must never see.
#
# WHERE THESE FILES LIVE IS THE WHOLE SECURITY DESIGN. There are two
# existing ways to serve a file in this app and BOTH are open to everybody:
#
#   /static/...            nginx aliases it straight off disk. No Python
#                          runs. There is nothing to authenticate against.
#   /lessons/<id>/<file>   deliberately unauthenticated, because lesson
#                          artwork has to load inside the game frame.
#
# Putting an answer key in either would hand it to every student with a
# browser and a guess. So resources live in their own directory, are served
# only through the route below, and that route serves ONLY files a manifest
# actually names — a whitelist, so a traversal attempt has nothing to
# traverse to even if the filename checks in tracks.resources() were wrong.

_RESOURCE_OWNERS = ("lesson", "track")


def _resource_owner(kind: str, owner_id: str) -> dict | None:
    """The lesson or track a resource hangs off, or None."""
    if kind == "lesson":
        return get_lesson(owner_id)
    if kind == "track":
        return next((t for t in load_tracks() if t["id"] == owner_id), None)
    return None


def _resource_or_404(kind: str, owner_id: str, filename: str, role: str) -> tuple[dict, dict]:
    """
    Resolve (owner, resource) for a download, or 404.

    The whitelist: `filename` has to appear in this owner's own manifest and
    be visible to this role. A file sitting in the directory that no
    manifest mentions is not servable, which means an accidental commit of
    something private cannot be fetched by guessing its name.

    404 rather than 403 throughout, so the response cannot be used to
    discover which resources exist.
    """
    if kind not in _RESOURCE_OWNERS:
        abort(404)
    owner = _resource_owner(kind, owner_id)
    if not owner:
        abort(404)

    allowed = tracks.visible_resources(owner.get("resources") or [], role)
    resource = next((r for r in allowed if r["file"] and r["file"] == filename), None)
    if not resource:
        abort(404)
    return owner, resource


def _resource_paywalled(owner: dict, kind: str) -> bool:
    """
    Whether this owner's material needs a subscription.

    Mirrors the lesson it belongs to rather than having a rule of its own:
    a guide to a free lesson is free, a guide to a subscriber lesson is not.
    Anything else would either sell help nobody needs or give away the
    answer keys for the paid content.
    """
    if entitlement()["active"]:
        return False
    if kind == "lesson":
        return not billing.lesson_is_free(owner)
    # A track's own material is free when any lesson in it is.
    return not any(billing.lesson_is_free(l) for l in owner.get("lessons") or [])


@app.route("/grownup/resources")
@login_required("parent", "teacher")
@membership_required
def resources_home():
    """
    Everything a grown-up can download, by track.

    Teachers see the shared material; parents see that plus anything marked
    for home only. Students cannot reach this route at all — the role list
    on login_required is the first of the three checks, the second is
    tracks.visible_resources() below, and the third is on the download
    itself.
    """
    user = current_user()
    role = user["role"]

    groups = []
    for track in load_tracks():
        track_items = tracks.visible_resources(track.get("resources") or [], role)
        lessons = []
        for lesson in track["lessons"]:
            items = tracks.visible_resources(lesson.get("resources") or [], role)
            if items:
                lessons.append({
                    "id": lesson["id"], "title": lesson["title"],
                    "band_label": lesson.get("band_label", ""),
                    "resources": items,
                    "locked": _resource_paywalled(lesson, "lesson"),
                })
        if track_items or lessons:
            groups.append({
                "id": track["id"], "title": track["title"],
                "description": track.get("description", ""),
                "band_label": track.get("band_label", ""),
                "skills": track.get("skills") or [],
                "resources": track_items,
                "locked": _resource_paywalled(track, "track"),
                "lessons": lessons,
            })

    return render_template("resources.html", groups=groups, role=role)


@app.route("/grownup/resources/<kind>/<owner_id>/<path:filename>")
@login_required("parent", "teacher")
@membership_required
def resource_download(kind: str, owner_id: str, filename: str):
    """
    Hand over one file, to a grown-up who is allowed it.

    Sent as an attachment with `Cache-Control: private, no-store`: these go
    out over the same connection as the student's own pages, and a shared
    or browser cache holding an answer key would undo the whole point.
    """
    user = current_user()
    owner, resource = _resource_or_404(kind, owner_id, filename, user["role"])

    if _resource_paywalled(owner, kind):
        return redirect(url_for("locked", lesson_id=owner_id))

    directory = RESOURCES_DIR / f"{kind}s" / owner_id
    if not (directory / filename).is_file():
        log.error("resource %s/%s/%s is in the manifest but not on disk",
                  kind, owner_id, filename)
        abort(404)

    log.info("resource downloaded",
             extra={"username": user["username"], "resource": f"{kind}/{owner_id}/{filename}"})
    response = make_response(send_from_directory(directory, filename, as_attachment=True))
    response.headers["Cache-Control"] = "private, no-store"
    return response


@app.route("/grownup/resources/<kind>/<owner_id>/<path:filename>/read")
@login_required("parent", "teacher")
@membership_required
def resource_read(kind: str, owner_id: str, filename: str):
    """
    Read a Markdown guide in the browser rather than downloading it.

    Most of these get opened on a phone at a kitchen table, where a
    downloaded .md file is useless. Only text renders; anything else is
    sent to the download route instead of being guessed at.
    """
    user = current_user()
    owner, resource = _resource_or_404(kind, owner_id, filename, user["role"])

    if _resource_paywalled(owner, kind):
        return redirect(url_for("locked", lesson_id=owner_id))

    path = RESOURCES_DIR / f"{kind}s" / owner_id / filename
    if path.suffix.lower() not in (".md", ".markdown", ".txt"):
        return redirect(url_for("resource_download", kind=kind, owner_id=owner_id,
                                filename=filename))
    if not path.is_file():
        abort(404)

    body = render_markdown(path.read_text(encoding="utf-8", errors="replace"))
    response = make_response(render_template(
        "resource.html", owner=owner, owner_kind=kind, resource=resource, body=body))
    response.headers["Cache-Control"] = "private, no-store"
    return response


# ── Curriculum tracker ──────────────────────────────────────────────────────────
#
# The parent-facing question this answers: "for a kid this age, what is a
# US student expected to be able to do, and where has mine actually got to?"
#
# Everything here leans on standards.py, which carries the long version of
# why this is harder than it sounds. The short version, which the screen
# itself also says: there is no national curriculum, so "the standards" are
# whichever ones a state adopted, and the alignment between our lessons and
# any of them is our own reading.

@app.route("/grownup/student/<username>/standards")
@login_required("parent", "teacher")
@membership_required
def student_standards(username: str):
    """
    One student against one grade's standards.

    Visibility runs through _visible_student_or_404() like every other
    student screen, so a parent sees only their own children and a teacher
    only the classrooms they are assigned to. The tracker adds no new way
    to see a child.

    The grade comes from ?grade= if given, else the student's recorded
    grade, else a guess from the age floor — and which of those three it
    was is passed to the template, because "we guessed" and "their parent
    told us" should not look the same on screen.
    """
    user = current_user()
    student = _visible_student_or_404(user, username)

    grade, source = _grade_for(student, request.args.get("grade"))

    lessons = load_lessons()
    statuses = db.lesson_statuses(student["id"], [l["id"] for l in lessons])
    report = standards.report(load_frameworks(), lessons, grade, statuses)

    return render_template("standards.html",
                           student=student,
                           report=report,
                           grade_source=source,
                           grades=list(range(0, standards.LAST_GRADE + 1)),
                           grade_label=standards.grade_label,
                           is_teacher=user["role"] == "teacher")


def _grade_for(student: dict, requested: str | None) -> tuple[int, str]:
    """
    Which grade to measure against, and where that number came from.

    Three sources, worst last. The guess exists so the page shows something
    useful before anyone has set a grade, but it is labelled as a guess
    every time: we hold no date of birth, only the age floor a student
    attested to at signup, and grade cut-offs vary by state anyway.
    """
    if requested:
        try:
            asked = int(requested)
        except ValueError:
            asked = None
        if asked is not None and 0 <= asked <= standards.LAST_GRADE:
            return asked, "chosen"

    if student.get("grade_level") is not None:
        return student["grade_level"], "recorded"

    return standards.grade_for_age(cfg.MIN_AGE), "guessed"


@app.route("/grownup/student/<username>/grade", methods=["POST"])
@login_required("parent", "teacher")
@membership_required
def set_student_grade(username: str):
    """
    Record which grade a student is in.

    Open to a parent as well as a teacher: for a homeschooling family the
    parent is the only person who knows, and this is the one fact the
    tracker cannot work properly without. Clearing it back to "not set" is
    allowed — an empty answer is better than a wrong one.
    """
    user = current_user()
    student = _visible_student_or_404(user, username)

    raw = (request.form.get("grade_level") or "").strip()
    grade = None
    if raw:
        try:
            grade = int(raw)
        except ValueError:
            flash("Pick a grade from the list.", "error")
            return redirect(url_for("student_standards", username=username))

    try:
        db.set_grade_level(student["id"], grade)
    except ValueError:
        flash("That is not a grade between kindergarten and 12.", "error")
        return redirect(url_for("student_standards", username=username))

    if grade is None:
        flash(f"Cleared {student['name']}'s grade.", "success")
    else:
        flash(f"{student['name']} is in {standards.grade_label(grade)}.", "success")
    return redirect(url_for("student_standards", username=username))


@app.route("/grownup/student/<username>/assign", methods=["POST"])
@login_required("teacher", "parent")
@membership_required
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
@membership_required
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


# ── Classrooms ──────────────────────────────────────────────────────────────────
#
# A classroom is the roster a teacher is assigned to, and it is what decides
# which students that teacher can see anywhere in the app.
#
# Who may do what, and why:
#
#   org admin   creates classrooms, assigns teachers, moves students in and
#               out. They see the whole organisation already.
#   teacher     sees the classrooms they run and the students in them, and
#               nothing else.
#
# Roster changes are admin-only on purpose. If an ordinary teacher could add
# any student in the organisation to their own classroom, they could see any
# student by adding them — which is exactly the boundary classrooms exist to
# draw. Relaxing that is a deliberate decision, not an oversight.

@app.route("/classrooms")
@login_required("teacher")
@membership_required
def classrooms_home():
    """Every classroom this account may see.

    An admin gets the whole organisation, plus the students nobody has
    placed in a classroom yet — those are invisible to ordinary teachers,
    so if the admin does not see them, nobody will.

    A teacher gets the classrooms they are assigned to, and an explanation
    rather than a blank page when that is none of them.
    """
    user = current_user()
    is_admin = bool(user["org_admin"])

    # An admin sees every classroom in the organisation; a teacher sees the
    # ones they actually run.
    rows = db.classroom_rows(user["org_id"], None if is_admin else user["id"])

    students = db.visible_students(user)
    ids = [s["id"] for s in students]
    summaries = summarise_many(ids)
    stuck_counts = db.unresolved_counts(ids, _catalog["valid_pairs"])

    # One query for the whole organisation's memberships, then matched in
    # memory — rather than a query per classroom card.
    membership = db.classroom_membership(user["org_id"])

    cards = []
    for row in rows:
        members = membership.get(row["id"], [])
        stats = [summaries[m] for m in members if m in summaries]
        cards.append({
            "id":       row["id"],
            "name":     row["name"],
            "students": row["students"],
            "teachers": row["teachers"],
            "avg":      round(sum(s["percent"] for s in stats) / len(stats)) if stats else 0,
            "stuck":    sum(stuck_counts.get(m, 0) for m in members),
        })

    return render_template("classrooms.html",
                           classrooms=cards,
                           is_admin=is_admin,
                           unplaced=db.unplaced_students(user["org_id"]) if is_admin else [],
                           student_count=len(students),
                           lesson_count=len(load_lessons()))


def _classroom_or_404(user: dict, classroom_id: int) -> dict:
    """
    Resolve a classroom this account may open.

    Scoped by org first, then by assignment for a non-admin. 404 rather than
    403 throughout, so the response cannot be used to discover which
    classrooms exist elsewhere.
    """
    classroom = db.classroom_in_org(classroom_id, user["org_id"])
    if not classroom:
        abort(404)
    if not user["org_admin"] and not db.teaches_classroom(user["id"], classroom_id):
        abort(404)
    return classroom


@app.route("/classrooms/new", methods=["POST"])
@org_admin_required
def classroom_create():
    """Create a classroom and put its creator in it.

    The admin who makes a classroom is assigned to it straight away.
    Without that a brand new classroom belongs to nobody, and would drop
    off the list of every teacher including the one who just made it.
    """
    user = current_user()
    name = request.form.get("name", "").strip()
    if not name:
        flash("Give the classroom a name.", "error")
        return redirect(url_for("classrooms_home"))

    classroom_id = db.create_classroom(user["org_id"], name[:120], user["id"])
    # The admin who made it is its first teacher; otherwise a brand new
    # classroom belongs to nobody and drops off every teacher's screen.
    db.add_classroom_teacher(classroom_id, user["id"])

    flash(f"Created “{name}”.", "success")
    return redirect(url_for("classroom_detail", classroom_id=classroom_id))


@app.route("/classrooms/<int:classroom_id>")
@login_required("teacher")
@membership_required
def classroom_detail(classroom_id: int):
    """One classroom: who teaches it, who is in it, how they are doing.

    Reachable by an admin, or by a teacher assigned to this classroom —
    _classroom_or_404() enforces both, in that order. The add/remove
    controls are only rendered for an admin, and separately refused
    server-side; a hidden form is not a permission check.
    """
    user = current_user()
    classroom = _classroom_or_404(user, classroom_id)

    roster = db.classroom_students(classroom_id)
    ids = [m["id"] for m in roster]
    summaries = summarise_many(ids)
    stuck_counts = db.unresolved_counts(ids, _catalog["valid_pairs"])

    students = []
    for row in roster:
        summary = summaries[row["id"]]
        students.append({
            "id":       row["id"],
            "username": row["username"],
            "name":     row["name"],
            "link_code": row["link_code"],
            "headline": headline(summary, stuck_counts.get(row["id"], 0)),
            "stuck":    stuck_counts.get(row["id"], 0),
            **summary,
        })

    # Only an admin can change the roster, so only an admin needs the lists
    # of who could be added.
    in_class = set(ids)
    addable, addable_teachers = [], []
    if user["org_admin"]:
        addable = [{"id": s["id"], "username": s["username"], "name": s["name"]}
                   for s in db.visible_students(user) if s["id"] not in in_class]
        assigned = {t["id"] for t in db.classroom_teachers(classroom_id)}
        addable_teachers = [t for t in db.org_teachers(user["org_id"])
                            if t["id"] not in assigned]

    return render_template("classroom_detail.html",
                           classroom=classroom,
                           students=students,
                           teachers=db.classroom_teachers(classroom_id),
                           addable=addable,
                           addable_teachers=addable_teachers,
                           is_admin=bool(user["org_admin"]))


@app.route("/classrooms/<int:classroom_id>/students/add", methods=["POST"])
@org_admin_required
def classroom_add_student(classroom_id: int):
    """Put a student in a classroom, which is what lets its teachers see them.

    Admin-only, and the student is resolved through
    _visible_student_or_404() so an id from another organisation cannot be
    posted in.
    """
    user = current_user()
    _classroom_or_404(user, classroom_id)
    student = _visible_student_or_404(user, request.form.get("username", ""))

    db.add_classroom_student(classroom_id, student["id"])
    flash(f"Added {student['name']}.", "success")
    return redirect(url_for("classroom_detail", classroom_id=classroom_id))


@app.route("/classrooms/<int:classroom_id>/students/remove", methods=["POST"])
@org_admin_required
def classroom_remove_student(classroom_id: int):
    """Take a student out of a classroom.

    Their work is untouched — only the membership goes, and with it the
    classroom's teachers' sight of them.
    """
    user = current_user()
    _classroom_or_404(user, classroom_id)
    student = _visible_student_or_404(user, request.form.get("username", ""))

    db.remove_classroom_student(classroom_id, student["id"])
    flash(f"Removed {student['name']} from this classroom.", "success")
    return redirect(url_for("classroom_detail", classroom_id=classroom_id))


@app.route("/classrooms/<int:classroom_id>/teachers/add", methods=["POST"])
@org_admin_required
def classroom_add_teacher(classroom_id: int):
    """Assign a teacher to a classroom.

    This is the grant that gives them sight of its students, so it is
    admin-only and the account is resolved within the organisation first.
    Students cannot be assigned: being a teacher of a classroom means
    seeing other people's children.
    """
    user = current_user()
    _classroom_or_404(user, classroom_id)
    teacher = _member_or_404(user, request.form.get("teacher_id", ""))
    if teacher["role"] != "teacher":
        abort(404)

    db.add_classroom_teacher(classroom_id, teacher["id"])
    flash(f"{teacher['name']} now teaches this classroom.", "success")
    return redirect(url_for("classroom_detail", classroom_id=classroom_id))


@app.route("/classrooms/<int:classroom_id>/teachers/remove", methods=["POST"])
@org_admin_required
def classroom_remove_teacher(classroom_id: int):
    """Unassign a teacher, revoking their sight of that classroom's students.

    Removing the last teacher is allowed and leaves the classroom visible
    only to admins. The screen says so rather than silently stranding it.
    """
    user = current_user()
    _classroom_or_404(user, classroom_id)
    teacher = _member_or_404(user, request.form.get("teacher_id", ""))

    db.remove_classroom_teacher(classroom_id, teacher["id"])
    flash(f"{teacher['name']} no longer teaches this classroom.", "success")
    return redirect(url_for("classroom_detail", classroom_id=classroom_id))


@app.route("/classrooms/<int:classroom_id>/delete", methods=["POST"])
@org_admin_required
def classroom_delete(classroom_id: int):
    """Delete a classroom.

    The students stay in the organisation and keep every bit of their
    work; only the roster and its teacher assignments go.
    """
    user = current_user()
    name = db.delete_classroom(classroom_id, user["org_id"])
    if name:
        flash(f"Deleted “{name}”. The students are still in the class.", "success")
    return redirect(url_for("classrooms_home"))



# ── Provisioning student accounts ───────────────────────────────────────────────
#
# The self-serve signup form asks for an email address and sends a
# confirmation link. That works for a parent at a kitchen table and fails
# completely for a class of twenty-eight, half of whom have no inbox and
# the other half of whom are on a district account that drops outside mail.
# So a teacher can create the accounts directly: usernames they choose,
# passwords the system generates and they hand out on paper, and no email
# anywhere in the loop.

# One import at a time, so a pasted spreadsheet cannot become a
# denial-of-service against the seat count or the database.
_MAX_IMPORT = 200


def _username_from_name(name: str, taken: set[str]) -> str | None:
    """
    Derive a free username from a display name.

    "Ada Lovelace" becomes "ada.lovelace", then "ada.lovelace2" and so on.
    `taken` carries the names claimed earlier in the same import, which the
    database cannot tell us about yet because those rows are still being
    written in this transaction.

    Returns None if the name has nothing usable in it — no letters or
    digits at all — rather than inventing a username nobody can read out.
    """
    cleaned = re.sub(r"[^a-z0-9]+", ".", name.strip().lower()).strip(".")
    if not cleaned:
        return None
    base = cleaned[:28] or "student"
    if len(base) < 3:
        base = f"{base}.s"
    candidate = base
    for suffix in range(2, 500):
        if candidate not in taken and not db.username_taken(candidate):
            return candidate
        candidate = f"{base}{suffix}"
    return None


def _provision_student(cur, *, org_id: int, classroom_id: int, name: str,
                       username: str, by_user_id: int) -> dict:
    """
    Create one student account and put it in the classroom.

    Runs inside the caller's transaction so a bulk import is all-or-nothing
    per row. Returns the generated password alongside the username — this
    is the only moment either the teacher or we will ever see it, since
    only its hash is stored.
    """
    password = security.temp_password()
    db.create_student_in_classroom(
        cur, org_id=org_id, classroom_id=classroom_id, username=username,
        name=name, password_hash=generate_password_hash(password),
        by_user_id=by_user_id)
    return {"name": name, "username": username, "password": password}


@app.route("/classrooms/<int:classroom_id>/students/new", methods=["POST"])
@login_required("teacher")
@membership_required
def classroom_new_student(classroom_id: int):
    """
    Create one student account straight into this classroom.

    Open to any teacher of the classroom, not just an admin:
    _classroom_or_404 already refused anyone who does not teach it, and
    making a teacher wait for an admin to enrol their own class is the
    friction this whole flow exists to remove.
    """
    user = current_user()
    _classroom_or_404(user, classroom_id)

    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip().lower()

    def back(message: str, category: str = "error"):
        flash(message, category)
        return redirect(url_for("classroom_detail", classroom_id=classroom_id))

    if not name:
        return back("Enter the student's name.")
    if not request.form.get("consent_ok"):
        return back("Confirm you have permission to create accounts for these students.")

    if username:
        problem = security.username_problem(username)
        if problem:
            return back(problem)
        if db.username_taken(username):
            return back(f"The username “{username}” is taken. Pick another.")
    else:
        username = _username_from_name(name, set())
        if not username:
            return back("That name has no letters or numbers in it to build a username from.")

    try:
        with db.write() as cur:
            created = _provision_student(cur, org_id=user["org_id"],
                                         classroom_id=classroom_id, name=name,
                                         username=username, by_user_id=user["id"])
    except psycopg.errors.UniqueViolation:
        return back("That username was just taken. Try another.")

    _resize_org_seats(user["org_id"])
    log.info("student provisioned",
             extra={"username": username, "by": user["username"], "org_id": user["org_id"]})

    # The password is shown once, here, and never again — only its hash is
    # stored. Rendering the results page rather than flashing it keeps it
    # off every subsequent screen and out of the session cookie.
    return render_template("roster_result.html",
                           classroom=db.classroom_in_org(classroom_id, user["org_id"]),
                           created=[created], failed=[])


@app.route("/classrooms/<int:classroom_id>/students/import", methods=["GET", "POST"])
@login_required("teacher")
@membership_required
def classroom_import_students(classroom_id: int):
    """
    Create a whole class at once from a pasted list.

    One student per line: a name, optionally followed by a comma and the
    username to give them. A header row saying "name,username" is ignored
    if present, because every spreadsheet export has one.

    Rows are independent. A duplicate username or an unusable name fails
    that row and the rest still go through, reported side by side on the
    results page — an import of thirty students should not be defeated by
    one typo on line nine.
    """
    user = current_user()
    classroom = _classroom_or_404(user, classroom_id)

    if request.method != "POST":
        return render_template("roster_import.html", classroom=classroom)

    raw = request.form.get("roster", "")
    if request.files.get("roster_file"):
        # Decoded leniently: these files come out of Excel on a school
        # laptop and are as likely to be cp1252 as UTF-8. Mangling one
        # accented character beats refusing the whole import.
        raw = request.files["roster_file"].read(512_000).decode("utf-8", "replace")

    if not request.form.get("consent_ok"):
        flash("Confirm you have permission to create accounts for these students.", "error")
        return render_template("roster_import.html", classroom=classroom, roster=raw)

    rows = _parse_roster(raw)
    if not rows:
        flash("No students found in that list. One name per line.", "error")
        return render_template("roster_import.html", classroom=classroom, roster=raw)
    if len(rows) > _MAX_IMPORT:
        flash(f"That's {len(rows)} students. Import at most {_MAX_IMPORT} at a time.", "error")
        return render_template("roster_import.html", classroom=classroom, roster=raw)

    created, failed = [], []
    claimed: set[str] = set()
    for name, wanted in rows:
        username = wanted
        if username:
            problem = security.username_problem(username)
            if problem:
                failed.append({"name": name, "reason": problem})
                continue
            if username in claimed or db.username_taken(username):
                failed.append({"name": name, "reason": f"Username “{username}” is taken."})
                continue
        else:
            username = _username_from_name(name, claimed)
            if not username:
                failed.append({"name": name, "reason": "No letters or numbers to build a username from."})
                continue

        try:
            # A transaction per row, so one failure rolls back only itself.
            with db.write() as cur:
                created.append(_provision_student(
                    cur, org_id=user["org_id"], classroom_id=classroom_id,
                    name=name, username=username, by_user_id=user["id"]))
            claimed.add(username)
        except psycopg.errors.UniqueViolation:
            failed.append({"name": name, "reason": f"Username “{username}” was just taken."})
        except Exception:
            log.exception("roster import row failed")
            failed.append({"name": name, "reason": "Something went wrong creating this account."})

    if created:
        _resize_org_seats(user["org_id"])
    # Not "created": logging.LogRecord already has that attribute (the
    # record's own timestamp) and makeRecord raises rather than let an
    # extra shadow it, which turns the log line into a 500.
    log.info("roster imported",
             extra={"by": user["username"],
                    "accounts_created": len(created),
                    "accounts_failed": len(failed)})

    return render_template("roster_result.html", classroom=classroom,
                           created=created, failed=failed)


def _parse_roster(raw: str) -> list[tuple[str, str]]:
    """
    Turn pasted text into (name, requested_username) pairs.

    Tolerant by design: blank lines go, a leading header row goes, quotes
    and stray whitespace are stripped, and anything past the second column
    is ignored so a spreadsheet with extra columns still imports. The
    username is lowercased here because usernames are matched
    case-insensitively and a teacher typing "Ada.L" should get what they
    expect.
    """
    rows: list[tuple[str, str]] = []
    for line in csv.reader(io.StringIO(raw)):
        if not line:
            continue
        name = line[0].strip()
        username = (line[1].strip().lower() if len(line) > 1 else "")
        if not name:
            continue
        if not rows and name.lower() in ("name", "student", "full name", "student name"):
            continue
        rows.append((name, username))
    return rows


@app.route("/grownup/student/<username>/reset-password", methods=["POST"])
@login_required("teacher")
@membership_required
def student_reset_password(username: str):
    """
    Give a student a new password, because they forgot theirs.

    The reason this exists: the email reset loop is useless to a student
    with no email address, and most of them have none. A teacher who can
    already see all of this student's work is not gaining anything by
    being able to reset their password, so this is open to any teacher of
    their classroom rather than admins only.

    Restricted to students on purpose. A teacher must not be able to reset
    another teacher's or a parent's password — that would turn any
    compromised teacher account into a way to take over the org admin's,
    and grown-ups have email addresses and the ordinary reset flow.
    """
    user = current_user()
    student = _visible_student_or_404(user, username)

    password = security.temp_password()
    db.set_password(student["id"], generate_password_hash(password), must_change=True)
    security.clear_attempts("login_user", student["username"])
    log.info("student password reset by teacher",
             extra={"username": student["username"], "by": user["username"]})

    return render_template("roster_result.html",
                           classroom=None,
                           reset=True,
                           created=[{"name": student["name"],
                                     "username": student["username"],
                                     "password": password}],
                           failed=[])


@app.route("/grownup/student/<username>/delete", methods=["POST"])
@org_admin_required
def student_delete(username: str):
    """
    Erase a student account on request.

    Admin-only, unlike the password reset. A reset is recoverable and
    routine; this is neither, so it sits with the person who answers for
    the organisation. What goes and what stays is documented on
    db.delete_user.
    """
    user = current_user()
    student = _visible_student_or_404(user, username)

    if request.form.get("confirm", "").strip().upper() != "DELETE":
        flash("Type DELETE to confirm.", "error")
        return redirect(url_for("student_detail", username=username))

    db.delete_user(student["id"])
    _resize_org_seats(user["org_id"])
    log.info("student deleted",
             extra={"username": student["username"], "by": user["username"]})
    flash(f"Deleted {student['name']} and all of their work.", "success")
    return redirect(url_for("grownup_home"))


# ── Locked lesson ───────────────────────────────────────────────────────────────

@app.route("/locked")
@login_required()
def locked():
    """
    Where a student lands on a lesson that will not open.

    Two quite different situations share this page, and it says which:

      prerequisite  the track is staged and they have not reached this one.
                    Nothing to buy; go and finish the lesson before it.
      subscription  nobody is paying for their account.

    Deliberately not a 402 with a Buy button: a 13-year-old is not the
    payer, so this tells them who to ask rather than selling to them.
    """
    user = current_user()
    lesson = get_lesson(request.args.get("lesson_id", "")) or None
    why = request.args.get("why", "subscription")

    blocked = None
    if lesson and user["role"] == "student":
        blocked = prerequisite_block(user["id"], lesson)
    # Trust the recomputed answer over the query string, which a student
    # can type anything into.
    if blocked:
        why = "prerequisite"
    elif why == "prerequisite":
        why = "subscription"

    return render_template("locked.html", lesson=lesson, why=why, blocked=blocked,
                           entitlement=entitlement()), (403 if why == "prerequisite" else 402)


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
    """
    Put a member out of the organisation.

    Removing yourself is refused: an admin who did it by accident would
    lock themselves out of the org they administer, and there is no
    self-service way back in. Their work is untouched — the membership goes,
    not the account, which is what /settings/delete is for.
    """
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
    """
    Promote a teacher to admin, or demote one.

    Two guards. An organisation must keep at least one admin, or nobody can
    manage its roster or its billing and there is no way to appoint someone
    from inside. And only teachers can hold it: admin carries sight of every
    student in the org, which is not a thing to hand a student or a parent.
    """
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
    """
    Stripe telling us something changed.

    The only route in the app exempt from CSRF, because the caller is Stripe
    and has no session or token to present. What replaces CSRF is the
    signature check below: the body is verified against the exact bytes
    Stripe sent, so anything that re-reads or re-encodes it first breaks
    verification.

    Then idempotency. Stripe retries, and retries can arrive out of order or
    twice, so the event id is CLAIMED in the database before any work
    happens and released again if that work throws. Applying one event
    twice would double-count a seat or extend a subscription that never
    renewed.

    Failures answer 500 on purpose: Stripe treats that as "try again",
    which is what we want. A 200 would tell it the event was handled and it
    would never come back.
    """
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

    Opening the pool never blocks and never fails the boot: a worker that
    starts during a database blip comes up anyway and reconnects by itself,
    rather than dying and turning a short outage into a crash loop.

    Migrations are the one thing that genuinely needs a live database, so
    they wait for one — with a budget, and then loudly. In production they
    should not run here at all: apply them in a pre-deploy step and set
    RUN_MIGRATIONS=0, which also avoids old tasks meeting a new schema
    mid-rollout. See docs/AWS_READINESS.md.

    They take a Postgres advisory lock, so several workers or containers
    starting at the same moment cannot apply them twice.
    """
    db.init_pool(cfg)

    if os.environ.get("RUN_MIGRATIONS", "1") == "1":
        if not db.wait_for_database(cfg.DB_BOOT_RETRY):
            raise RuntimeError(
                f"database unreachable after {cfg.DB_BOOT_RETRY}s and RUN_MIGRATIONS "
                "is on, so the schema cannot be verified. Set RUN_MIGRATIONS=0 and "
                "migrate in a pre-deploy step, or raise DB_BOOT_RETRY.")
        applied = db.migrate()
        if applied:
            log.info("applied %d migration(s)", applied)

    refresh_catalog()
    log.info("catalog loaded: %d lesson(s) across %d track(s), "
             "%d standard(s) in %d framework(s)",
             len(load_lessons()), len(load_tracks()),
             len(_catalog["standard_by_code"]), len(_catalog["frameworks"]))


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

    print(f"  Lessons discovered: {len(load_lessons())} "
          f"across {len(load_tracks())} track(s)")
    for item in load_lessons():
        print(f"    {item['id']:16} {item['type']:12} {len(item.get('quiz', []))} question(s)")

    if not art_exists("backgrounds/classroom"):
        print("  Classroom art not found — placeholder will be shown:")
        print("    static/art/backgrounds/classroom.png")

    print(f"\n  Serving at  http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
