#!/usr/bin/env python3
"""
app.py — Ignite Academy game server.

Two account roles:

    student  → classroom → lessons → quiz → trinkets
    parent   → plain-language progress, no digging required
    teacher  → same view as parent, plus group management

Usage:
    pip install -r ../requirements.txt
    python app.py
    python app.py --host 0.0.0.0 --port 5000

Default accounts are seeded into data/users.json on first run.
See README.md for credentials.

──────────────────────────────────────────────────────
LESSONS ARE SELF-CONTAINED PACKAGES
──────────────────────────────────────────────────────
Every lesson is one folder under lessons/.  Drop a folder in, it appears
in the game — nothing to register.

    lessons/circuits-03/
    ├── lesson.json      manifest: title, xp, quiz, reward
    ├── index.html       the lesson itself (interactive types)
    └── anything else    its own js/css/assets, namespaced to this folder

Interactive lessons render in an IFRAME.  That is deliberate and is the
whole isolation strategy: each lesson gets its own JavaScript context,
its own global scope and its own CSS scope, enforced by the browser.  A
lesson can define `window.player`, throw on load, or capture every key
event, and no other lesson can observe it.  There is no shared bundle to
break and no load order to get wrong.

Lessons talk to the host only through postMessage, via the kit — see
static/kit/lesson-kit.js.

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

import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from flask import (
        Flask, abort, flash, jsonify, redirect, render_template,
        request, send_from_directory, session, url_for,
    )
    from werkzeug.security import check_password_hash, generate_password_hash
except ImportError:
    sys.exit("Missing dependency: run  pip install -r ../requirements.txt")


BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
ART_DIR     = BASE_DIR / "static" / "art"
LESSONS_DIR = BASE_DIR / "lessons"    # one folder per lesson
CONTENT_DIR = BASE_DIR / "content"    # Markdown prose — also make_epub.py input

USERS_FILE     = DATA_DIR / "users.json"
GROUPS_FILE    = DATA_DIR / "groups.json"
PROGRESS_FILE  = DATA_DIR / "progress.json"
ITEMS_FILE     = DATA_DIR / "items.json"
CLASSROOM_FILE = DATA_DIR / "classroom.json"
SECRET_FILE    = DATA_DIR / "secret_key"

ART_EXTS = (".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg")

# Flash-style fixed stage.  Everything scales to fit the viewport.
STAGE_W = 960
STAGE_H = 600

# A student is "quiet" after this many days with no activity
QUIET_DAYS = 5
# A question missed this many times counts as a sticking point
STUCK_TRIES = 2

SEED_USERS = {
    "student":  {"password": "spark123",  "role": "student", "name": "Alex Rivera",  "avatar": "characters/avatar-student"},
    "student2": {"password": "spark123",  "role": "student", "name": "Jamie Chen",   "avatar": "characters/avatar-student2"},
    "teacher":  {"password": "ignite123", "role": "teacher", "name": "Ms. Chen",     "avatar": "characters/avatar-teacher"},
    "parent":   {"password": "ignite123", "role": "parent",  "name": "Dana Rivera",  "avatar": "characters/avatar-parent",
                 "children": ["student"]},
}

app = Flask(__name__)


# ── JSON store ──────────────────────────────────────────────────────────────────

def read_json(path: Path, default):
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
def load_items()    -> dict: return read_json(ITEMS_FILE,    {})


def load_classroom() -> dict:
    return read_json(CLASSROOM_FILE, {"background": "backgrounds/classroom", "hotspots": []})


# ── Lesson discovery ────────────────────────────────────────────────────────────

def load_lessons() -> list[dict]:
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
        data = read_json(manifest, None)
        if not isinstance(data, dict):
            print(f"Warning: skipping {folder.name} — unreadable lesson.json", file=sys.stderr)
            continue
        data["id"] = folder.name
        data.setdefault("title",   folder.name)
        data.setdefault("subject", "General")
        data.setdefault("type",    "interactive")
        data.setdefault("xp",      50)
        data.setdefault("order",   999)
        data.setdefault("quiz",    [])
        data.setdefault("thumb",   f"lessons/{folder.name}")
        found.append(data)

    return sorted(found, key=lambda l: (l["order"], l["id"]))


def get_lesson(lesson_id: str) -> dict | None:
    return next((l for l in load_lessons() if l["id"] == lesson_id), None)


@app.route("/kit/<path:filename>")
def kit_asset(filename: str):
    """
    Short, stable URL for the shared lesson kit, so every lesson writes
    the same two lines regardless of where it lives:

        <link rel="stylesheet" href="/kit/lesson-kit.css">
        <script src="/kit/lesson-kit.js"></script>
    """
    return send_from_directory(BASE_DIR / "static" / "kit", filename)


@app.route("/lessons/<lesson_id>/<path:filename>")
def lesson_asset(lesson_id: str, filename: str):
    """
    Serve a lesson package's own files.  Each lesson is sandboxed to its
    own folder, so one lesson cannot reach into another's assets.
    """
    folder = LESSONS_DIR / lesson_id
    if not (folder / "lesson.json").is_file():
        abort(404)
    return send_from_directory(folder, filename)


# ── First-run setup ─────────────────────────────────────────────────────────────

def seed_users() -> None:
    if USERS_FILE.exists():
        return
    users = {}
    for username, info in SEED_USERS.items():
        entry = {
            "password_hash": generate_password_hash(info["password"]),
            "role":          info["role"],
            "name":          info["name"],
            "avatar":        info["avatar"],
        }
        if "children" in info:
            entry["children"] = info["children"]
        users[username] = entry
    write_json(USERS_FILE, users)
    print(f"  Seeded {len(users)} account(s) → {USERS_FILE.relative_to(BASE_DIR)}")
    for username, info in SEED_USERS.items():
        print(f"    {info['role']:8} {username} / {info['password']}")


def load_secret_key() -> str:
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRET_FILE.write_text(key, encoding="utf-8")
    return key


# ── Art resolution (one shared namespace for every lesson) ──────────────────────

def find_art(name: str) -> str | None:
    for ext in ART_EXTS:
        if (ART_DIR / f"{name}{ext}").is_file():
            return f"art/{name}{ext}"
    return None


def art(name: str) -> str:
    found = find_art(name)
    if found:
        return url_for("static", filename=found)
    return url_for("art_placeholder", name=name)


def art_exists(name: str) -> bool:
    return find_art(name) is not None


def media(source: str) -> str:
    if source.startswith(("http://", "https://", "//", "/")):
        return source
    return art(source)


app.jinja_env.globals.update(
    art=art, art_exists=art_exists, media=media,
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
        return redirect(url_for("static", filename=found))
    return redirect(url_for("art_placeholder", name=name))


@app.route("/art-placeholder/<path:name>")
def art_placeholder(name: str):
    """SVG placeholder naming the exact file path to create."""
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


# ── Auth ────────────────────────────────────────────────────────────────────────

def current_user() -> dict | None:
    username = session.get("username")
    if not username:
        return None
    user = load_users().get(username)
    if not user:
        session.clear()
        return None
    return {**user, "username": username}


def login_required(*roles: str):
    """Require a session, and optionally membership of one of `roles`."""
    def decorator(fn):
        def wrapper(*fargs, **fkwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login", next=request.path))
            if roles and user["role"] not in roles:
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
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if user["role"] in ("teacher", "parent"):
        return redirect(url_for("grownup_home"))
    return redirect(url_for("classroom"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user     = load_users().get(username)

        if not user or not check_password_hash(user["password_hash"], password):
            flash("That username and password don't match.", "error")
            return render_template("login.html",
                                   role_tab=request.form.get("role_tab", "student"),
                                   username=username)

        session["username"] = username
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


# ── Progress ────────────────────────────────────────────────────────────────────

def blank_record() -> dict:
    return {"xp": 0, "items": [], "lessons": {}}


def student_progress(username: str) -> dict:
    return {**blank_record(), **load_progress().get(username, {})}


def _save_record(username: str, record: dict) -> None:
    progress = load_progress()
    progress[username] = record
    write_json(PROGRESS_FILE, progress)


def set_lesson_status(username: str, lesson_id: str, status: str,
                      score: int | None = None) -> dict:
    """Record lesson status.  XP and the reward item are granted once."""
    record = student_progress(username)
    entry  = record["lessons"].get(lesson_id, {})

    was_complete = entry.get("status") == "completed"
    entry["status"]  = status
    entry["updated"] = datetime.now().isoformat(timespec="seconds")
    if score is not None:
        entry["score"] = max(int(score), int(entry.get("score", 0)))

    if status == "completed" and not was_complete:
        lesson = get_lesson(lesson_id)
        if lesson:
            record["xp"] = record.get("xp", 0) + lesson.get("xp", 0)
            reward = lesson.get("reward")
            if reward and reward not in record["items"]:
                record["items"].append(reward)

    record["lessons"][lesson_id] = entry
    _save_record(username, record)
    return record


def record_answer(username: str, lesson_id: str, question_id: str,
                  chosen: int, correct: bool) -> dict:
    """
    Store one quiz answer.  Every attempt is kept, because "what did they
    get wrong, and how many tries did it take" is the question a parent
    actually wants answered.
    """
    record = student_progress(username)
    entry  = record["lessons"].setdefault(lesson_id, {"status": "in_progress"})
    quiz   = entry.setdefault("quiz", {})
    q      = quiz.setdefault(question_id, {"tries": 0, "correct": False})

    q["tries"]   = q.get("tries", 0) + 1
    q["chosen"]  = chosen
    q["correct"] = bool(correct)
    if correct and "first_try" not in q:
        q["first_try"] = q["tries"] == 1

    entry["updated"] = datetime.now().isoformat(timespec="seconds")
    _save_record(username, record)
    return record


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


def summarise(username: str) -> dict:
    lessons = load_lessons()
    record  = student_progress(username)
    entries = record.get("lessons", {})
    done    = sum(1 for e in entries.values() if e.get("status") == "completed")
    active  = sum(1 for e in entries.values() if e.get("status") == "in_progress")
    stamps  = [e["updated"] for e in entries.values() if e.get("updated")]

    scores = [s for s in (quiz_score(l, entries.get(l["id"], {})) for l in lessons)
              if s is not None]

    return {
        "xp": record.get("xp", 0),
        # Named "trinkets", not "items": in Jinja, `summary.items` resolves
        # to the dict's .items() method rather than this key.
        "trinkets":    record.get("items", []),
        "completed":   done,
        "in_progress": active,
        "total":       len(lessons),
        "percent":     round(done / len(lessons) * 100) if lessons else 0,
        "last_active": max(stamps) if stamps else None,
        "avg_score":   round(sum(scores) / len(scores)) if scores else None,
    }


# ── Plain-language reporting (the grown-up view) ────────────────────────────────

def days_since(stamp: str | None) -> int | None:
    if not stamp:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(stamp)).days
    except ValueError:
        return None


def sticking_points(username: str) -> list[dict]:
    """
    Questions this student got wrong, newest first, with the topic and the
    right answer spelled out.  This is what a parent reads instead of
    interpreting a score.
    """
    entries = student_progress(username).get("lessons", {})
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
            chosen  = a.get("chosen")
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


def headline(username: str) -> dict:
    """
    One sentence a parent can read in two seconds, plus a tone for colour.
    Ordered by what most needs saying.
    """
    summary = summarise(username)
    quiet   = days_since(summary["last_active"])
    stuck   = [s for s in sticking_points(username) if not s["resolved"]]

    if summary["completed"] == 0 and summary["in_progress"] == 0:
        return {"tone": "idle", "icon": "🌱",
                "text": "Hasn't started yet — the first lesson is ready when they are."}

    if quiet is not None and quiet >= QUIET_DAYS:
        return {"tone": "warn", "icon": "💤",
                "text": f"No practice in {quiet} days — a nudge would help."}

    if stuck:
        topic = stuck[0]["subject"] or stuck[0]["lesson"]
        return {"tone": "warn", "icon": "🤔",
                "text": f"Stuck on {topic} — {len(stuck)} question{'' if len(stuck) == 1 else 's'} still wrong."}

    if summary["completed"] == summary["total"] and summary["total"]:
        return {"tone": "good", "icon": "🎉",
                "text": "Finished every lesson. Time for new material!"}

    if summary["avg_score"] is not None and summary["avg_score"] >= 80:
        return {"tone": "good", "icon": "⭐",
                "text": f"Doing great — {summary['completed']} lessons done, {summary['avg_score']}% on quizzes."}

    return {"tone": "ok", "icon": "👍",
            "text": f"On track — {summary['completed']} of {summary['total']} lessons done."}


def recent_activity(username: str, limit: int = 8) -> list[dict]:
    """Newest-first timeline of what actually happened."""
    entries = student_progress(username).get("lessons", {})
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


def visible_students(user: dict) -> list[str]:
    """Teachers see every student; parents see only their own children."""
    students = [u for u, d in load_users().items() if d["role"] == "student"]
    if user["role"] == "parent":
        children = user.get("children", [])
        return [u for u in students if u in children]
    return students


# ── Student screens ─────────────────────────────────────────────────────────────

@app.route("/classroom")
@login_required("student")
def classroom():
    user = current_user()
    return render_template("classroom.html",
                           layout=load_classroom(),
                           summary=summarise(user["username"]))


@app.route("/lessons")
@login_required("student")
def lessons():
    user    = current_user()
    entries = student_progress(user["username"]).get("lessons", {})
    catalog = [{**l, "progress": entries.get(l["id"], {"status": "not_started"})}
               for l in load_lessons()]
    return render_template("lessons.html", lessons=catalog,
                           summary=summarise(user["username"]))


@app.route("/lesson/<lesson_id>")
@login_required("student")
def lesson(lesson_id: str):
    user   = current_user()
    lesson = get_lesson(lesson_id)
    if not lesson:
        abort(404)

    entry = student_progress(user["username"])["lessons"].get(lesson_id, {})
    if entry.get("status") != "completed":
        set_lesson_status(user["username"], lesson_id, "in_progress")

    body = render_content(lesson["content"]) if lesson["type"] == "reading" else None

    # Never ship the answer key to the client — questions are stripped and
    # answers checked server-side in /api/quiz.
    quiz = [{"id": q["id"], "prompt": q["prompt"], "choices": q.get("choices", [])}
            for q in lesson.get("quiz", [])]

    return render_template("lesson.html", lesson=lesson, entry=entry,
                           body=body, quiz=quiz,
                           summary=summarise(user["username"]))


@app.route("/satchel")
@login_required("student")
def satchel():
    user    = current_user()
    record  = student_progress(user["username"])
    catalog = load_items()
    earned  = set(record.get("items", []))

    items = [{**info, "id": iid, "earned": iid in earned}
             for iid, info in catalog.items()]
    items.sort(key=lambda i: (not i["earned"], i.get("name", "")))

    return render_template("satchel.html", items=items,
                           earned_count=len(earned & set(catalog)),
                           summary=summarise(user["username"]))


# ── Student APIs ────────────────────────────────────────────────────────────────

@app.route("/api/progress", methods=["POST"])
@login_required("student")
def api_progress():
    """Called by the lesson player, and by lessons via the kit's postMessage."""
    user = current_user()
    body = request.get_json(silent=True) or {}

    lesson_id = body.get("lesson_id")
    status    = body.get("status", "in_progress")
    score     = body.get("score")

    if not lesson_id or not get_lesson(lesson_id):
        return jsonify({"error": "Unknown lesson."}), 400
    if status not in ("in_progress", "completed"):
        return jsonify({"error": "Invalid status."}), 400

    set_lesson_status(user["username"], lesson_id, status, score)
    return jsonify({"ok": True, "summary": summarise(user["username"])})


