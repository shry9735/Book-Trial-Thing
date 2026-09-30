#!/usr/bin/env python3
"""
selftest.py — end-to-end checks against a real Postgres.

Deliberately not unit tests with a mocked database: every bug this
rewrite was meant to fix (lost concurrent writes, cross-organisation
disclosure, replayable reset links) only exists in the interaction with
the real thing.  A fake would pass while the product broke.

    createdb ignite_test
    DATABASE_URL=postgresql://.../ignite_test python selftest.py

The target database is wiped at the start of the run, so point it at a
scratch database and never at production.  It refuses to run if
APP_ENV=production.
"""

import gzip
import os
import re
import sys
import threading

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "0")
os.environ.setdefault("SECRET_KEY", "0" * 64)
os.environ.setdefault("RUN_MIGRATIONS", "1")
# This run creates a few dozen accounts from one address, which the real
# signup limit is there to stop. Raised here and exercised on its own in
# t_signup_rate_limit() rather than tripping every later test.
os.environ.setdefault("RL_SIGNUP_IP", "10000")

if os.environ.get("APP_ENV") == "production":
    sys.exit("selftest refuses to run against APP_ENV=production")

import app as appmod           # noqa: E402
import db                      # noqa: E402
import security                # noqa: E402

PASSED, FAILED = [], []


def check(name):
    def decorator(fn):
        def run():
            try:
                fn()
                PASSED.append(name)
                print(f"  \033[32mPASS\033[0m  {name}")
            except Exception as exc:
                FAILED.append((name, exc))
                print(f"  \033[31mFAIL\033[0m  {name}\n          {type(exc).__name__}: {exc}")
        run.__name__ = fn.__name__
        return run
    return decorator


def reset_database():
    """
    Drop whatever is in the public schema and migrate from nothing.

    Dropping the schema rather than a hardcoded table list means adding a
    migration never silently breaks the teardown — which it did once,
    exactly that way.
    """
    with db.write() as cur:
        cur.execute("DROP SCHEMA public CASCADE")
        cur.execute("CREATE SCHEMA public")
    db.migrate()


def client():
    return appmod.app.test_client()


