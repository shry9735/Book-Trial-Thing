#!/usr/bin/env python3
"""
selftest_accounts.py — provisioned accounts, password changes, deletion.

Three things that are only really testable against a real database, and
all three of which fail quietly if you get them wrong:

  Does erasure actually erase?   delete_user() leans entirely on the
  foreign keys cascading. A table added later without ON DELETE CASCADE
  leaves a child row behind and nothing complains, so the test writes a
  row into every child table and then asserts the lot is gone.

  Can a teacher only reset the passwords they should?   A teacher resetting
  a student they teach is the feature. A teacher resetting another
  teacher's password — or the org admin's — would turn one borrowed staff
  login into the whole school, so every wrong target is checked here.

  Does a handed-out password expire on use?   must_change_password has to
  hold the account on one page and nowhere else, or a printout left on a
  desk stays a working login for the term.

    DATABASE_URL=postgresql://.../ignite_test python selftest_accounts.py
"""

import os
import re
import sys

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "0")
os.environ.setdefault("SECRET_KEY", "0" * 64)
os.environ.setdefault("RL_SIGNUP_IP", "10000")
os.environ.setdefault("RL_LOGIN_IP", "10000")
os.environ.setdefault("RL_LOGIN_USER", "10000")

if os.environ.get("APP_ENV") == "production":
    sys.exit("selftest refuses to run against APP_ENV=production")

import app as appmod        # noqa: E402
import db                   # noqa: E402
import security             # noqa: E402

PASSED, FAILED = [], []
PASSWORD = "correct-horse-battery"


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
        "password": PASSWORD,
        "password_confirm": PASSWORD,
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


def login(c, username, password=PASSWORD):
    page = c.get("/login").get_data(as_text=True)
    return c.post("/login", data={"csrf_token": token_from(page),
                                  "username": username, "password": password},
                  follow_redirects=True)


def post(c, path, from_path, **fields):
    page = c.get(from_path).get_data(as_text=True)
    fields["csrf_token"] = token_from(page)
    return c.post(path, data=fields, follow_redirects=False)


def signed_in_teacher(username="head"):
    c = client()
    login(c, username)
    return c


# ── World ───────────────────────────────────────────────────────────────────────

WORLD = {}


def build_world():
    """
    One school: an admin (head), a classroom teacher (alpha) who teaches
    Period 1, a self-registered student (ana) in it, and a parent (pat)
    linked to ana. Plus a rival school, to keep the org boundary honest.
    """
    signup(client(), "teacher", username="head", email="head@school.test",
           org_name="Rivera Middle", name="Head Teacher")
    head = db.user_by_username("head")
    code = db.org_by_id(head["org_id"])["join_code"]

    signup(client(), "teacher", username="alpha", email="alpha@school.test",
           org_name="scratch", name="Mr Alpha")
    alpha = db.user_by_username("alpha")
    with db.write() as cur:
        cur.execute("UPDATE users SET org_id = %s, org_admin = false WHERE id = %s",
                    (head["org_id"], alpha["id"]))

    signup(client(), "student", username="ana", email="ana@home.test",
           join_code=code, name="Ana")
    signup(client(), "parent", username="pat", email="pat@home.test",
           join_code=code, name="Pat")

    ana = db.user_by_username("ana")
    db.link_parent(db.user_by_username("pat")["id"], ana["id"])

    p1 = db.create_classroom(head["org_id"], "Period 1", head["id"])
    db.add_classroom_teacher(p1, alpha["id"])
    db.add_classroom_student(p1, ana["id"])

    signup(client(), "teacher", username="rival", email="rival@other.test",
           org_name="Other School", name="Rival")
    rival = db.user_by_username("rival")
    signup(client(), "student", username="outsider", email="out@other.test",
           join_code=db.org_by_id(rival["org_id"])["join_code"], name="Outsider")

    WORLD.update(org=head["org_id"], p1=p1)


# ── Provisioning ────────────────────────────────────────────────────────────────