@app.route("/api/quiz", methods=["POST"])
@login_required("student")
def api_quiz():
    """
    Check one answer and record the attempt.  The answer key never leaves
    the server, so it cannot be read out of the page source.
    """
    user = current_user()
    body = request.get_json(silent=True) or {}

    lesson = get_lesson(body.get("lesson_id", ""))
    if not lesson:
        return jsonify({"error": "Unknown lesson."}), 400

    question = next((q for q in lesson.get("quiz", []) if q["id"] == body.get("question_id")), None)
    if not question:
        return jsonify({"error": "Unknown question."}), 400

    try:
        chosen = int(body.get("chosen"))
    except (TypeError, ValueError):
        return jsonify({"error": "No answer given."}), 400

    correct = chosen == question["answer"]
    record_answer(user["username"], lesson["id"], question["id"], chosen, correct)

    return jsonify({
        "correct": correct,
        "answer":  question["answer"],
        "explain": question.get("explain", ""),
    })


@app.route("/api/quiz/finish", methods=["POST"])
@login_required("student")
def api_quiz_finish():
    """Score the quiz, complete the lesson, and hand back any reward earned."""
    user = current_user()
    body = request.get_json(silent=True) or {}

    lesson = get_lesson(body.get("lesson_id", ""))
    if not lesson:
        return jsonify({"error": "Unknown lesson."}), 400

    before = set(student_progress(user["username"]).get("items", []))
    entry  = student_progress(user["username"])["lessons"].get(lesson["id"], {})
    score  = quiz_score(lesson, entry)

    set_lesson_status(user["username"], lesson["id"], "completed", score)

    after   = set(student_progress(user["username"]).get("items", []))
    new_ids = after - before
    catalog = load_items()
    rewards = [{**catalog[i], "id": i} for i in new_ids if i in catalog]

    return jsonify({
        "ok":      True,
        "score":   score,
        "xp":      lesson.get("xp", 0),
        "rewards": rewards,
        "summary": summarise(user["username"]),
    })


