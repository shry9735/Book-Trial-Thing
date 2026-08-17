#!/usr/bin/env python3
"""
app.py — Ignite Academy game server.

A Flash-era style browser game for STEM lessons.  Two account roles:

    student  → lands in the classroom, clicks hotspots to reach lessons
    teacher  → group management + student progress tracking

Usage:
    pip install -r ../requirements.txt
    python app.py
    python app.py --host 0.0.0.0 --port 5000

Default accounts are seeded into data/users.json on first run.
See README.md for the credentials.

──────────────────────────────────────────────────────
GRAPHICS
──────────────────────────────────────────────────────
All art is resolved from static/art/ by name — there is no UI for it and
no per-user setting.  To change a graphic, drop a file into the folder:

    static/art/backgrounds/classroom.png

Templates request it as {{ art('backgrounds/classroom') }}.  Any of
.webp .png .jpg .jpeg .gif .svg works; the first match wins.  If nothing
is there yet, a labelled placeholder is drawn telling you the exact path
to create.  See static/art/README.md.

──────────────────────────────────────────────────────
BOOK ↔ WEB CROSSOVER
──────────────────────────────────────────────────────
Lessons of type "reading" pull their prose from content/ as Markdown.
Those same files are valid input to the repo's make_epub.py, so one
source file serves both surfaces:

    game/content/01-circuits.md
        → rendered in-game at /lesson/<id>
        → built into a chapter with:
          python ../make_epub.py content/ -t "Ignite Academy" -o book.epub

Going the other way, EPUBs in books/ are indexed by ../ingest.py for the
RAG chat.  Keep prose in content/ and it stays usable by all three.
"""

import argparse
import json
import secrets
import sys
from datetime import datetime
from pathlib import Path

try:
    from flask import (
        Flask, abort, flash, jsonify, redirect, render_template,
        request, session, url_for,
    )
    from werkzeug.security import check_password_hash, generate_password_hash
except ImportError:
    sys.exit("Missing dependency: run  pip install -r ../requirements.txt")


BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
ART_DIR     = BASE_DIR / "static" / "art"
CONTENT_DIR = BASE_DIR / "content"   # Markdown prose — also make_epub.py input

USERS_FILE     = DATA_DIR / "users.json"
GROUPS_FILE    = DATA_DIR / "groups.json"
PROGRESS_FILE  = DATA_DIR / "progress.json"
LESSONS_FILE   = DATA_DIR / "lessons.json"
CLASSROOM_FILE = DATA_DIR / "classroom.json"
SECRET_FILE    = DATA_DIR / "secret_key"

# Art file extensions, in resolution priority order
ART_EXTS = (".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg")

# Flash-style fixed stage size.  Everything scales to fit the viewport.
STAGE_W = 960
STAGE_H = 600

# Seed accounts created on first run
SEED_USERS = {
    "student": {
        "password": "spark123",
        "role":     "student",
        "name":     "Alex Rivera",
        "avatar":   "characters/avatar-student",
    },
    "student2": {
        "password": "spark123",
        "role":     "student",
        "name":     "Jamie Chen",
        "avatar":   "characters/avatar-student2",
    },
    "teacher": {
        "password": "ignite123",
        "role":     "teacher",
        "name":     "Ms. Chen",
        "avatar":   "characters/avatar-teacher",
    },
}

app = Flask(__name__)


# ── JSON store ──────────────────────────────────────────────────────────────────

def read_json(path: Path, default):
    """Read a JSON file, returning `default` if missing or unparseable."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            print(f"Warning: could not parse {path.name}, using default.", file=sys.stderr)
    return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_users()    -> dict: return read_json(USERS_FILE,    {})
def load_groups()   -> dict: return read_json(GROUPS_FILE,   {})
def load_progress() -> dict: return read_json(PROGRESS_FILE, {})
def load_lessons()  -> list: return read_json(LESSONS_FILE,  [])


def load_classroom() -> dict:
    return read_json(CLASSROOM_FILE, {"background": "backgrounds/classroom", "hotspots": []})


# ── First-run setup ─────────────────────────────────────────────────────────────

def seed_users() -> None:
    """Create data/users.json with hashed passwords if it doesn't exist."""
    if USERS_FILE.exists():
        return
    users = {
        username: {
            "password_hash": generate_password_hash(info["password"]),
            "role":          info["role"],
            "name":          info["name"],
            "avatar":        info["avatar"],
        }
        for username, info in SEED_USERS.items()
    }
    write_json(USERS_FILE, users)
    print(f"  Seeded {len(users)} account(s) → {USERS_FILE.relative_to(BASE_DIR)}")
    for username, info in SEED_USERS.items():
        print(f"    {info['role']:8} {username} / {info['password']}")