@check("a teacher can create a student login with no email address")
def t_provision_one():
    c = signed_in_teacher("alpha")
    page = f"/classrooms/{WORLD['p1']}"
    response = post(c, f"{page}/students/new", page,
                    name="Grace Hopper", consent_ok="1")
    assert response.status_code == 200, response.status_code

    grace = db.user_by_username("grace.hopper")
    assert grace, "no account created"
    assert grace["email"] is None, f"email should be NULL, got {grace['email']!r}"
    assert grace["must_change_password"], "provisioned account is not forced to change"
    assert grace["created_by"] == db.user_by_username("alpha")["id"], "created_by not recorded"
    assert grace["age_confirmed_at"], "the teacher's attestation was not recorded"


@check("the first password is shown once and is not stored in the clear")
def t_password_shown_once():
    c = signed_in_teacher("alpha")
    page = f"/classrooms/{WORLD['p1']}"
    html = post(c, f"{page}/students/new", page,
                name="Katherine Johnson", consent_ok="1").get_data(as_text=True)

    match = re.search(r'class="temp-pass">([^<]+)<', html)
    assert match, "the results page did not show a password"
    password = match.group(1).strip()

    row = db.user_by_username("katherine.johnson")
    assert password not in row["password_hash"], "the password is recoverable from the hash"
    # And it is a working password, once.
    fresh = client()
    login(fresh, "katherine.johnson", password)
    assert fresh.get("/", follow_redirects=False).status_code == 302


@check("a provisioned student lands in the classroom that made them")
def t_provisioned_in_classroom():
    c = signed_in_teacher("alpha")
    page = f"/classrooms/{WORLD['p1']}"
    post(c, f"{page}/students/new", page, name="Ada Lovelace", consent_ok="1")

    ada = db.user_by_username("ada.lovelace")
    roster = {s["id"] for s in db.classroom_students(WORLD["p1"])}
    assert ada["id"] in roster, "created but not in the classroom"
    # And therefore visible to the teacher who created them.
    assert db.can_see_student(db.user_by_username("alpha"), ada["id"])


@check("creating a login requires the consent checkbox")
def t_consent_required():
    c = signed_in_teacher("alpha")
    page = f"/classrooms/{WORLD['p1']}"
    post(c, f"{page}/students/new", page, name="No Consent")
    assert db.user_by_username("no.consent") is None, "created without consent"


@check("a teacher cannot provision into a classroom they do not teach")
def t_provision_scoped():
    head = db.user_by_username("head")
    other = db.create_classroom(head["org_id"], "Period 9", head["id"])
    c = signed_in_teacher("alpha")          # alpha teaches Period 1 only
    response = post(c, f"/classrooms/{other}/students/new", "/classrooms",
                    name="Sneaky Student", consent_ok="1")
    assert response.status_code == 404, response.status_code
    assert db.user_by_username("sneaky.student") is None


@check("a teacher cannot provision into another school's classroom")
def t_provision_cross_org():
    rival = db.user_by_username("rival")
    theirs = db.create_classroom(rival["org_id"], "Their Room", rival["id"])
    c = signed_in_teacher("head")           # admin, but of the wrong org
    response = post(c, f"/classrooms/{theirs}/students/new", "/classrooms",
                    name="Cross Org", consent_ok="1")
    assert response.status_code == 404, response.status_code
    assert db.user_by_username("cross.org") is None


@check("derived usernames do not collide")
def t_username_collision():
    c = signed_in_teacher("alpha")
    page = f"/classrooms/{WORLD['p1']}"
    for _ in range(3):
        post(c, f"{page}/students/new", page, name="Sam Twin", consent_ok="1")
    assert db.user_by_username("sam.twin"), "first Sam missing"
    assert db.user_by_username("sam.twin2"), "second Sam did not get a suffix"
    assert db.user_by_username("sam.twin3"), "third Sam did not get a suffix"


# ── Roster import ───────────────────────────────────────────────────────────────