# ── Grown-up screens (parent + teacher) ─────────────────────────────────────────

@app.route("/grownup")
@login_required("teacher", "parent")
def grownup_home():
    """
    Answers "is my kid doing the work?" without any digging: a headline
    per student, and anything needing attention pulled to the top.
    """
    user     = current_user()
    users    = load_users()
    students = visible_students(user)

    cards = []
    for username in students:
        summary = summarise(username)
        stuck   = [s for s in sticking_points(username) if not s["resolved"]]
        cards.append({
            "username": username,
            "name":     users[username]["name"],
            "avatar":   users[username].get("avatar", ""),
            "headline": headline(username),
            "stuck":    len(stuck),
            "quiet":    days_since(summary["last_active"]),
            **summary,
        })

    order = {"warn": 0, "idle": 1, "ok": 2, "good": 3}
    cards.sort(key=lambda c: (order.get(c["headline"]["tone"], 9), c["name"].lower()))
    needs_attention = [c for c in cards if c["headline"]["tone"] in ("warn", "idle")]

    return render_template("grownup.html",
                           cards=cards,
                           needs_attention=needs_attention,
                           is_teacher=user["role"] == "teacher",
                           lesson_count=len(load_lessons()))


@app.route("/grownup/student/<username>")
@login_required("teacher", "parent")
def student_detail(username: str):
    user    = current_user()
    users   = load_users()
    student = users.get(username)

    if not student or student["role"] != "student":
        abort(404)
    if username not in visible_students(user):
        abort(403)

    entries = student_progress(username).get("lessons", {})
    rows    = []
    for lesson in load_lessons():
        entry = entries.get(lesson["id"], {"status": "not_started"})
        rows.append({**lesson, "progress": entry, "score": quiz_score(lesson, entry)})

    return render_template("student.html",
                           student={**student, "username": username},
                           rows=rows,
                           summary=summarise(username),
                           headline=headline(username),
                           sticking=sticking_points(username),
                           activity=recent_activity(username),
                           quiet=days_since(summarise(username)["last_active"]),
                           is_teacher=user["role"] == "teacher")