def load_secret_key() -> str:
    """Persist a random secret key so sessions survive restarts."""
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRET_FILE.write_text(key, encoding="utf-8")
    return key


# ── Art resolution ──────────────────────────────────────────────────────────────

def find_art(name: str) -> str | None:
    """Return the static-relative path for an art name, or None if absent."""
    for ext in ART_EXTS:
        if (ART_DIR / f"{name}{ext}").is_file():
            return f"art/{name}{ext}"
    return None


def art(name: str) -> str:
    """
    Resolve an art name to a URL.  Falls back to a labelled placeholder
    that names the exact file path you need to create.
    """
    found = find_art(name)
    if found:
        return url_for("static", filename=found)
    return url_for("art_placeholder", name=name)


def art_exists(name: str) -> bool:
    return find_art(name) is not None


def media(source: str) -> str:
    """
    Resolve a lesson media source.  Absolute URLs pass through untouched;
    everything else resolves through the art folder.
    """
    if source.startswith(("http://", "https://", "//", "/")):
        return source
    return art(source)


# ── Reading content (shared with make_epub.py) ──────────────────────────────────

def render_content(source: str) -> str:
    """
    Render a file from content/ to HTML for the in-game reader.

    The same file is valid make_epub.py input, so prose written once can be
    served on the web and built into an EPUB chapter without conversion.
    Markdown is rendered; .html is passed through as-is.
    """
    path = CONTENT_DIR / source
    try:
        path.resolve().relative_to(CONTENT_DIR.resolve())   # block path escapes
    except ValueError:
        return "<p>Invalid content path.</p>"

    if not path.is_file():
        return (
            f'<p class="content-missing">No content file yet — create '
            f'<code>game/content/{source}</code>.</p>'
        )

    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in (".html", ".htm"):
        return raw

    try:
        import markdown
    except ImportError:
        return f"<pre>{raw}</pre>"
    return markdown.markdown(raw, extensions=["extra", "tables"])


app.jinja_env.globals.update(
    art=art, art_exists=art_exists, media=media,
    STAGE_W=STAGE_W, STAGE_H=STAGE_H,
)


@app.route("/art-placeholder/<path:name>")
def art_placeholder(name: str):
    """
    Draw an SVG placeholder naming the missing file, so it is obvious
    which path to drop a graphic into.
    """
    label = f"static/art/{name}.png"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500">
  <defs>
    <pattern id="p" width="40" height="40" patternUnits="userSpaceOnUse">
      <rect width="40" height="40" fill="#f2e8dc"/>
      <path d="M0 40 L40 0" stroke="#e4d3c0" stroke-width="2"/>
    </pattern>
  </defs>
  <rect width="800" height="500" fill="url(#p)"/>
  <rect x="10" y="10" width="780" height="480" fill="none"
        stroke="#d4521a" stroke-width="4" stroke-dasharray="14 10" rx="8"/>
  <text x="400" y="228" text-anchor="middle"
        font-family="Trebuchet MS, Verdana, sans-serif" font-size="30"
        font-weight="bold" fill="#d4521a">Drop a graphic here</text>
  <text x="400" y="278" text-anchor="middle"
        font-family="Consolas, Menlo, monospace" font-size="21" fill="#4a4a5e">{label}</text>
  <text x="400" y="316" text-anchor="middle"
        font-family="Trebuchet MS, Verdana, sans-serif" font-size="15" fill="#8888a0">
    .webp .png .jpg .gif or .svg — any of these work
  </text>
