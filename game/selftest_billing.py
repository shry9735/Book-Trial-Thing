#!/usr/bin/env python3
"""
selftest_billing.py — subscriptions, org administration and net-30 terms.

Stripe itself is never called: every test here drives the code that
*surrounds* Stripe — entitlement resolution, webhook idempotency, seat
counting, who is allowed to spend money — because that is the part we
wrote and therefore the part that can be wrong.

The two things worth being explicit about:

  * Webhook handling is tested by constructing genuine Stripe-shaped
    event payloads and running them through the real handler with a
    stubbed API client. A retried or out-of-order event is normal Stripe
    traffic, not an edge case.

  * Entitlement is tested from the student's side, because that is where
    a mistake is visible: a child locked out of a lesson their school has
    paid for.

    DATABASE_URL=postgresql://.../ignite_test python selftest_billing.py
"""

import os
import re
import sys
from datetime import timedelta

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "0")
os.environ.setdefault("SECRET_KEY", "0" * 64)
os.environ.setdefault("RL_SIGNUP_IP", "10000")
# A key and a secret are needed for billing to be "on"; no request ever
# reaches Stripe, because every call is stubbed.
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_selftest")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_selftest")

if os.environ.get("APP_ENV") == "production":
    sys.exit("selftest refuses to run against APP_ENV=production")

import app as appmod        # noqa: E402
import billing              # noqa: E402
import db                   # noqa: E402

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
        "password": "correct-horse-battery",
        "password_confirm": "correct-horse-battery",
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


def login(c, username):
    page = c.get("/login").get_data(as_text=True)
    return c.post("/login", data={"csrf_token": token_from(page),
                                  "username": username,
                                  "password": "correct-horse-battery"},
                  follow_redirects=True)


def post(c, path, **fields):
    page = c.get(fields.pop("_from", "/org")).get_data(as_text=True)
    fields["csrf_token"] = token_from(page)
    return c.post(path, data=fields, follow_redirects=False)


def join_code(username):
    user = db.user_by_username(username)
    return db.org_by_id(user["org_id"])["join_code"]


def now():
    return billing.now()


# ── Fixtures ────────────────────────────────────────────────────────────────────

def build_world():
    """One school with an admin teacher, a second teacher, students, a parent."""
    signup(client(), "teacher", username="head", email="head@school.test",
           org_name="Rivera Middle", name="Ms. Chen")
    code = join_code("head")
    signup(client(), "teacher", username="deputy", email="deputy@school.test",
           org_name="ignored", name="Mr. Diaz")
    # A second teacher signing up creates their own org, so move them into
    # the first one the way a real invite would.
    head = db.user_by_username("head")
    deputy = db.user_by_username("deputy")
    with db.write() as cur:
        cur.execute("UPDATE users SET org_id = %s, org_admin = false WHERE id = %s",
                    (head["org_id"], deputy["id"]))

    signup(client(), "student", username="alex", email="alex@home.test",
           join_code=code, name="Alex Rivera")
    signup(client(), "student", username="jamie", email="jamie@home.test",
           join_code=code, name="Jamie Chen")
    signup(client(), "parent", username="dana", email="dana@home.test",
           join_code=code, name="Dana Rivera")

    dana = db.user_by_username("dana")
    alex = db.user_by_username("alex")
    db.link_parent(dana["id"], alex["id"])
    return head, code


def give_org_subscription(org_id, status="active", collection="charge_automatically",
                          period_end=None, seats=2):
    return db.upsert_subscription(
        account_kind="org", org_id=org_id, user_id=None,
        stripe_customer_id="cus_org", stripe_subscription_id=f"sub_org_{org_id}",
        status=status, plan="org_seat_monthly", seats=seats,
        collection_method=collection,
        current_period_end=period_end or (now() + timedelta(days=20)),
        cancel_at_period_end=False, trial_end=None)


def give_parent_subscription(user_id, status="active"):
    return db.upsert_subscription(
        account_kind="parent", org_id=None, user_id=user_id,
        stripe_customer_id="cus_parent", stripe_subscription_id=f"sub_par_{user_id}",
        status=status, plan="family_monthly", seats=1,
        collection_method="charge_automatically",
        current_period_end=now() + timedelta(days=20),
        cancel_at_period_end=False, trial_end=None)