# ── Groups (teacher only) ───────────────────────────────────────────────────────

@app.route("/groups")
@login_required("teacher")
def groups_home():
    groups   = load_groups()
    students = {u: d for u, d in load_users().items() if d["role"] == "student"}

    cards = []
    for gid, group in groups.items():
        members = [m for m in group.get("members", []) if m in students]
        stats   = [summarise(m) for m in members]
        stuck   = sum(len([s for s in sticking_points(m) if not s["resolved"]]) for m in members)
        cards.append({
            "id": gid, "name": group["name"], "members": len(members),
            "avg": round(sum(s["percent"] for s in stats) / len(stats)) if stats else 0,
            "xp":  sum(s["xp"] for s in stats),
            "stuck": stuck,
        })

    return render_template("groups.html",
                           groups=sorted(cards, key=lambda c: c["name"].lower()),
                           student_count=len(students),
                           lesson_count=len(load_lessons()))


@app.route("/groups/new", methods=["POST"])
@login_required("teacher")
def group_create():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Give the group a name.", "error")
        return redirect(url_for("groups_home"))

    groups = load_groups()
    gid    = f"g{max((int(k[1:]) for k in groups if k[1:].isdigit()), default=0) + 1}"
    groups[gid] = {"name": name, "members": [],
                   "created": datetime.now().isoformat(timespec="seconds")}
    write_json(GROUPS_FILE, groups)
    flash(f"Created “{name}”.", "success")
    return redirect(url_for("group_detail", gid=gid))