</svg>"""
    return app.response_class(svg, mimetype="image/svg+xml")


# ── Auth ────────────────────────────────────────────────────────────────────────

def current_user() -> dict | None:
    """Return the logged-in user dict (with 'username' added), or None."""
    username = session.get("username")
    if not username:
        return None
    user = load_users().get(username)
    if not user:
        session.clear()
        return None
    return {**user, "username": username}


def login_required(role: str | None = None):
    """
    Decorator enforcing a session, and optionally a specific role.
    Wrong-role users are bounced to their own home screen rather than
    shown an error.
    """
    def decorator(fn):
        def wrapper(*fargs, **fkwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login", next=request.path))
            if role and user["role"] != role:
                return redirect(url_for("home"))
            return fn(*fargs, **fkwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


@app.context_processor
def inject_user():
    return {"user": current_user()}


@app.route("/")
def home():
    """Route to the right home screen for whoever is logged in."""
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if user["role"] == "teacher":
        return redirect(url_for("teacher_dashboard"))
    return redirect(url_for("classroom"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        users    = load_users()
        user     = users.get(username)

        if not user or not check_password_hash(user["password_hash"], password):
            flash("That username and password don't match.", "error")
            return render_template(
                "login.html",
                role_tab=request.form.get("role_tab", "student"),
                username=username,
            )

        session["username"] = username
        # The account's own role decides the destination — picking the
        # wrong tab on the login screen is harmless.
        nxt = request.args.get("next")
        if nxt and nxt.startswith("/"):
            return redirect(nxt)
        return redirect(url_for("home"))

    if current_user():
        return redirect(url_for("home"))
    return render_template("login.html", role_tab=request.args.get("role", "student"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Progress helpers ────────────────────────────────────────────────────────────

def student_progress(username: str) -> dict:
    """Return {xp, lessons:{id:{status,score,updated}}} for one student."""
    return load_progress().get(username, {"xp": 0, "lessons": {}})


def set_lesson_status(username: str, lesson_id: str, status: str, score: int | None = None) -> dict:
    """
    Record progress for a lesson.  XP is awarded once, on first completion.
    Returns the updated record for that student.
    """
    progress = load_progress()
    record   = progress.setdefault(username, {"xp": 0, "lessons": {}})
    entry    = record["lessons"].get(lesson_id, {})

    was_complete = entry.get("status") == "completed"
    entry["status"]  = status
    entry["updated"] = datetime.now().isoformat(timespec="seconds")
    if score is not None:
        entry["score"] = max(int(score), int(entry.get("score", 0)))

    if status == "completed" and not was_complete:
        lesson = next((l for l in load_lessons() if l["id"] == lesson_id), None)
        record["xp"] = record.get("xp", 0) + (lesson.get("xp", 0) if lesson else 0)

    record["lessons"][lesson_id] = entry
    write_json(PROGRESS_FILE, progress)
    return record


def summarise(username: str) -> dict:
    """Roll a student's progress up into dashboard-friendly totals."""
    lessons  = load_lessons()
    record   = student_progress(username)
    entries  = record.get("lessons", {})
    done     = sum(1 for e in entries.values() if e.get("status") == "completed")
    active   = sum(1 for e in entries.values() if e.get("status") == "in_progress")
    stamps   = [e["updated"] for e in entries.values() if e.get("updated")]
    return {
        "xp":          record.get("xp", 0),
        "completed":   done,
        "in_progress": active,
        "total":       len(lessons),
        "percent":     round(done / len(lessons) * 100) if lessons else 0,
        "last_active": max(stamps) if stamps else None,
    }


# ── Student screens ─────────────────────────────────────────────────────────────

@app.route("/classroom")
@login_required("student")
def classroom():
    user    = current_user()
    layout  = load_classroom()
    summary = summarise(user["username"])
    return render_template("classroom.html", layout=layout, summary=summary)


@app.route("/lessons")
@login_required("student")
def lessons():
    user     = current_user()
    record   = student_progress(user["username"])
    entries  = record.get("lessons", {})
    catalog  = [
        {**lesson, "progress": entries.get(lesson["id"], {"status": "not_started"})}
        for lesson in load_lessons()
    ]
    return render_template("lessons.html", lessons=catalog, summary=summarise(user["username"]))


@app.route("/lesson/<lesson_id>")
@login_required("student")
def lesson(lesson_id: str):
    user   = current_user()
    lesson = next((l for l in load_lessons() if l["id"] == lesson_id), None)
    if not lesson:
        abort(404)

    entry = student_progress(user["username"])["lessons"].get(lesson_id, {})
    if entry.get("status") != "completed":
        set_lesson_status(user["username"], lesson_id, "in_progress")

    body = render_content(lesson["source"]) if lesson["type"] == "reading" else None
    return render_template("lesson.html", lesson=lesson, entry=entry, body=body)


@app.route("/api/progress", methods=["POST"])
@login_required("student")
def api_progress():
    """
    Called by the lesson player when a video finishes or an embedded game
    reports a result.  Games post from inside their iframe with:

        window.parent.postMessage(
            {type: "lesson:complete", score: 90}, "*"
        )
    """
    user = current_user()
    body = request.get_json(silent=True) or {}

    lesson_id = body.get("lesson_id")
    status    = body.get("status", "in_progress")
    score     = body.get("score")

    if not lesson_id or not any(l["id"] == lesson_id for l in load_lessons()):
        return jsonify({"error": "Unknown lesson."}), 400
    if status not in ("in_progress", "completed"):
        return jsonify({"error": "Invalid status."}), 400

    set_lesson_status(user["username"], lesson_id, status, score)
    return jsonify({"ok": True, "summary": summarise(user["username"])})