@check("a pasted roster creates the whole class")
def t_import_roster():
    c = signed_in_teacher("alpha")
    page = f"/classrooms/{WORLD['p1']}/students/import"
    html = post(c, page, page, consent_ok="1", roster=(
        "name,username\n"
        "Alan Turing\n"
        "Barbara Liskov, blisk\n"
        "Carol Shaw\n"
    )).get_data(as_text=True)

    assert db.user_by_username("alan.turing"), "row 1 missing"
    assert db.user_by_username("blisk"), "explicit username ignored"
    assert db.user_by_username("carol.shaw"), "row 3 missing"
    assert "blisk" in html, "the results page did not list the new accounts"
    # The header row must not have become a student.
    assert db.user_by_username("name") is None, "the header row was imported"


@check("one bad row does not defeat the rest of the import")
def t_import_partial():
    c = signed_in_teacher("alpha")
    page = f"/classrooms/{WORLD['p1']}/students/import"
    html = post(c, page, page, consent_ok="1", roster=(
        "Good Student One\n"
        "Duplicate Person, head\n"        # username already belongs to a teacher
        "Good Student Two\n"
    )).get_data(as_text=True)

    assert db.user_by_username("good.student.one"), "row before the bad one was lost"
    assert db.user_by_username("good.student.two"), "row after the bad one was lost"
    assert "Skipped" in html, "the failure was not reported"
    # And the clash did not overwrite the teacher.
    assert db.user_by_username("head")["role"] == "teacher", "a teacher was overwritten"


@check("an oversized import is refused whole")
def t_import_capped():
    c = signed_in_teacher("alpha")
    page = f"/classrooms/{WORLD['p1']}/students/import"
    roster = "\n".join(f"Bulk Student {i}" for i in range(appmod._MAX_IMPORT + 5))
    post(c, page, page, consent_ok="1", roster=roster)
    assert db.user_by_username("bulk.student.0") is None, "an over-cap import went through"


@check("the roster parser tolerates real spreadsheet output")
def t_parse_roster():
    rows = appmod._parse_roster(
        'Student Name,Username\n'
        '"Lovelace, Ada",ada.l,ignored-column\n'
        '\n'
        '   Grace Hopper   \n'
    )
    assert rows == [("Lovelace, Ada", "ada.l"), ("Grace Hopper", "")], rows


# ── The forced first password ───────────────────────────────────────────────────

def provision(name: str) -> tuple[str, str]:
    """Create a student through the UI and return (username, password)."""
    c = signed_in_teacher("alpha")
    page = f"/classrooms/{WORLD['p1']}"
    html = post(c, f"{page}/students/new", page,
                name=name, consent_ok="1").get_data(as_text=True)
    username = re.search(r'<code>([^<]+)</code>\s*</td>\s*<td>\s*<code class="temp-pass"',
                         html).group(1)
    password = re.search(r'class="temp-pass">([^<]+)<', html).group(1).strip()
    return username.strip(), password


@check("a handed-out password reaches only the change-password page")
def t_forced_change_gate():
    username, password = provision("Gated Pupil")
    c = client()
    login(c, username, password)

    for path in ("/", "/classroom", "/lessons", "/satchel"):
        response = c.get(path, follow_redirects=False)
        assert response.status_code == 302, f"{path} was reachable ({response.status_code})"
        assert response.headers["Location"].endswith("/settings/first-password"), \
            f"{path} redirected to {response.headers['Location']}"

    assert c.get("/settings/first-password").status_code == 200


@check("the forced gate answers the API with 403, not a redirect")
def t_forced_change_api():
    username, password = provision("Api Pupil")
    c = client()
    login(c, username, password)
    response = c.post("/api/progress", json={"lesson_id": "x", "status": "in_progress"})
    assert response.status_code == 403, response.status_code