def clear_subscriptions():
    with db.write() as cur:
        cur.execute("DELETE FROM subscriptions")


# ── Entitlement ─────────────────────────────────────────────────────────────────

@check("with no subscription a student is not entitled")
def t_no_subscription():
    clear_subscriptions()
    alex = db.user_by_username("alex")
    result = billing.entitlement_for(appmod.cfg, alex)
    assert result["active"] is False, result


@check("a school subscription covers its students")
def t_org_covers_students():
    clear_subscriptions()
    head = db.user_by_username("head")
    give_org_subscription(head["org_id"])

    for username in ("alex", "jamie"):
        result = billing.entitlement_for(appmod.cfg, db.user_by_username(username))
        assert result["active"] is True, (username, result)
        assert result["source"] == "org", result


@check("a parent subscription covers only that parent's own children")
def t_parent_covers_own_child():
    clear_subscriptions()
    dana = db.user_by_username("dana")
    give_parent_subscription(dana["id"])

    alex = billing.entitlement_for(appmod.cfg, db.user_by_username("alex"))
    assert alex["active"] is True and alex["source"] == "parent", alex

    # Jamie is in the same class but is not Dana's child.
    jamie = billing.entitlement_for(appmod.cfg, db.user_by_username("jamie"))
    assert jamie["active"] is False, "a parent's plan covered someone else's child"


@check("a lapsed card gets a grace window, then stops")
def t_card_grace():
    clear_subscriptions()
    head = db.user_by_username("head")
    cfg = appmod.cfg

    # Failed yesterday: still inside the window.
    give_org_subscription(head["org_id"], status="past_due",
                          period_end=now() - timedelta(days=1))
    result = billing.entitlement_for(cfg, db.user_by_username("alex"))
    assert result["active"] is True and result["in_grace"] is True, result

    # Failed longer ago than the window allows.
    clear_subscriptions()
    give_org_subscription(head["org_id"], status="past_due",
                          period_end=now() - timedelta(days=cfg.GRACE_DAYS_CARD + 2))
    result = billing.entitlement_for(cfg, db.user_by_username("alex"))
    assert result["active"] is False, "grace window never expired"


@check("an unpaid invoice gets the longer school grace window")
def t_invoice_grace():
    clear_subscriptions()
    head = db.user_by_username("head")
    cfg = appmod.cfg

    # Past the card window but inside the invoice one: a school working
    # through a PO must not lose access on a card-payment timetable.
    days = cfg.GRACE_DAYS_CARD + 5
    assert days < cfg.GRACE_DAYS_INVOICE, "test needs the invoice window to be longer"

    give_org_subscription(head["org_id"], status="past_due",
                          collection="send_invoice",
                          period_end=now() - timedelta(days=days))
    result = billing.entitlement_for(cfg, db.user_by_username("alex"))
    assert result["active"] is True, "a school on net-30 was cut off on card timings"
    assert result["in_grace"] is True, result


@check("a comp grants access with no Stripe subscription")
def t_comp():
    clear_subscriptions()
    head = db.user_by_username("head")
    db.set_comp_until(org_id=head["org_id"], user_id=None,
                      until=now() + timedelta(days=30))

    result = billing.entitlement_for(appmod.cfg, db.user_by_username("alex"))
    assert result["active"] is True and result["status"] == "comped", result

    db.set_comp_until(org_id=head["org_id"], user_id=None,
                      until=now() - timedelta(days=1))
    result = billing.entitlement_for(appmod.cfg, db.user_by_username("alex"))
    assert result["active"] is False, "an expired comp still granted access"


@check("one payer cannot end up with two live subscriptions")
def t_one_live_subscription():
    clear_subscriptions()
    head = db.user_by_username("head")
    give_org_subscription(head["org_id"])

    import psycopg
    try:
        db.upsert_subscription(
            account_kind="org", org_id=head["org_id"], user_id=None,
            stripe_customer_id="cus_dupe", stripe_subscription_id="sub_dupe",
            status="active", plan="org_seat_monthly", seats=1,
            collection_method="charge_automatically",
            current_period_end=now() + timedelta(days=30),
            cancel_at_period_end=False, trial_end=None)
    except psycopg.errors.UniqueViolation:
        return
    raise AssertionError("a second live subscription was allowed for one org")


# ── Lesson gating ───────────────────────────────────────────────────────────────