# ── Teacher screens ─────────────────────────────────────────────────────────────

@app.route("/teacher")
@login_required("teacher")
def teacher_dashboard():
    groups   = load_groups()
    students = {u: d for u, d in load_users().items() if d["role"] == "student"}

    cards = []
    for gid, group in groups.items():
        members = [m for m in group.get("members", []) if m in students]
        stats   = [summarise(m) for m in members]
        cards.append({
            "id":      gid,
            "name":    group["name"],
            "members": len(members),
            "avg":     round(sum(s["percent"] for s in stats) / len(stats)) if stats else 0,
            "xp":      sum(s["xp"] for s in stats),
        })

    return render_template(
        "teacher.html",
        groups=sorted(cards, key=lambda c: c["name"].lower()),
        student_count=len(students),
        lesson_count=len(load_lessons()),
    )


@app.route("/teacher/group/new", methods=["POST"])
@login_required("teacher")
def group_create():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Give the group a name.", "error")
        return redirect(url_for("teacher_dashboard"))

    groups = load_groups()
    gid    = f"g{max((int(k[1:]) for k in groups if k[1:].isdigit()), default=0) + 1}"
    groups[gid] = {
        "name":    name,
        "members": [],
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    write_json(GROUPS_FILE, groups)
    flash(f"Created “{name}”.", "success")
    return redirect(url_for("group_detail", gid=gid))


@app.route("/teacher/group/<gid>")
@login_required("teacher")
def group_detail(gid: str):
    groups = load_groups()
    group  = groups.get(gid)
    if not group:
        abort(404)

    users    = load_users()
    students = {u: d for u, d in users.items() if d["role"] == "student"}
    members  = [
        {"username": u, "name": students[u]["name"], **summarise(u)}
        for u in group.get("members", []) if u in students
    ]
    available = [
        {"username": u, "name": d["name"]}
        for u, d in sorted(students.items()) if u not in group.get("members", [])
    ]

    return render_template(
        "group.html",
        gid=gid, group=group,
        members=sorted(members, key=lambda m: m["name"].lower()),
        available=available,
        lessons=load_lessons(),
    )


@app.route("/teacher/group/<gid>/add", methods=["POST"])
@login_required("teacher")
def group_add_member(gid: str):
    groups = load_groups()
    group  = groups.get(gid)
    if not group:
        abort(404)

    username = request.form.get("username", "").strip()
    users    = load_users()
    if users.get(username, {}).get("role") != "student":
        flash("That isn't a student account.", "error")
        return redirect(url_for("group_detail", gid=gid))

    if username not in group["members"]:
        group["members"].append(username)
        write_json(GROUPS_FILE, groups)
        flash(f"Added {users[username]['name']}.", "success")

    return redirect(url_for("group_detail", gid=gid))


@app.route("/teacher/group/<gid>/remove", methods=["POST"])
@login_required("teacher")
def group_remove_member(gid: str):
    groups = load_groups()
    group  = groups.get(gid)
    if not group:
        abort(404)

    username = request.form.get("username", "").strip()
    if username in group["members"]:
        group["members"].remove(username)
        write_json(GROUPS_FILE, groups)
        flash("Removed from group.", "success")

    return redirect(url_for("group_detail", gid=gid))


@app.route("/teacher/group/<gid>/delete", methods=["POST"])
@login_required("teacher")
def group_delete(gid: str):
    groups = load_groups()
    group  = groups.pop(gid, None)
    if group:
        write_json(GROUPS_FILE, groups)
        flash(f"Deleted “{group['name']}”.", "success")
    return redirect(url_for("teacher_dashboard"))


@app.route("/teacher/student/<username>")
@login_required("teacher")
def student_detail(username: str):
    users   = load_users()
    student = users.get(username)
    if not student or student["role"] != "student":
        abort(404)

    entries = student_progress(username)["lessons"]
    rows    = [
        {**lesson, "progress": entries.get(lesson["id"], {"status": "not_started"})}
        for lesson in load_lessons()
    ]
    return render_template(
        "student.html",
        student={**student, "username": username},
        rows=rows,
        summary=summarise(username),
    )


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ignite Academy game server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug reloader.")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    seed_users()
    app.secret_key = load_secret_key()

    missing = [
        name for name in ("backgrounds/classroom",)
        if not art_exists(name)
    ]
    if missing:
        print("  Art not found yet (placeholders will be shown):")
        for name in missing:
            print(f"    static/art/{name}.png")

    print(f"\n  Serving at  http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