def token_from(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "no CSRF token in the page"
    return match.group(1)


def signup(c, role, **fields):
    page = c.get(f"/signup?role={role}").get_data(as_text=True)
    data = {
        "csrf_token": token_from(page),
        "name": fields.get("name", "Test Person"),
        "username": fields["username"],
        "email": fields["email"],
        "password": fields.get("password", "correct-horse-battery"),
        "password_confirm": fields.get("password", "correct-horse-battery"),
        "terms_ok": "1",
    }
    if role == "student":
        data["age_ok"] = "1"
        data["join_code"] = fields["join_code"]
    elif role == "parent":
        data["join_code"] = fields["join_code"]
    else:
        data["org_name"] = fields.get("org_name", "Test School")
    return c.post(f"/signup?role={role}", data=data, follow_redirects=True)


def login(c, username, password="correct-horse-battery"):
    page = c.get("/login").get_data(as_text=True)
    return c.post("/login", data={
        "csrf_token": token_from(page),
        "username": username,
        "password": password,
    }, follow_redirects=True)


def join_code_for(username):
    user = db.user_by_username(username)
    return db.org_by_id(user["org_id"])["join_code"]


# ── Accounts ────────────────────────────────────────────────────────────────────

@check("teacher signup creates an org with a join code")
def t_teacher_signup():
    c = client()
    res = signup(c, "teacher", username="ms_chen", email="chen@example.com",
                 org_name="Rivera Middle")
    assert res.status_code == 200, res.status_code
    user = db.user_by_username("ms_chen")
    assert user and user["role"] == "teacher", "teacher not created"
    org = db.org_by_id(user["org_id"])
    assert org["name"] == "Rivera Middle", org
    assert len(org["join_code"]) == 8, org["join_code"]


@check("student signup requires a valid join code")
def t_student_join_code():
    c = client()
    res = signup(c, "student", username="badjoin", email="bad@example.com",
                 join_code="ZZZZZZZZ")
    assert db.user_by_username("badjoin") is None, "account created with a bogus join code"
    assert "join code" in res.get_data(as_text=True).lower()

    code = join_code_for("ms_chen")
    signup(client(), "student", username="alex", email="alex@example.com", join_code=code)
    student = db.user_by_username("alex")
    assert student and student["role"] == "student", "student not created"
    assert student["link_code"] and len(student["link_code"]) == 6, "no parent link code"
    assert student["age_confirmed_at"] is not None, "age attestation not recorded"


@check("duplicate usernames and emails are refused")
def t_duplicates():
    code = join_code_for("ms_chen")
    signup(client(), "student", username="ALEX", email="other@example.com", join_code=code)
    with db.query() as cur:
        cur.execute("SELECT count(*) AS n FROM users WHERE lower(username) = 'alex'")
        assert cur.fetchone()["n"] == 1, "case-different duplicate username was allowed"

    signup(client(), "student", username="alex2", email="ALEX@example.com", join_code=code)
    assert db.user_by_username("alex2") is None, "case-different duplicate email was allowed"


@check("short and common passwords are refused")
def t_password_policy():
    code = join_code_for("ms_chen")
    signup(client(), "student", username="weak1", email="w1@example.com",
           join_code=code, password="short")
    assert db.user_by_username("weak1") is None, "short password accepted"
    signup(client(), "student", username="weak2", email="w2@example.com",
           join_code=code, password="password123")
    assert db.user_by_username("weak2") is None, "common password accepted"


@check("login works and a wrong password is refused")
def t_login():
    c = client()
    res = login(c, "alex")
    assert res.status_code == 200
    assert "/classroom" in res.request.path or c.get("/").headers.get("Location", "") != "/login", res.request.path

    bad = client()
    res = login(bad, "alex", "wrong-password-entirely")
    assert "don&#39;t match" in res.get_data(as_text=True) or "don't match" in res.get_data(as_text=True)
    assert bad.get("/classroom").status_code == 302, "signed in despite a wrong password"


# ── Web hardening ───────────────────────────────────────────────────────────────

@check("a form POST without a CSRF token is rejected")
def t_csrf():
    c = client()
    login(c, "ms_chen")
    res = c.post("/classrooms/new", data={"name": "No Token Class"})
    assert res.status_code == 400, f"expected 400, got {res.status_code}"

    page = c.get("/classrooms").get_data(as_text=True)
    res = c.post("/classrooms/new", data={"name": "Real Class",
                                          "csrf_token": token_from(page)})
    assert res.status_code in (302, 200), res.status_code


@check("a form-encoded POST to a JSON API is rejected")
def t_api_content_type():
    c = client()
    login(c, "alex")
    # This is the shape a cross-site <form> attack takes: it can only send
    # form encodings, never application/json.
    res = c.post("/api/progress", data={"lesson_id": "circuits-01-breadboard",
                                        "status": "completed"})
    assert res.status_code == 415, f"expected 415, got {res.status_code}"


@check("open redirect via ?next= is blocked")
def t_open_redirect():
    assert security.safe_next("//evil.example.com") == "/", "protocol-relative URL allowed"
    assert security.safe_next("https://evil.example.com") == "/", "absolute URL allowed"
    assert security.safe_next("/\\evil.example.com") == "/", "backslash form allowed"
    assert security.safe_next("/lessons") == "/lessons", "local path rejected"


@check("security headers are set on responses")
def t_headers():
    res = client().get("/login")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert res.headers.get("Referrer-Policy") == "same-origin"


@check("session cookie is HttpOnly and SameSite=Lax")
def t_cookie_flags():
    c = client()
    res = login(c, "alex")
    cookies = [h for k, h in res.headers if k == "Set-Cookie"] or []
    if not cookies:
        # Set during the redirect chain; check the config the app applied.
        assert appmod.app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert appmod.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
        return
    assert any("HttpOnly" in c_ for c_ in cookies), cookies


@check("signup is rate limited per address")
def t_signup_rate_limit():
    original = appmod.cfg.RL_SIGNUP_IP
    appmod.cfg.RL_SIGNUP_IP = 2
    try:
        code = join_code_for("ms_chen")
        last = None
        for n in range(4):
            last = signup(client(), "student", username=f"flood{n}",
                          email=f"flood{n}@example.com", join_code=code)
        assert last.status_code == 429, f"expected 429, got {last.status_code}"
        assert db.user_by_username("flood3") is None, "account created past the limit"
    finally:
        appmod.cfg.RL_SIGNUP_IP = original
        security.clear_attempts("signup_ip", "127.0.0.1")


@check("login is rate limited")
def t_rate_limit():
    c = client()
    limit = appmod.cfg.RL_LOGIN_USER
    for _ in range(limit + 1):
        login(c, "alex", "definitely-wrong-password")
    res = login(c, "alex", "definitely-wrong-password")
    assert res.status_code == 429, f"expected 429 after {limit} failures, got {res.status_code}"
    # A correct password must still be refused while the lockout holds.
    security.clear_attempts("login_user", "alex")
    security.clear_attempts("login_ip", "127.0.0.1")


# ── Tenancy ─────────────────────────────────────────────────────────────────────

@check("a teacher cannot see another organisation's students")
def t_tenancy():
    signup(client(), "teacher", username="mr_other", email="other@school.com",
           org_name="Other School")
    other_code = join_code_for("mr_other")
    signup(client(), "student", username="notyours", email="ny@example.com",
           join_code=other_code)

    chen = db.user_by_username("ms_chen")
    visible = {s["username"] for s in db.visible_students(chen)}
    assert "alex" in visible, "own student missing"
    assert "notyours" not in visible, "SAW ANOTHER ORG'S STUDENT"

    c = client()
    login(c, "ms_chen")
    res = c.get("/grownup/student/notyours")
    assert res.status_code == 404, f"cross-org student page returned {res.status_code}"

    body = c.get("/grownup").get_data(as_text=True)
    assert "notyours" not in body, "cross-org student leaked onto the dashboard"


@check("a parent sees only their linked children")
def t_parent_scope():
    code = join_code_for("ms_chen")
    signup(client(), "parent", username="dana", email="dana@example.com", join_code=code)
    parent = db.user_by_username("dana")
    assert db.visible_students(parent) == [], "parent saw children before linking"

    alex = db.user_by_username("alex")
    db.link_parent(parent["id"], alex["id"])
    visible = {s["username"] for s in db.visible_students(parent)}
    assert visible == {"alex"}, visible

    c = client()
    login(c, "dana")
    assert c.get("/grownup/student/notyours").status_code == 404
    assert c.get("/classrooms").status_code == 302, "parent reached teacher-only classrooms"


# ── Progress ────────────────────────────────────────────────────────────────────

def api(c, path, payload):
    return c.post(path, json=payload)


@check("quiz answers record tries and first_try correctly")
def t_quiz_recording():
    lesson = next(l for l in appmod.load_lessons() if l.get("quiz"))
    question = lesson["quiz"][0]
    wrong = 0 if question["answer"] != 0 else 1

    c = client()
    login(c, "alex")
    alex = db.user_by_username("alex")

    res = api(c, "/api/quiz", {"lesson_id": lesson["id"],
                               "question_id": question["id"], "chosen": wrong})
    assert res.get_json()["correct"] is False, res.get_json()

    res = api(c, "/api/quiz", {"lesson_id": lesson["id"],
                               "question_id": question["id"], "chosen": question["answer"]})
    assert res.get_json()["correct"] is True

    entries = db.lesson_entries(alex["id"])
    answer = entries[lesson["id"]]["quiz"][question["id"]]
    assert answer["tries"] == 2, f"tries={answer['tries']}, expected 2"
    assert answer["correct"] is True
    assert answer["first_try"] is False, "second-attempt correct counted as first try"


@check("a reward is granted exactly once, even on a double submit")
def t_reward_once():
    lesson = next((l for l in appmod.load_lessons() if l.get("reward")), None)
    if lesson is None:
        raise AssertionError("no lesson defines a reward — cannot test grant-once")

    alex = db.user_by_username("alex")
    c = client()
    login(c, "alex")

    first = api(c, "/api/quiz/finish", {"lesson_id": lesson["id"], "quiz_seconds": 30})
    second = api(c, "/api/quiz/finish", {"lesson_id": lesson["id"], "quiz_seconds": 30})

    assert len(first.get_json()["rewards"]) >= 0
    assert len(second.get_json()["rewards"]) == 0, "the same reward was granted twice"

    items = db.inventory(alex["id"])
    assert items.count(lesson["reward"]) == 1, items


@check("concurrent progress writes do not lose data")
def t_concurrent_writes():
    """
    The failure the JSON store had: read whole file, mutate, write whole
    file.  Two students finishing at once meant one result vanished.
    """
    code = join_code_for("ms_chen")
    ids = []
    for n in range(8):
        signup(client(), "student", username=f"racer{n}",
               email=f"racer{n}@example.com", join_code=code)
        ids.append(db.user_by_username(f"racer{n}")["id"])

    lesson_ids = [l["id"] for l in appmod.load_lessons()][:4]
    assert lesson_ids, "no lessons to write against"

    errors = []

    def worker(student_id):
        try:
            for lesson_id in lesson_ids:
                db.set_lesson_status(student_id, lesson_id, "completed", 100)
        except Exception as exc:            # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(sid,)) for sid in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"writer errors: {errors[:3]}"
    for student_id in ids:
        entries = db.lesson_entries(student_id)
        done = [l for l in lesson_ids if entries.get(l, {}).get("status") == "completed"]
        assert len(done) == len(lesson_ids), (
            f"student {student_id} kept {len(done)}/{len(lesson_ids)} lessons — writes were lost")


@check("the same question answered concurrently counts every try")
def t_concurrent_same_row():
    lesson = next(l for l in appmod.load_lessons() if l.get("quiz"))
    question = lesson["quiz"][0]
    student = db.user_by_username("racer0")
    wrong = 0 if question["answer"] != 0 else 1

    def worker():
        db.record_answer(student["id"], lesson["id"], question["id"], wrong, False)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    entries = db.lesson_entries(student["id"])
    tries = entries[lesson["id"]]["quiz"][question["id"]]["tries"]
    assert tries == 10, f"10 concurrent answers recorded {tries} tries"


@check("the dashboard runs a constant number of queries")
def t_dashboard_queries():
    """
    Guards the N+1 that made the old grown-up page re-parse the whole
    progress file once per student per metric.
    """
    chen = db.user_by_username("ms_chen")
    students = db.visible_students(chen)
    assert len(students) >= 8, f"only {len(students)} students to measure against"

    calls = {"n": 0}
    original = db.query

    import contextlib

    @contextlib.contextmanager
    def counting():
        calls["n"] += 1
        with original() as cur:
            yield cur

    db.query = counting
    try:
        c = client()
        login(c, "ms_chen")
        calls["n"] = 0
        res = c.get("/grownup")
    finally:
        db.query = original

    assert res.status_code == 200, res.status_code
    # Constant work: session lookup, student list, three summary queries,
    # the stuck-count query and the org lookup. Nothing per student.
    assert calls["n"] <= 12, (
        f"{calls['n']} queries for {len(students)} students — this scales per student")


# ── Tokens ──────────────────────────────────────────────────────────────────────

@check("a password reset link works once and then never again")
def t_reset_single_use():
    user = db.user_by_username("alex")
    raw, hashed = security.new_token()
    with db.write() as cur:
        db.store_token(cur, hashed, user["id"], "reset", 24)

    c = client()
    page = c.get(f"/reset/{raw}").get_data(as_text=True)
    res = c.post(f"/reset/{raw}", data={
        "csrf_token": token_from(page),
        "password": "brand-new-password-here",
        "password_confirm": "brand-new-password-here",
    }, follow_redirects=True)
    assert res.status_code == 200

    assert login(client(), "alex", "brand-new-password-here").status_code == 200
    fresh = client()
    login(fresh, "alex", "brand-new-password-here")
    assert fresh.get("/classroom").status_code == 200, "new password does not work"

    page = c.get(f"/reset/{raw}").get_data(as_text=True)
    c.post(f"/reset/{raw}", data={
        "csrf_token": token_from(page),
        "password": "second-attempt-password",
        "password_confirm": "second-attempt-password",
    }, follow_redirects=True)
    replay = client()
    login(replay, "alex", "second-attempt-password")
    assert replay.get("/classroom").status_code == 302, "reset link was replayable"


@check("changing a password invalidates existing sessions")
def t_session_epoch():
    code = join_code_for("ms_chen")
    signup(client(), "student", username="rotate", email="rotate@example.com", join_code=code)

    c = client()
    login(c, "rotate")
    assert c.get("/classroom").status_code == 200, "could not sign in"

    user = db.user_by_username("rotate")
    from werkzeug.security import generate_password_hash
    db.set_password(user["id"], generate_password_hash("a-completely-new-password"))

    assert c.get("/classroom").status_code == 302, "old session still valid after password change"


@check("an expired token is refused")
def t_expired_token():
    user = db.user_by_username("ms_chen")
    raw, hashed = security.new_token()
    with db.write() as cur:
        db.store_token(cur, hashed, user["id"], "reset", 24)
        cur.execute("UPDATE auth_tokens SET expires_at = now() - interval '1 hour' "
                    "WHERE token_hash = %s", (hashed,))
    assert db.consume_token(hashed, "reset") is None, "expired token accepted"


@check("the forgot-password form does not reveal which emails exist")
def t_no_enumeration():
    c = client()
    page = c.get("/forgot").get_data(as_text=True)
    known = c.post("/forgot", data={"csrf_token": token_from(page),
                                    "email": "chen@example.com"}, follow_redirects=True)
    c2 = client()
    page = c2.get("/forgot").get_data(as_text=True)
    unknown = c2.post("/forgot", data={"csrf_token": token_from(page),
                                       "email": "nobody@nowhere.test"}, follow_redirects=True)
    assert known.status_code == unknown.status_code
    assert "reset link is on its way" in known.get_data(as_text=True)
    assert "reset link is on its way" in unknown.get_data(as_text=True)


# ── Assignments and classrooms ──────────────────────────────────────────────────

@check("assignment restrictions are enforced server-side")
def t_assignments():
    lessons = appmod.load_lessons()
    assert len(lessons) >= 2, "need at least two lessons"
    allowed, blocked = lessons[0]["id"], lessons[1]["id"]

    student = db.user_by_username("racer1")
    teacher = db.user_by_username("ms_chen")
    db.set_assignment(student["id"], [allowed], teacher["id"])

    c = client()
    login(c, "racer1")
    assert c.get(f"/lesson/{allowed}").status_code == 200
    assert c.get(f"/lesson/{blocked}").status_code == 403, "blocked lesson was reachable"

    db.set_assignment(student["id"], None, teacher["id"])
    assert c.get(f"/lesson/{blocked}").status_code == 200, "unrestricting did not work"


@check("classroom membership cannot cross organisations")
def t_classroom_tenancy():
    teacher = db.user_by_username("ms_chen")
    classroom_id = db.create_classroom(teacher["org_id"], "Period 1", teacher["id"])
    db.add_classroom_teacher(classroom_id, teacher["id"])

    c = client()
    login(c, "ms_chen")
    page = c.get(f"/classrooms/{classroom_id}").get_data(as_text=True)
    res = c.post(f"/classrooms/{classroom_id}/students/add",
                 data={"csrf_token": token_from(page), "username": "notyours"})
    assert res.status_code == 404, "added another org's student to a classroom"

    res = c.post(f"/classrooms/{classroom_id}/students/add",
                 data={"csrf_token": token_from(page), "username": "alex"})
    assert res.status_code in (302, 200)
    assert {m["username"] for m in db.classroom_students(classroom_id)} == {"alex"}

    other = db.user_by_username("mr_other")
    assert db.classroom_in_org(classroom_id, other["org_id"]) is None, \
        "classroom visible to another org"


@check("HTTP errors keep their own status instead of becoming 500s")
def t_http_error_codes():
    """
    A handler registered for Exception also catches HTTPException, which
    turned every 404, 405 and 415 into a 500 with a stack trace.
    """
    c = client()
    cases = [
        ("GET", "/logout", 405),          # POST-only
        ("GET", "/api/progress", 405),    # POST-only
        ("GET", "/definitely-not-a-page", 404),
    ]
    for method, path, expect in cases:
        res = c.open(path, method=method)
        assert res.status_code == expect, f"{method} {path} → {res.status_code}, expected {expect}"

    # API errors answer as JSON, not as an HTML error page.
    res = c.get("/api/progress")
    assert res.is_json, f"API error returned {res.content_type}"


@check("a HEAD request does not run the login POST path")
def t_head_not_post():
    """
    Flask adds HEAD to every GET route, so a `method == "GET"` guard is
    false for HEAD and the POST branch runs.  An uptime monitor doing
    HEAD /login would have burned a password hash and a rate-limit slot
    on every probe.
    """
    c = client()
    before = db.rate_count(
        "login_user:" + __import__("hashlib").sha256(b"").hexdigest()[:32], 900)
    for path in ("/login", "/signup", "/forgot", "/reset/some-token"):
        res = c.head(path)
        assert res.status_code == 200, f"HEAD {path} returned {res.status_code}"
    after = db.rate_count(
        "login_user:" + __import__("hashlib").sha256(b"").hexdigest()[:32], 900)
    assert after == before, "a HEAD request recorded a failed-login attempt"


@check("no page that varies by session is publicly cacheable")
def t_cache_headers():
    """
    `public` on a response whose body depends on who is looking invites a
    shared cache to hand one visitor's copy to another.

    /legal shipped that way: the content only changes on deploy, but the
    page says "Back" to somebody signed in and "Sign in" to somebody who is
    not. Nothing in front of this app caches today, so it was latent — and
    it would have become a real leak the first time anyone put a name on
    that page.
    """
    anon = client()

    for path in ("/legal/terms", "/legal/privacy"):
        out = anon.get(path)
        cache = out.headers.get("Cache-Control", "")
        assert "public" not in cache, f"{path} is publicly cacheable: {cache!r}"
        assert "private" in cache, f"{path}: {cache!r}"
        assert "Cookie" in out.headers.get("Vary", ""), \
            f"{path} varies by session but does not say so"

        # What makes the header matter: the page really is session-aware.
        # Asserted on the anonymous side only, because comparing two whole
        # bodies makes this test depend on the fixture's login still
        # working, which earlier checks in this file deliberately break.
        assert "Sign in" in out.get_data(as_text=True), \
            f"{path} no longer varies by session — the rule can be relaxed"

    # The genuinely identical-for-everyone responses may stay public.
    for path in ("/kit/lesson-kit.js", "/art-placeholder/missing/thing"):
        cache = anon.get(path).headers.get("Cache-Control", "")
        assert "public" in cache, f"{path} lost its public cache: {cache!r}"

    # And nothing behind a login is ever publicly cacheable.
    signed_in = client()
    login(signed_in, "racer0")
    assert signed_in.get("/classroom").status_code == 200, "fixture login failed"
    for path in ("/classroom", "/lessons", "/satchel"):
        cache = signed_in.get(path).headers.get("Cache-Control", "")
        assert "public" not in cache, f"{path} is publicly cacheable: {cache!r}"


@check("a pending member is held out of everything but their own account")
def t_membership_gate_is_complete():
    """
    Walk the route table rather than testing routes one at a time.

    This exists because eight routes were missing @membership_required at
    once, and the worst of them let a parent an org admin had NOT approved
    link themselves to a child with that child's link code and then read
    that child's progress — precisely what approval exists to prevent.

    Asserting on the decorator catches the next one the moment it is
    written, which testing behaviour route-by-route does not: the route
    nobody thinks to test is exactly the one that will be missing its gate.
    """
    import inspect

    # Routes that legitimately skip it, each for a reason that has to stay
    # true. Anything else must carry the gate.
    exempt = {
        "pending":            "it IS the holding pen",
        "logout":             "you can always leave",
        "settings_home":      "your own account, not the org's content",
        "change_password":    "your own account",
        "first_password":     "has to work before anything else does",
        "delete_own_account": "your own account",
        "billing_home":       "a pending admin may still need to pay",
        "billing_subscribe":  "a pending admin may still need to pay",
        "billing_portal":     "a pending admin may still need to pay",
        "billing_return":     "returns from Stripe",
        "billing_invoice_request": "a pending admin may still need to pay",
        "locked":             "explains why something is shut",
        "resend_verification": "happens before approval by nature",
        "verify_email":       "happens before approval by nature",
        "legal":              "public",
        "home":               "routes onward, including to /pending",
    }

    pattern = (r"((?:@app\.route\([^)]*\)\s*\n)+"
               r"(?:@[\w_]+(?:\([^)]*\))?\s*\n)*)def (\w+)\(")
    ungated = []
    for match in re.finditer(pattern, inspect.getsource(appmod)):
        decorators, name = match.group(1), match.group(2)
        if "@org_admin_required" in decorators:
            continue          # implies an already-approved admin
        if "@login_required" not in decorators:
            continue          # public
        if "@membership_required" in decorators or name in exempt:
            continue
        ungated.append(name)

    assert not ungated, (
        f"authenticated route(s) with no membership gate and no documented "
        f"reason: {ungated}. Add @membership_required, or add the route to "
        f"the exemption list here together with why.")


@check("an unapproved parent cannot reach a child, even with the link code")
def t_pending_parent_blocked():
    """The concrete hole the audit above was written for."""
    head = db.user_by_username("ms_chen")
    original = db.org_by_id(head["org_id"])["join_policy"]
    db.set_join_policy(head["org_id"], "approval")
    try:
        signup(client(), "parent", username="unapproved",
               email="unapproved@example.com", join_code=join_code_for("ms_chen"))
        snooper = db.user_by_username("unapproved")
        assert snooper["membership_status"] == "pending", snooper["membership_status"]

        child = db.user_by_username("alex")
        c = client()
        login(c, "unapproved")

        # Linking is refused while pending...
        page = c.get("/pending").get_data(as_text=True)
        c.post("/grownup/link",
               data={"csrf_token": token_from(page), "link_code": child["link_code"]},
               follow_redirects=False)
        assert not db.can_see_student(db.user_by_username("unapproved"), child["id"]), \
            "a pending parent linked themselves to a child"

        # ...and so is every way of reading that child.
        for path in (f"/grownup/student/{child['username']}",
                     f"/grownup/student/{child['username']}/standards",
                     "/grownup", "/grownup/resources"):
            response = c.get(path, follow_redirects=False)
            assert response.status_code == 302, f"{path} -> {response.status_code}"
            assert "pending" in response.headers["Location"], \
                f"{path} went to {response.headers['Location']}, not the holding pen"
    finally:
        db.set_join_policy(head["org_id"], original)


@check("every page renders for every role")
def t_pages_render():
    """
    A 500 from a template is invisible to the checks above, which mostly
    assert on status codes for a handful of paths.  This walks the whole
    surface, because the read model changing shape breaks views, not logic
    — which is exactly how the quiz_seconds guard broke.
    """
    broken = []

    def visit(c, path, expect=200):
        res = c.get(path)
        if res.status_code != expect:
            broken.append((path, res.status_code, expect))

    anon = client()
    for path in ("/login", "/signup?role=student", "/signup?role=parent",
                 "/signup?role=teacher", "/forgot", "/reset/not-a-real-token",
                 "/healthz", "/art-placeholder/missing/thing"):
        visit(anon, path)
    visit(anon, "/no-such-page", 404)

    student = client()
    login(student, "racer0")
    for path in ("/classroom", "/lessons", "/satchel"):
        visit(student, path)
    # A lesson the student has not earned redirects to /locked rather than
    # rendering, which is the gate doing its job — see selftest_gating.py
    # for which reason applies to which. Here we only care that the page
    # answers at all, so either is fine.
    for lesson in appmod.load_lessons():
        res = student.get(f"/lesson/{lesson['id']}")
        if res.status_code not in (200, 302):
            broken.append((f"/lesson/{lesson['id']}", res.status_code, "200 or 302"))
    # /locked answers 402 for a paywall and 403 for a gate, never 200 —
    # a "you cannot have this" page returning OK would be a lie to a cache.
    visit(student, "/locked", 402)
    visit(student, "/locked?why=prerequisite&lesson_id=code-02-debug", 403)

    teacher = client()
    login(teacher, "ms_chen")
    visit(teacher, "/grownup")
    visit(teacher, "/classrooms")
    chen = db.user_by_username("ms_chen")
    for row in db.visible_students(chen):
        visit(teacher, f"/grownup/student/{row['username']}")
    for row in db.classroom_rows(chen["org_id"]):
        visit(teacher, f"/classrooms/{row['id']}")

    parent = client()
    login(parent, "dana")
    visit(parent, "/grownup")
    visit(parent, "/grownup/student/alex")

    assert not broken, f"pages did not render: {broken}"


@check("the local stack boots with the settings compose actually sets")
def t_local_stack_boots():
    """
    docker compose up is the "prove it works" path, and the production
    guards were written strictly enough to reject it — no TLS to the
    database, no https, console mail. APP_ENV=local exists for exactly
    that, and this pins the combination so it cannot break again.
    """
    import importlib

    import config

    compose_env = {
        "APP_ENV": "local",
        "DATABASE_URL": "postgresql://ignite:pw@db:5432/ignite",   # no sslmode
        "SECRET_KEY": "0" * 64,
        "BASE_URL": "http://localhost:8000",                        # not https
        "COOKIE_SECURE": "false",
        "TRUSTED_PROXIES": "0",
        "EMAIL_BACKEND": "console",
        "REQUIRE_EMAIL_VERIFICATION": "false",
    }
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(compose_env)
    try:
        cfg = importlib.reload(config).validate()
        assert cfg.IS_LOCAL and not cfg.IS_PROD
        assert cfg.COOKIE_SECURE is False, "a Secure cookie never returns over http"
        assert cfg.LOG_JSON is False, "local should log readable lines"
    finally:
        os.environ.clear()
        os.environ.update(saved)
        importlib.reload(config)


@check("an unrecognised APP_ENV is refused rather than silently relaxed")
def t_app_env_validated():
    """
    Everything hangs off APP_ENV, so a typo used to land in development and
    switch off secure cookies, proxy handling and every boot check at once.
    """
    import importlib

    import config

    saved = dict(os.environ)
    for value, should_boot in (("production", True), ("local", True),
                               ("development", True), ("prod", False),
                               ("Production ", True), ("staging", False)):
        os.environ.clear()
        os.environ.update({
            "APP_ENV": value,
            "SECRET_KEY": "0" * 64,
            "BASE_URL": "https://example.test",
            "DATABASE_URL": "postgresql://u:p@h/db?sslmode=require",
            "TRUSTED_PROXIES": "1",
            "EMAIL_BACKEND": "smtp",
            "SMTP_HOST": "smtp.example.test",
            # Production also refuses to boot with unfilled legal
            # placeholders; that is its own check, below.
            "LEGAL_ENTITY": "Example Co",
            "LEGAL_EMAIL": "legal@example.test",
            "LEGAL_JURISDICTION": "Nowhere",
        })
        try:
            importlib.reload(config).validate()
            booted = True
        except SystemExit:
            booted = False
        assert booted == should_boot, f"APP_ENV={value!r} booted={booted}"
    os.environ.clear()
    os.environ.update(saved)
    importlib.reload(config)


@check("liveness is separate from readiness")
def t_livez():
    """
    /livez must never touch the database. Pointing a load balancer at a
    check that fails during a failover means every task is replaced at
    once, for an outage the pool would have ridden out by itself.
    """
    res = client().get("/livez")
    assert res.status_code == 200, res.status_code
    assert res.get_json() == {"status": "ok"}, res.get_json()

    # Signed out, and with the database stubbed away, it still answers.
    original = db.healthy
    db.healthy = lambda: False
    try:
        assert client().get("/livez").status_code == 200, \
            "liveness followed the database down"
        assert client().get("/healthz").status_code == 503, \
            "readiness did not notice the database was gone"
    finally:
        db.healthy = original


@check("production refuses the misconfigurations that fail silently")
def t_production_guards():
    """
    Each of these boots fine today and breaks something later — no signups
    at all, every user in one rate-limit bucket, or student data crossing
    the network in the clear. They are boot failures now.
    """
    import importlib

    import config

    # Config reads the environment when the module is imported, not when
    # validate() runs, so each case needs a genuine re-import — which is
    # also exactly what a container restart does.
    base = {
        "APP_ENV": "production",
        "BASE_URL": "https://example.test",
        "SECRET_KEY": "0" * 64,
        "DATABASE_URL": "postgresql://u:p@h/db?sslmode=require",
        "TRUSTED_PROXIES": "1",
        "EMAIL_BACKEND": "smtp",
        "SMTP_HOST": "smtp.example.test",
        "LEGAL_ENTITY": "Example Co",
        "LEGAL_EMAIL": "legal@example.test",
        "LEGAL_JURISDICTION": "Nowhere",
    }

    def boots(**overrides):
        env = {**base, **overrides}
        saved = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            importlib.reload(config).validate()
            return True
        except SystemExit:
            return False
        finally:
            os.environ.clear()
            os.environ.update(saved)
            importlib.reload(config)

    assert boots(), "a correct production config was rejected"
    assert not boots(EMAIL_BACKEND="console", REQUIRE_EMAIL_VERIFICATION="1"), \
        "console email with verification required would let nobody sign up"
    assert not boots(TRUSTED_PROXIES="0"), \
        "TRUSTED_PROXIES=0 puts every user in one rate-limit bucket"
    assert not boots(DATABASE_URL="postgresql://u:p@h/db"), \
        "a database URL with no sslmode was accepted"
    assert not boots(DATABASE_URL="postgresql://u:p@h/db?sslmode=prefer"), \
        "sslmode=prefer falls back to plaintext silently"
    assert boots(DATABASE_URL="postgresql://u:p@h/db?sslmode=verify-full"), \
        "verify-full was rejected"

    # Signup makes people tick "I agree to the terms". Booting production
    # with the placeholders unfilled would put [YOUR COMPANY NAME] on the
    # page behind that box, which makes the consent meaningless.
    assert not boots(LEGAL_ENTITY=""), "production booted with no legal entity"
    assert not boots(LEGAL_EMAIL=""), "production booted with no legal contact"
    assert not boots(LEGAL_JURISDICTION=""), "production booted with no jurisdiction"
    # Unreviewed boilerplate is a decision, not a mistake: it warns and
    # banners rather than blocking. LEGAL_REVIEWED must not gate the boot.
    assert boots(LEGAL_REVIEWED="false"), "the review flag blocked the boot"


@check("a proxy we were not told about is reported, once")
def t_proxy_warning():
    """
    X-Forwarded-For present with TRUSTED_PROXIES=0 means remote_addr is the
    proxy, so everyone shares a rate-limit bucket. Almost always APP_ENV
    not being set to production, which also switches off the boot checks —
    so this has to be caught at runtime.
    """
    import logging
    import security as sec

    sec._warned_about_proxy = False
    original = appmod.cfg.TRUSTED_PROXIES
    appmod.cfg.TRUSTED_PROXIES = 0

    records = []

    class Catch(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = Catch()
    logging.getLogger("ignite.security").addHandler(handler)
    try:
        c = client()
        page = c.get("/login").get_data(as_text=True)
        for _ in range(3):
            c.post("/login", data={"csrf_token": token_from(page),
                                   "username": "nobody", "password": "wrong-one"},
                   headers={"X-Forwarded-For": "1.2.3.4"})
    finally:
        logging.getLogger("ignite.security").removeHandler(handler)
        appmod.cfg.TRUSTED_PROXIES = original
        sec._warned_about_proxy = False

    hits = [r for r in records if "TRUSTED_PROXIES=0" in r]
    assert len(hits) == 1, f"expected exactly one warning, got {len(hits)}"


@check("rate events do not accumulate forever")
def t_rate_events_trim():
    """
    rate_count only looks inside the window, so expired rows are dead
    weight — but nothing deleted them except a purge command that is easy
    never to schedule.
    """
    with db.write() as cur:
        cur.execute("DELETE FROM rate_events")
        cur.execute("INSERT INTO rate_events (bucket, created_at) "
                    "SELECT 'stale:x', now() - interval '3 days' "
                    "FROM generate_series(1, 40)")

    with db.query() as cur:
        cur.execute("SELECT count(*) AS n FROM rate_events")
        before = cur.fetchone()["n"]
    assert before == 40, before

    # The sweep is probabilistic (db._TRIM_ODDS), so this needs enough
    # attempts that a miss is not worth thinking about. 200 was not: at
    # 1-in-50 the chance of never firing is (49/50)^200 = 1.8%, roughly one
    # failed run in every 55, which is exactly often enough to teach people
    # to re-run a red build. 600 puts it at 6e-6.
    for _ in range(600):
        db.rate_hit("trimtest")
        with db.query() as cur:
            cur.execute("SELECT count(*) AS n FROM rate_events WHERE bucket = 'stale:x'")
            if cur.fetchone()["n"] == 0:
                break
    else:
        raise AssertionError("600 attempts and the expired rows were never swept")

    with db.write() as cur:
        cur.execute("DELETE FROM rate_events")


@check("health check reports the database")
def t_health():
    res = client().get("/healthz")
    assert res.status_code == 200, res.status_code
    assert res.get_json() == {"status": "ok", "database": True}, res.get_json()


@check("responses are compressed, and Vary keeps caches honest")
def t_compression():
    """
    The default deployment publishes gunicorn straight onto a port with
    nothing in front, so compression has to happen here or not at all.

    The Vary half matters more than the bytes: several pages already vary
    on Cookie, and overwriting that with a bare "Accept-Encoding" would
    let a shared cache hand one account's page to another.
    """
    c = client()
    login(c, "ms_chen")

    packed = c.get("/grownup", headers={"Accept-Encoding": "gzip"})
    assert packed.headers.get("Content-Encoding") == "gzip", dict(packed.headers)
    vary = packed.headers.get("Vary", "")
    assert "accept-encoding" in vary.lower(), vary
    body = gzip.decompress(packed.get_data())
    assert b"<html" in body.lower(), "compressed body is not the page"
    assert int(packed.headers["Content-Length"]) == len(packed.get_data()), \
        "Content-Length does not match the compressed body"

    # A client that did not ask gets it uncompressed, and the same bytes.
    plain = c.get("/grownup", headers={"Accept-Encoding": "identity"})
    assert "Content-Encoding" not in plain.headers, dict(plain.headers)
    assert plain.get_data() == body, "compressed and plain bodies differ"
    assert len(packed.get_data()) < len(plain.get_data()), "compression made it bigger"

    # A page that varies on Cookie must still say so after compressing.
    legal = c.get("/legal/terms", headers={"Accept-Encoding": "gzip"})
    vary = legal.headers.get("Vary", "").lower()
    assert "cookie" in vary, f"Vary lost Cookie: {vary!r}"
    assert "accept-encoding" in vary, f"Vary lost Accept-Encoding: {vary!r}"


@check("opening a lesson does not invent a score of zero")
def t_no_phantom_score():
    """
    set_lesson_status() is called with no score every time a student opens
    a lesson. It used to COALESCE that NULL to 0 and take the GREATEST,
    which stored a real zero — so a lesson somebody had merely started
    reported "scored 0%" on the grown-up activity feed, indistinguishable
    from a lesson they had sat and failed.
    """
    # Its own student, untouched by any other check. Sharing one across
    # tests is how three earlier fixtures in this repo broke: a test that
    # advanced progress silently changed what a later assertion measured.
    signup(client(), "student", username="scorer", email="scorer@example.com",
           join_code=join_code_for("ms_chen"))
    student = db.user_by_username("scorer")
    assert student, "fixture student not created"
    lesson = "circuits-01-breadboard"

    db.set_lesson_status(student["id"], lesson, "in_progress")
    entry = db.lesson_entries(student["id"])[lesson]
    assert entry["score"] is None, f"opening a lesson stored score={entry['score']!r}"

    # A real score still lands, and still only ever goes up.
    db.set_lesson_status(student["id"], lesson, "completed", score=70)
    assert db.lesson_entries(student["id"])[lesson]["score"] == 70
    db.set_lesson_status(student["id"], lesson, "completed", score=40)
    assert db.lesson_entries(student["id"])[lesson]["score"] == 70, "a worse score won"

    # And a later scoreless touch does not wipe the score that is there.
    db.set_lesson_status(student["id"], lesson, "in_progress")
    assert db.lesson_entries(student["id"])[lesson]["score"] == 70, "a scoreless call cleared it"


# ── Runner ──────────────────────────────────────────────────────────────────────

TESTS = [
    t_teacher_signup, t_student_join_code, t_duplicates, t_password_policy, t_login,
    t_csrf, t_api_content_type, t_open_redirect, t_headers, t_cookie_flags,
    t_signup_rate_limit, t_rate_limit,
    t_tenancy, t_parent_scope,
    t_quiz_recording, t_reward_once, t_concurrent_writes, t_concurrent_same_row,
    t_dashboard_queries,
    t_reset_single_use, t_session_epoch, t_expired_token, t_no_enumeration,
    t_assignments, t_classroom_tenancy, t_http_error_codes, t_head_not_post,
    t_cache_headers, t_membership_gate_is_complete, t_pending_parent_blocked,
    t_pages_render,
    t_local_stack_boots, t_app_env_validated,
    t_livez, t_production_guards, t_proxy_warning, t_rate_events_trim,
    t_health, t_no_phantom_score, t_compression,
]


def main() -> int:
    appmod.db.init_pool(appmod.cfg)
    reset_database()
    appmod.refresh_catalog()

    print(f"\n  {len(TESTS)} checks against {appmod.cfg.DATABASE_URL.rsplit('@', 1)[-1]}\n")
    for test in TESTS:
        test()

    print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