@check("lessons are free unless a manifest opts out")
def t_free_by_default():
    assert billing.lesson_is_free({}) is True, "a lesson with no flag was treated as paid"
    assert billing.lesson_is_free({"access": "free"}) is True
    assert billing.lesson_is_free({"access": "subscriber"}) is False


@check("access tiers resolve, and a typo fails open rather than shut")
def t_access_tiers():
    assert billing.lesson_access({}) == "free"
    assert billing.lesson_access({"access": "free"}) == "free"
    assert billing.lesson_access({"access": "subscriber"}) == "subscriber"

    # A misspelled tier must not silently lock a lesson: too-available is a
    # recoverable mistake, a locked classroom mid-term is not.
    assert billing.lesson_access({"access": "subscribers"}) == "free"
    assert billing.lesson_access({"access": ""}) == "free"


@check("the older \"free\": false spelling still works")
def t_access_back_compat():
    assert billing.lesson_access({"free": False}) == "subscriber"
    assert billing.lesson_access({"free": True}) == "free"
    assert billing.lesson_is_free({"free": False}) is False

    # An explicit tier wins over the legacy boolean.
    assert billing.lesson_access({"access": "free", "free": False}) == "free"


@check("a kit is normalised and never gates a lesson")
def t_kit_metadata():
    assert billing.lesson_kit({}) is None
    assert billing.lesson_kit({"kit": False}) is None

    bare = billing.lesson_kit({"kit": True})
    assert bare == {"name": "", "url": "", "note": ""}, bare

    full = billing.lesson_kit({"kit": {
        "name": "Breadboard Starter Kit",
        "url": "https://example.test/kit",
        "note": "Parts for the circuits track.",
    }})
    assert full["name"] == "Breadboard Starter Kit"
    assert full["url"] == "https://example.test/kit"

    # Malformed input is dropped, not raised on — a bad manifest should not
    # take the lesson menu down.
    assert billing.lesson_kit({"kit": "yes please"}) is None
    assert billing.lesson_kit({"kit": 3}) is None

    # The crucial property: having a kit changes nothing about access.
    kitted = {"kit": True}
    assert billing.lesson_is_free(kitted) is True, "a kit gated a free lesson"
    paid_with_kit = {"access": "subscriber", "kit": True}
    assert billing.lesson_access(paid_with_kit) == "subscriber"


@check("a kit shows on the menu and the lesson without blocking either")
def t_kit_rendered():
    clear_subscriptions()
    lesson = appmod.load_lessons()[0]
    original = dict(lesson)
    lesson["kit"] = {"name": "Breadboard Starter Kit",
                     "url": "https://example.test/kit", "note": ""}
    try:
        c = client()
        login(c, "alex")

        menu = c.get("/lessons")
        assert menu.status_code == 200
        assert "Kit" in menu.get_data(as_text=True), "no kit badge on the menu"

        page = c.get(f"/lesson/{lesson['id']}")
        assert page.status_code == 200, f"a kit blocked the lesson ({page.status_code})"
        body = page.get_data(as_text=True)
        assert "Breadboard Starter Kit" in body, "kit name missing from the lesson"
        assert "example.test/kit" in body, "kit link missing"
    finally:
        lesson.clear()
        lesson.update(original)


@check("a paid lesson is blocked in the page and in the API")
def t_paid_lesson_blocked():
    clear_subscriptions()
    lesson = appmod.load_lessons()[0]
    original = dict(lesson)
    lesson["access"] = "subscriber"
    try:
        c = client()
        login(c, "alex")

        res = c.get(f"/lesson/{lesson['id']}")
        assert res.status_code == 302 and "/locked" in res.headers["Location"], \
            f"page returned {res.status_code}"

        # The API is the real gate: the page can simply be skipped.
        res = c.post("/api/progress", json={"lesson_id": lesson["id"], "status": "completed"})
        assert res.status_code == 402, f"API allowed a paid lesson: {res.status_code}"

        res = c.post("/api/quiz", json={"lesson_id": lesson["id"],
                                        "question_id": "x", "chosen": 0})
        assert res.status_code == 402, f"quiz API allowed a paid lesson: {res.status_code}"
    finally:
        lesson.clear()
        lesson.update(original)