@check("setting a first password opens the rest of the site")
def t_first_password_clears():
    username, password = provision("Freed Pupil")
    c = client()
    login(c, username, password)

    page = c.get("/settings/first-password").get_data(as_text=True)
    response = c.post("/settings/first-password",
                      data={"csrf_token": token_from(page),
                            "password": "brand-new-passphrase",
                            "password_confirm": "brand-new-passphrase"},
                      follow_redirects=False)
    assert response.status_code == 302, response.status_code

    assert not db.user_by_username(username)["must_change_password"], "flag not cleared"
    # Still signed in on this device, and now able to move around.
    assert c.get("/classroom", follow_redirects=False).status_code == 200

    # The old handed-out password is dead.
    stale = client()
    login(stale, username, password)
    assert stale.get("/", follow_redirects=False).status_code == 302
    assert "login" in stale.get("/", follow_redirects=False).headers["Location"]


@check("a provisioned student can sign in with verification switched on")
def t_no_email_verification_bypass():
    username, password = provision("Verified Pupil")
    appmod.cfg.REQUIRE_EMAIL_VERIFICATION = True
    try:
        c = client()
        login(c, username, password)
        assert c.get("/settings/first-password").status_code == 200, \
            "an account with no email was blocked by email verification"
    finally:
        appmod.cfg.REQUIRE_EMAIL_VERIFICATION = False


@check("verification still gates an account that does have an email")
def t_verification_still_applies():
    signup(client(), "student", username="unverified", email="unv@home.test",
           join_code=db.org_by_id(WORLD["org"])["join_code"], name="Unverified")
    with db.write() as cur:
        cur.execute("UPDATE users SET email_verified = false WHERE username = 'unverified'")

    appmod.cfg.REQUIRE_EMAIL_VERIFICATION = True
    try:
        c = client()
        login(c, "unverified")
        assert c.get("/", follow_redirects=False).status_code == 302, \
            "an unverified account with an email got in"
    finally:
        appmod.cfg.REQUIRE_EMAIL_VERIFICATION = False


# ── Teacher-initiated reset ─────────────────────────────────────────────────────

@check("a teacher can reset a student they teach")
def t_teacher_reset():
    c = signed_in_teacher("alpha")
    html = post(c, "/grownup/student/ana/reset-password",
                "/grownup/student/ana").get_data(as_text=True)
    password = re.search(r'class="temp-pass">([^<]+)<', html).group(1).strip()

    assert db.user_by_username("ana")["must_change_password"], "reset did not force a change"
    fresh = client()
    login(fresh, "ana", password)
    assert fresh.get("/settings/first-password").status_code == 200

    # The student's old password no longer works.
    stale = client()
    login(stale, "ana", PASSWORD)
    assert stale.get("/", follow_redirects=False).status_code == 302


@check("a reset signs the student out of every device they were on")
def t_reset_kills_sessions():
    student = client()
    login(student, "ana")
    # (t_teacher_reset already forced a change; give ana a normal password back)
    db.set_password(db.user_by_username("ana")["id"],
                    appmod.generate_password_hash(PASSWORD))
    student = client()
    login(student, "ana")
    assert student.get("/classroom", follow_redirects=False).status_code == 200

    teacher = signed_in_teacher("alpha")
    post(teacher, "/grownup/student/ana/reset-password", "/grownup/student/ana")

    assert student.get("/classroom", follow_redirects=False).status_code == 302, \
        "the student's existing session survived a reset"


@check("a teacher cannot reset another teacher's password")
def t_reset_teacher_refused():
    before = db.user_by_username("head")["password_hash"]
    c = signed_in_teacher("alpha")
    response = post(c, "/grownup/student/head/reset-password", "/grownup")
    assert response.status_code == 404, response.status_code
    assert db.user_by_username("head")["password_hash"] == before, \
        "a teacher reset the admin's password"


@check("a teacher cannot reset a parent's password")
def t_reset_parent_refused():
    before = db.user_by_username("pat")["password_hash"]
    c = signed_in_teacher("alpha")
    response = post(c, "/grownup/student/pat/reset-password", "/grownup")
    assert response.status_code == 404, response.status_code
    assert db.user_by_username("pat")["password_hash"] == before