@app.route("/groups/<gid>")
@login_required("teacher")
def group_detail(gid: str):
    groups = load_groups()
    group  = groups.get(gid)
    if not group:
        abort(404)

    users    = load_users()
    students = {u: d for u, d in users.items() if d["role"] == "student"}
    members  = []
    for username in group.get("members", []):
        if username not in students:
            continue
        members.append({
            "username": username,
            "name":     students[username]["name"],
            "headline": headline(username),
            "stuck":    len([s for s in sticking_points(username) if not s["resolved"]]),
            **summarise(username),
        })

    available = [{"username": u, "name": d["name"]}
                 for u, d in sorted(students.items())
                 if u not in group.get("members", [])]

    return render_template("group.html", gid=gid, group=group,
                           members=sorted(members, key=lambda m: m["name"].lower()),
                           available=available)


@app.route("/groups/<gid>/add", methods=["POST"])
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


@app.route("/groups/<gid>/remove", methods=["POST"])
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


@app.route("/groups/<gid>/delete", methods=["POST"])
@login_required("teacher")
def group_delete(gid: str):
    groups = load_groups()
    group  = groups.pop(gid, None)
    if group:
        write_json(GROUPS_FILE, groups)
        flash(f"Deleted “{group['name']}”.", "success")
    return redirect(url_for("groups_home"))


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

    found = load_lessons()
    print(f"  Lessons discovered: {len(found)}")
    for lesson in found:
        quiz_n = len(lesson.get("quiz", []))
        print(f"    {lesson['id']:16} {lesson['type']:12} {quiz_n} question(s)")

    if not art_exists("backgrounds/classroom"):
        print("  Classroom art not found — placeholder will be shown:")
        print("    static/art/backgrounds/classroom.png")

    print(f"\n  Serving at  http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