@check("a paid lesson opens once the school pays")
def t_paid_lesson_unlocked():
    lesson = appmod.load_lessons()[0]
    original = dict(lesson)
    lesson["access"] = "subscriber"
    try:
        clear_subscriptions()
        head = db.user_by_username("head")
        give_org_subscription(head["org_id"])

        c = client()
        login(c, "alex")
        assert c.get(f"/lesson/{lesson['id']}").status_code == 200, "still locked after paying"
    finally:
        lesson.clear()
        lesson.update(original)
        clear_subscriptions()


# ── Org administration ──────────────────────────────────────────────────────────

@check("approval-gated joins land pending and are held out of lessons")
def t_join_approval():
    head = db.user_by_username("head")
    db.set_join_policy(head["org_id"], "approval")
    code = join_code("head")

    signup(client(), "student", username="newkid", email="newkid@home.test",
           join_code=code, name="New Kid")
    newkid = db.user_by_username("newkid")
    assert newkid["membership_status"] == "pending", newkid["membership_status"]

    c = client()
    login(c, "newkid")
    res = c.get("/classroom")
    assert res.status_code == 302 and "/pending" in res.headers["Location"], \
        f"a pending student reached the classroom ({res.status_code})"
    assert c.get("/pending").status_code == 200

    # And they are not on anybody's roster yet.
    visible = {s["username"] for s in db.visible_students(head)}
    assert "newkid" not in visible, "a pending student appeared on the dashboard"


@check("an admin can approve a pending member")
def t_approve_member():
    head = db.user_by_username("head")
    newkid = db.user_by_username("newkid")

    c = client()
    login(c, "head")
    res = post(c, f"/org/members/{newkid['id']}/approve")
    assert res.status_code == 302, res.status_code

    assert db.user_by_username("newkid")["membership_status"] == "active"
    assert "newkid" in {s["username"] for s in db.visible_students(head)}

    student = client()
    login(student, "newkid")
    assert student.get("/classroom").status_code == 200, "still blocked after approval"


@check("a non-admin teacher cannot reach the org console")
def t_non_admin_blocked():
    c = client()
    login(c, "deputy")
    assert c.get("/org").status_code == 404, "a non-admin teacher saw the org console"

    newkid = db.user_by_username("newkid")
    res = post(c, f"/org/members/{newkid['id']}/remove", _from="/grownup")
    assert res.status_code == 404, f"a non-admin removed a member ({res.status_code})"
    assert db.user_by_username("newkid")["membership_status"] == "active"


@check("an admin cannot touch another org's roster")
def t_cross_org_admin():
    signup(client(), "teacher", username="rival", email="rival@other.test",
           org_name="Other School")
    rival = db.user_by_username("rival")
    signup(client(), "student", username="theirs", email="theirs@other.test",
           join_code=db.org_by_id(rival["org_id"])["join_code"], name="Their Kid")

    theirs = db.user_by_username("theirs")
    c = client()
    login(c, "head")
    res = post(c, f"/org/members/{theirs['id']}/remove")
    assert res.status_code == 404, f"reached another org's member ({res.status_code})"
    assert db.user_by_username("theirs")["membership_status"] == "active"


@check("the last admin cannot be removed or demoted")
def t_last_admin_protected():
    head = db.user_by_username("head")
    assert db.count_org_admins(head["org_id"]) == 1, "test expects a single admin"

    c = client()
    login(c, "head")
    # Removing yourself is refused outright.
    res = post(c, f"/org/members/{head['id']}/remove")
    assert res.status_code == 302
    assert db.user_by_username("head")["membership_status"] == "active"

    # Promote the deputy, then the first admin can step down.
    deputy = db.user_by_username("deputy")
    post(c, f"/org/members/{deputy['id']}/admin", admin="1")
    assert db.user_by_username("deputy")["org_admin"] is True, "promotion failed"
    assert db.count_org_admins(head["org_id"]) == 2

    res = post(c, f"/org/members/{head['id']}/admin", admin="0")
    assert res.status_code == 302
    assert db.user_by_username("head")["org_admin"] is False, "could not step down"


@check("only teachers can be made org admins")
def t_students_cannot_be_admin():
    alex = db.user_by_username("alex")
    deputy = db.user_by_username("deputy")

    c = client()
    login(c, "deputy")           # deputy is an admin from the previous check
    assert deputy["org_admin"] or db.user_by_username("deputy")["org_admin"]

    post(c, f"/org/members/{alex['id']}/admin", admin="1")
    assert db.user_by_username("alex")["org_admin"] is False, "a student was made an admin"