@check("a teacher cannot reset a student they do not teach")
def t_reset_out_of_classroom_refused():
    head = db.user_by_username("head")
    signup(client(), "student", username="elsewhere", email="else@home.test",
           join_code=db.org_by_id(head["org_id"])["join_code"], name="Elsewhere")
    before = db.user_by_username("elsewhere")["password_hash"]

    c = signed_in_teacher("alpha")          # teaches Period 1; this student is unplaced
    response = post(c, "/grownup/student/elsewhere/reset-password", "/grownup")
    assert response.status_code == 404, response.status_code
    assert db.user_by_username("elsewhere")["password_hash"] == before


@check("a teacher cannot reset a student in another school")
def t_reset_cross_org_refused():
    before = db.user_by_username("outsider")["password_hash"]
    c = signed_in_teacher("head")
    response = post(c, "/grownup/student/outsider/reset-password", "/grownup")
    assert response.status_code == 404, response.status_code
    assert db.user_by_username("outsider")["password_hash"] == before


@check("a parent cannot reset their own child's password")
def t_reset_parent_actor_refused():
    before = db.user_by_username("ana")["password_hash"]
    c = client()
    login(c, "pat")
    response = post(c, "/grownup/student/ana/reset-password", "/grownup")
    assert response.status_code in (302, 404), response.status_code
    assert db.user_by_username("ana")["password_hash"] == before


# ── Changing your own password ──────────────────────────────────────────────────

@check("changing your own password requires the current one")
def t_change_needs_current():
    c = signed_in_teacher("head")
    before = db.user_by_username("head")["password_hash"]
    post(c, "/settings/password", "/settings",
         current_password="not-the-password",
         password="a-brand-new-password", password_confirm="a-brand-new-password")
    assert db.user_by_username("head")["password_hash"] == before, \
        "the password changed without the current one"


@check("changing your own password works and keeps you signed in here")
def t_change_password():
    c = signed_in_teacher("alpha")
    response = post(c, "/settings/password", "/settings",
                    current_password=PASSWORD,
                    password="alpha-new-password", password_confirm="alpha-new-password")
    assert response.status_code == 302, response.status_code
    assert c.get("/grownup", follow_redirects=False).status_code == 200, \
        "changing your own password signed you out of the session that did it"

    fresh = client()
    login(fresh, "alpha", "alpha-new-password")
    assert fresh.get("/grownup", follow_redirects=False).status_code == 200

    db.set_password(db.user_by_username("alpha")["id"],
                    appmod.generate_password_hash(PASSWORD))


@check("changing a password signs out every other device")
def t_change_kills_other_sessions():
    other = signed_in_teacher("head")
    assert other.get("/grownup", follow_redirects=False).status_code == 200

    here = signed_in_teacher("head")
    post(here, "/settings/password", "/settings",
         current_password=PASSWORD,
         password="head-new-password", password_confirm="head-new-password")

    assert other.get("/grownup", follow_redirects=False).status_code == 302, \
        "an older session survived a password change"

    db.set_password(db.user_by_username("head")["id"],
                    appmod.generate_password_hash(PASSWORD))