@check("removed members lose access and their sessions")
def t_removed_member():
    head = db.user_by_username("head")
    code = join_code("head")
    db.set_join_policy(head["org_id"], "open")
    signup(client(), "student", username="leaver", email="leaver@home.test",
           join_code=code, name="Leaver")

    session = client()
    login(session, "leaver")
    assert session.get("/classroom").status_code == 200

    leaver = db.user_by_username("leaver")
    admin = client()
    login(admin, "deputy")
    post(admin, f"/org/members/{leaver['id']}/remove")

    assert db.user_by_username("leaver") is None, "a removed member is still resolvable"
    assert session.get("/classroom").status_code == 302, "removed member kept their session"


@check("billable seats count only active students")
def t_seat_count():
    head = db.user_by_username("head")
    seats = db.count_billable_seats(head["org_id"])

    with db.query() as cur:
        cur.execute("SELECT count(*) AS n FROM users WHERE org_id = %s AND role = 'student' "
                    "AND is_active AND membership_status = 'active'", (head["org_id"],))
        expected = cur.fetchone()["n"]

    assert seats == expected, f"{seats} seats vs {expected} active students"
    # Teachers and parents are not billed.
    with db.query() as cur:
        cur.execute("SELECT count(*) AS n FROM users WHERE org_id = %s "
                    "AND role <> 'student'", (head["org_id"],))
        grownups = cur.fetchone()["n"]
    assert grownups > 0 and seats < expected + grownups, "grown-ups are being billed"


# ── Billing pages ───────────────────────────────────────────────────────────────

@check("only the payer sees a billing page")
def t_billing_access():
    student = client()
    login(student, "alex")
    assert student.get("/billing").status_code == 302, "a student reached billing"

    plain = client()
    login(plain, "head")     # demoted in t_last_admin_protected
    assert plain.get("/billing").status_code == 404, "a non-admin teacher reached billing"

    admin = client()
    login(admin, "deputy")
    assert admin.get("/billing").status_code == 200, "the admin could not reach billing"

    parent = client()
    login(parent, "dana")
    assert parent.get("/billing").status_code == 200, "a parent could not reach billing"


@check("requesting net-30 records the request but grants nothing")
def t_invoice_request():
    c = client()
    login(c, "deputy")
    page = c.get("/billing").get_data(as_text=True)
    res = c.post("/billing/invoice-request", data={
        "csrf_token": token_from(page),
        "billing_email": "accounts@school.test",
        "po_number": "PO-2026-114",
        "tax_exempt": "1",
    }, follow_redirects=False)
    assert res.status_code == 302, res.status_code

    deputy = db.user_by_username("deputy")
    org = db.org_by_id(deputy["org_id"])
    assert org["invoice_requested_at"] is not None, "request not recorded"
    assert org["billing_email"] == "accounts@school.test"
    assert org["po_number"] == "PO-2026-114"
    assert org["tax_exempt"] is True
    # The crucial half: asking is not being granted.
    assert org["invoice_approved_at"] is None, "requesting net-30 granted it"
    assert org["billing_terms"] == "card", "terms changed without approval"

    assert org["id"] in {o["id"] for o in db.orgs_awaiting_invoice_approval()}


@check("approving net-30 is what changes the terms")
def t_invoice_approval():
    deputy = db.user_by_username("deputy")
    assert db.approve_invoice_terms(deputy["org_id"]) is True

    org = db.org_by_id(deputy["org_id"])
    assert org["billing_terms"] == "invoice", org["billing_terms"]
    assert org["invoice_approved_at"] is not None
    assert org["id"] not in {o["id"] for o in db.orgs_awaiting_invoice_approval()}


# ── Webhooks ────────────────────────────────────────────────────────────────────

def subscription_payload(org_id, status="active", sub_id="sub_hook_1", quantity=3):
    """The shape Stripe actually sends, trimmed to what we read."""
    return {
        "id": sub_id,
        "object": "subscription",
        "customer": "cus_hook",
        "status": status,
        "collection_method": "charge_automatically",
        "cancel_at_period_end": False,
        "current_period_end": int((now() + timedelta(days=30)).timestamp()),
        "trial_end": None,
        "metadata": {"account_kind": "org", "org_id": str(org_id)},
        "items": {"data": [{
            "id": "si_1", "quantity": quantity,
            "price": {"id": "price_1", "lookup_key": "org_seat_monthly"},
        }]},
    }


def event(event_type, obj, event_id="evt_1"):
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


@check("a subscription webhook is recorded")
def t_webhook_records():
    clear_subscriptions()
    head = db.user_by_username("head")

    payload = subscription_payload(head["org_id"])
    assert db.claim_event("evt_sub_1", "customer.subscription.created") is True
    billing.handle_event(appmod.cfg, event("customer.subscription.created",
                                           payload, "evt_sub_1"))
    db.finish_event("evt_sub_1")

    stored = db.subscription_for_org(head["org_id"])
    assert stored is not None, "webhook did not create the subscription"
    assert stored["status"] == "active"
    assert stored["seats"] == 3, stored["seats"]
    assert stored["plan"] == "org_seat_monthly"
    assert billing.entitlement_for(appmod.cfg, db.user_by_username("alex"))["active"]


@check("a replayed webhook is ignored")
def t_webhook_idempotent():
    """Stripe retries on any non-2xx and can deliver the same event twice."""
    assert db.claim_event("evt_sub_1", "customer.subscription.created") is False, \
        "the same event was claimed twice"

    with db.query() as cur:
        cur.execute("SELECT count(*) AS n FROM stripe_events WHERE event_id = 'evt_sub_1'")
        assert cur.fetchone()["n"] == 1


@check("an out-of-order webhook converges rather than duplicating")
def t_webhook_out_of_order():
    head = db.user_by_username("head")
    before = db.subscription_for_org(head["org_id"])

    payload = subscription_payload(head["org_id"], status="past_due")
    db.claim_event("evt_sub_2", "customer.subscription.updated")
    billing.handle_event(appmod.cfg, event("customer.subscription.updated",
                                           payload, "evt_sub_2"))
    db.finish_event("evt_sub_2")

    after = db.subscription_for_org(head["org_id"])
    assert after["id"] == before["id"], "the update created a second row"
    assert after["status"] == "past_due", after["status"]


@check("an unsigned webhook is rejected")
def t_webhook_signature():
    c = client()
    res = c.post("/stripe/webhook",
                 data=b'{"id":"evt_forged","type":"customer.subscription.created"}',
                 content_type="application/json")
    assert res.status_code == 400, f"an unsigned webhook returned {res.status_code}"

    res = c.post("/stripe/webhook",
                 data=b'{"id":"evt_forged","type":"customer.subscription.created"}',
                 content_type="application/json",
                 headers={"Stripe-Signature": "t=1,v1=deadbeef"})
    assert res.status_code == 400, f"a bogus signature returned {res.status_code}"

    with db.query() as cur:
        cur.execute("SELECT count(*) AS n FROM stripe_events WHERE event_id = 'evt_forged'")
        assert cur.fetchone()["n"] == 0, "a forged event was recorded"


@check("a correctly signed webhook is accepted end to end")
def t_webhook_signed():
    """
    Signs a payload the way Stripe does and posts it at the real endpoint,
    so the route, the signature check and the handler are all exercised.
    """
    import hashlib
    import hmac as hmac_mod
    import json
    import time

    head = db.user_by_username("head")
    payload = json.dumps(event("customer.subscription.updated",
                               subscription_payload(head["org_id"], status="active",
                                                    quantity=7),
                               "evt_signed_1")).encode()

    timestamp = int(time.time())
    secret = appmod.cfg.STRIPE_WEBHOOK_SECRET
    signature = hmac_mod.new(secret.encode(),
                             f"{timestamp}.".encode() + payload,
                             hashlib.sha256).hexdigest()

    res = client().post("/stripe/webhook", data=payload,
                        content_type="application/json",
                        headers={"Stripe-Signature": f"t={timestamp},v1={signature}"})
    assert res.status_code == 200, f"{res.status_code}: {res.get_data(as_text=True)[:200]}"
    assert db.subscription_for_org(head["org_id"])["seats"] == 7, "handler did not run"

    # And the replay of that same event is a no-op, not a second apply.
    res = client().post("/stripe/webhook", data=payload,
                        content_type="application/json",
                        headers={"Stripe-Signature": f"t={timestamp},v1={signature}"})
    assert res.get_json().get("duplicate") is True, res.get_json()