@check("a signed-out visitor cannot reach the settings page")
def t_settings_requires_session():
    response = client().get("/settings", follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert "login" in response.headers["Location"]


# ── Deletion ────────────────────────────────────────────────────────────────────

def litter(student_id: int) -> None:
    """Write one row into every table that hangs off a user."""
    with db.write() as cur:
        cur.execute("INSERT INTO lesson_progress (student_id, lesson_id, status) "
                    "VALUES (%s, 'circuits-01-breadboard', 'in_progress') "
                    "ON CONFLICT DO NOTHING", (student_id,))
        cur.execute("INSERT INTO quiz_answers (student_id, lesson_id, question_id, "
                    "tries, chosen, correct) "
                    "VALUES (%s, 'circuits-01-breadboard', 'q1', 1, 0, true) "
                    "ON CONFLICT DO NOTHING", (student_id,))
        cur.execute("INSERT INTO example_answers (student_id, lesson_id, example_id, "
                    "tries, chosen, correct) "
                    "VALUES (%s, 'circuits-01-breadboard', 'e1', 1, 0, true) "
                    "ON CONFLICT DO NOTHING", (student_id,))
        cur.execute("INSERT INTO inventory (student_id, item_id) VALUES (%s, 'wire') "
                    "ON CONFLICT DO NOTHING", (student_id,))
        cur.execute("INSERT INTO assignments (student_id, lesson_ids) "
                    "VALUES (%s, ARRAY['circuits-01-breadboard']) "
                    "ON CONFLICT DO NOTHING", (student_id,))
        cur.execute("INSERT INTO auth_tokens (token_hash, user_id, purpose, expires_at) "
                    "VALUES (%s, %s, 'reset', now() + interval '1 hour')",
                    (security.hash_token(f"tok-{student_id}"), student_id))


def subscribe(user_id: int, status: str, *, customer="cus_test", stripe_id="sub_test"):
    """A parent subscription in a given state, with the fields Stripe sends."""
    return db.upsert_subscription(
        account_kind="parent", org_id=None, user_id=user_id,
        stripe_customer_id=customer, stripe_subscription_id=stripe_id,
        status=status, plan="family", seats=1,
        collection_method="charge_automatically",
        current_period_end=None, cancel_at_period_end=False, trial_end=None)


CHILD_TABLES = ("lesson_progress", "quiz_answers", "example_answers", "inventory",
                "assignments", "auth_tokens", "classroom_students", "parent_links")


def child_rows(student_id: int) -> dict[str, int]:
    counts = {}
    with db.query() as cur:
        for table in CHILD_TABLES:
            column = "user_id" if table == "auth_tokens" else "student_id"
            cur.execute(f"SELECT count(*) AS n FROM {table} WHERE {column} = %s",
                        (student_id,))
            counts[table] = cur.fetchone()["n"]
    return counts


@check("deleting a student removes every row that belonged to them")
def t_delete_cascades():
    ana = db.user_by_username("ana")
    litter(ana["id"])
    before = child_rows(ana["id"])
    assert all(before.values()), f"the fixture did not populate every table: {before}"

    db.delete_user(ana["id"])

    assert db.user_by_username("ana") is None, "the account survived"
    after = child_rows(ana["id"])
    assert not any(after.values()), f"rows left behind: {after}"


@check("deleting a student leaves the rest of the school alone")
def t_delete_scoped():
    head = db.user_by_username("head")
    signup(client(), "student", username="doomed", email="doomed@home.test",
           join_code=db.org_by_id(head["org_id"])["join_code"], name="Doomed")
    doomed = db.user_by_username("doomed")
    db.add_classroom_student(WORLD["p1"], doomed["id"])
    survivors = {s["username"] for s in db.classroom_students(WORLD["p1"])} - {"doomed"}

    db.delete_user(doomed["id"])

    still = {s["username"] for s in db.classroom_students(WORLD["p1"])}
    assert still == survivors, f"took others with it: {survivors - still}"
    assert db.org_by_id(head["org_id"]), "the org was deleted"


@check("an admin can delete a student through the dashboard")
def t_admin_delete_route():
    head = db.user_by_username("head")
    signup(client(), "student", username="removeme", email="rm@home.test",
           join_code=db.org_by_id(head["org_id"])["join_code"], name="Remove Me")
    db.add_classroom_student(WORLD["p1"], db.user_by_username("removeme")["id"])

    c = signed_in_teacher("head")
    post(c, "/grownup/student/removeme/delete", "/grownup/student/removeme",
         confirm="DELETE")
    assert db.user_by_username("removeme") is None, "the account survived"


@check("deleting a student needs the typed confirmation")
def t_delete_needs_confirmation():
    head = db.user_by_username("head")
    signup(client(), "student", username="keepme", email="keep@home.test",
           join_code=db.org_by_id(head["org_id"])["join_code"], name="Keep Me")
    db.add_classroom_student(WORLD["p1"], db.user_by_username("keepme")["id"])

    c = signed_in_teacher("head")
    post(c, "/grownup/student/keepme/delete", "/grownup/student/keepme", confirm="yes")
    assert db.user_by_username("keepme"), "deleted without confirmation"


@check("a non-admin teacher cannot delete a student")
def t_delete_admin_only():
    head = db.user_by_username("head")
    signup(client(), "student", username="safeone", email="safe@home.test",
           join_code=db.org_by_id(head["org_id"])["join_code"], name="Safe One")
    db.add_classroom_student(WORLD["p1"], db.user_by_username("safeone")["id"])

    c = signed_in_teacher("alpha")          # teaches them, but is not an admin
    response = post(c, "/grownup/student/safeone/delete",
                    f"/classrooms/{WORLD['p1']}", confirm="DELETE")
    assert response.status_code == 404, response.status_code
    assert db.user_by_username("safeone"), "a non-admin deleted a student"


@check("an admin cannot delete a student in another school")
def t_delete_cross_org():
    c = signed_in_teacher("head")
    response = post(c, "/grownup/student/outsider/delete", "/grownup", confirm="DELETE")
    assert response.status_code == 404, response.status_code
    assert db.user_by_username("outsider"), "deleted across the org boundary"


@check("you can delete your own account")
def t_delete_self():
    head = db.user_by_username("head")
    signup(client(), "parent", username="leaver", email="leaver@home.test",
           join_code=db.org_by_id(head["org_id"])["join_code"], name="Leaver")

    c = client()
    login(c, "leaver")
    response = post(c, "/settings/delete", "/settings",
                    password=PASSWORD, confirm="DELETE")
    assert response.status_code == 302, response.status_code
    assert db.user_by_username("leaver") is None, "the account survived"
    # And the session went with it.
    assert c.get("/grownup", follow_redirects=False).status_code == 302


@check("deleting your own account needs your password")
def t_delete_self_needs_password():
    head = db.user_by_username("head")
    signup(client(), "parent", username="stayer", email="stayer@home.test",
           join_code=db.org_by_id(head["org_id"])["join_code"], name="Stayer")

    c = client()
    login(c, "stayer")
    post(c, "/settings/delete", "/settings", password="wrong-password", confirm="DELETE")
    assert db.user_by_username("stayer"), "deleted with the wrong password"

    post(c, "/settings/delete", "/settings", password=PASSWORD, confirm="nope")
    assert db.user_by_username("stayer"), "deleted without typing DELETE"


@check("the last admin of an organisation cannot delete themselves")
def t_last_admin_blocked():
    assert db.count_org_admins(WORLD["org"]) == 1, "fixture expects exactly one admin"
    c = signed_in_teacher("head")
    post(c, "/settings/delete", "/settings", password=PASSWORD, confirm="DELETE")
    assert db.user_by_username("head"), "the only admin deleted themselves"

    blocker = appmod._deletion_blocker(db.user_by_username("head"))
    assert blocker and "only admin" in blocker, blocker


@check("a second admin unblocks the first one's deletion")
def t_second_admin_unblocks():
    db.set_org_admin(db.user_by_username("alpha")["id"], WORLD["org"], True)
    try:
        assert appmod._deletion_blocker(db.user_by_username("head")) is None
    finally:
        db.set_org_admin(db.user_by_username("alpha")["id"], WORLD["org"], False)


@check("a live subscription blocks deletion instead of leaving it billing")
def t_subscription_blocks_deletion():
    head = db.user_by_username("head")
    signup(client(), "parent", username="payer", email="payer@home.test",
           join_code=db.org_by_id(head["org_id"])["join_code"], name="Payer")
    payer = db.user_by_username("payer")

    subscribe(payer["id"], "active")

    blocker = appmod._deletion_blocker(db.user_by_username("payer"))
    assert blocker and "subscription" in blocker, blocker

    c = client()
    login(c, "payer")
    post(c, "/settings/delete", "/settings", password=PASSWORD, confirm="DELETE")
    assert db.user_by_username("payer"), "deleted while still being billed"


@check("a cancelled subscription stops blocking deletion")
def t_cancelled_subscription_allows_deletion():
    payer = db.user_by_username("payer")
    subscribe(payer["id"], "canceled")
    assert appmod._deletion_blocker(db.user_by_username("payer")) is None


@check("invoices survive the account they belonged to")
def t_invoices_kept():
    head = db.user_by_username("head")
    signup(client(), "parent", username="invoiced", email="inv@home.test",
           join_code=db.org_by_id(head["org_id"])["join_code"], name="Invoiced")
    invoiced = db.user_by_username("invoiced")

    subscription = subscribe(invoiced["id"], "canceled", customer="cus_inv",
                             stripe_id="sub_inv")
    db.upsert_invoice(stripe_invoice_id="in_test_1", subscription_id=subscription["id"],
                      number="INV-1", status="paid", amount_due=4900, amount_paid=4900,
                      currency="usd", due_date=None, hosted_invoice_url=None, pdf_url=None)

    db.delete_user(invoiced["id"])

    with db.query() as cur:
        cur.execute("SELECT subscription_id FROM invoices WHERE stripe_invoice_id = 'in_test_1'")
        row = cur.fetchone()
    assert row, "the financial record was deleted with the account"
    assert row["subscription_id"] is None, "the invoice still points at a deleted subscription"


# ── Rendering ───────────────────────────────────────────────────────────────────

@check("every new page renders")
def t_pages_render():
    teacher = signed_in_teacher("head")
    for path in ("/settings", f"/classrooms/{WORLD['p1']}/students/import",
                 f"/classrooms/{WORLD['p1']}"):
        response = teacher.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"

    # The student settings page uses the game chrome, not the teacher one.
    username, password = provision("Render Pupil")
    student = client()
    login(student, username, password)
    page = student.get("/settings/first-password")
    assert page.status_code == 200, page.status_code

    page = student.post("/settings/first-password",
                        data={"csrf_token": token_from(page.get_data(as_text=True)),
                              "password": "render-pupil-password",
                              "password_confirm": "render-pupil-password"})
    assert student.get("/settings").status_code == 200, "student settings page failed"


TESTS = [
    t_provision_one, t_password_shown_once, t_provisioned_in_classroom,
    t_consent_required, t_provision_scoped, t_provision_cross_org,
    t_username_collision,
    t_import_roster, t_import_partial, t_import_capped, t_parse_roster,
    t_forced_change_gate, t_forced_change_api, t_first_password_clears,
    t_no_email_verification_bypass, t_verification_still_applies,
    t_teacher_reset, t_reset_kills_sessions, t_reset_teacher_refused,
    t_reset_parent_refused, t_reset_out_of_classroom_refused,
    t_reset_cross_org_refused, t_reset_parent_actor_refused,
    t_change_needs_current, t_change_password, t_change_kills_other_sessions,
    t_settings_requires_session,
    t_delete_cascades, t_delete_scoped, t_admin_delete_route,
    t_delete_needs_confirmation, t_delete_admin_only, t_delete_cross_org,
    t_delete_self, t_delete_self_needs_password, t_last_admin_blocked,
    t_second_admin_unblocks, t_subscription_blocks_deletion,
    t_cancelled_subscription_allows_deletion, t_invoices_kept,
    t_pages_render,
]


def main() -> int:
    appmod.db.init_pool(appmod.cfg)
    reset_database()
    appmod.refresh_catalog()
    build_world()

    print(f"\n  {len(TESTS)} account checks\n")
    for test in TESTS:
        test()

    print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