@check("an unhandled event type is acknowledged, not retried")
def t_webhook_unknown_event():
    import hashlib
    import hmac as hmac_mod
    import json
    import time

    payload = json.dumps(event("customer.discount.created", {"id": "di_1"},
                               "evt_unknown")).encode()
    timestamp = int(time.time())
    signature = hmac_mod.new(appmod.cfg.STRIPE_WEBHOOK_SECRET.encode(),
                             f"{timestamp}.".encode() + payload,
                             hashlib.sha256).hexdigest()

    res = client().post("/stripe/webhook", data=payload,
                        content_type="application/json",
                        headers={"Stripe-Signature": f"t={timestamp},v1={signature}"})
    # A non-2xx here would have Stripe retry forever and eventually disable
    # the endpoint.
    assert res.status_code == 200, res.status_code
    assert res.get_json().get("ignored") == "customer.discount.created"


@check("a failed handler releases its claim so the retry can work")
def t_webhook_retry_after_failure():
    db.claim_event("evt_transient", "invoice.paid")
    db.release_event("evt_transient")
    assert db.claim_event("evt_transient", "invoice.paid") is True, \
        "a transient failure permanently swallowed the event"


@check("invoices are recorded against their subscription")
def t_invoice_recorded():
    head = db.user_by_username("head")
    subscription = db.subscription_for_org(head["org_id"])

    billing.record_invoice({
        "id": "in_test_1",
        "number": "IGN-0001",
        "status": "open",
        "amount_due": 24000,
        "amount_paid": 0,
        "currency": "usd",
        "due_date": int((now() + timedelta(days=30)).timestamp()),
        "hosted_invoice_url": "https://invoice.stripe.test/1",
        "invoice_pdf": "https://invoice.stripe.test/1.pdf",
        "subscription": subscription["stripe_subscription_id"],
    })

    rows = db.invoices_for(subscription["id"])
    assert len(rows) == 1, rows
    assert rows[0]["number"] == "IGN-0001"
    assert rows[0]["amount_due"] == 24000

    # An overdue one shows up for chasing.
    billing.record_invoice({
        "id": "in_test_2", "number": "IGN-0002", "status": "open",
        "amount_due": 12000, "amount_paid": 0, "currency": "usd",
        "due_date": int((now() - timedelta(days=5)).timestamp()),
        "hosted_invoice_url": None, "invoice_pdf": None,
        "subscription": subscription["stripe_subscription_id"],
    })
    assert "in_test_2" in {i["stripe_invoice_id"] for i in db.overdue_invoices()}


# ── Rendering ───────────────────────────────────────────────────────────────────

@check("every new page renders")
def t_pages_render():
    broken = []

    def visit(c, path, expect=200):
        res = c.get(path)
        if res.status_code != expect:
            broken.append((path, res.status_code, expect))

    admin = client()
    login(admin, "deputy")
    visit(admin, "/org")
    visit(admin, "/billing")
    visit(admin, "/billing/return")

    parent = client()
    login(parent, "dana")
    visit(parent, "/billing")

    student = client()
    login(student, "alex")
    visit(student, "/locked", 402)
    visit(student, "/lessons")

    assert not broken, f"pages did not render: {broken}"


TESTS = [
    t_no_subscription, t_org_covers_students, t_parent_covers_own_child,
    t_card_grace, t_invoice_grace, t_comp, t_one_live_subscription,
    t_free_by_default, t_access_tiers, t_access_back_compat,
    t_kit_metadata, t_kit_rendered,
    t_paid_lesson_blocked, t_paid_lesson_unlocked,
    t_join_approval, t_approve_member, t_non_admin_blocked, t_cross_org_admin,
    t_last_admin_protected, t_students_cannot_be_admin, t_removed_member,
    t_seat_count,
    t_billing_access, t_invoice_request, t_invoice_approval,
    t_webhook_records, t_webhook_idempotent, t_webhook_out_of_order,
    t_webhook_signature, t_webhook_signed, t_webhook_unknown_event,
    t_webhook_retry_after_failure, t_invoice_recorded,
    t_pages_render,
]


def main() -> int:
    appmod.db.init_pool(appmod.cfg)
    reset_database()
    appmod.refresh_catalog()
    build_world()

    print(f"\n  {len(TESTS)} billing checks\n")
    for test in TESTS:
        test()

    print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
