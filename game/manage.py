#!/usr/bin/env python3
"""
manage.py — operator tasks that have no business being on the web.

    python manage.py orgs
    python manage.py invoice-requests
    python manage.py approve-invoice 3
    python manage.py start-invoice-subscription 3
    python manage.py overdue
    python manage.py comp --org 3 --days 90
    python manage.py deactivate alex
    python manage.py make-admin ms_chen
    python manage.py sync-seats
    python manage.py purge

Two of these are deliberately not self-service:

  approve-invoice   Net 30 is unsecured credit. A school district is worth
                    extending it to; an anonymous signup is not. A person
                    decides, having checked the org is who it says it is.

  comp              Free access, for pilots and for schools whose purchase
                    order is still crawling through procurement.

Everything here needs DATABASE_URL, and the Stripe commands need
STRIPE_SECRET_KEY.
"""

import argparse
import sys
from datetime import timedelta

import billing
import db
from config import validate as load_config
from logsetup import configure_logging


def money(cents: int, currency: str = "usd") -> str:
    return f"{cents / 100:,.2f} {currency.upper()}"


# ── Reporting ───────────────────────────────────────────────────────────────────

def cmd_orgs(cfg, args) -> int:
    with db.query() as cur:
        cur.execute("""
            SELECT o.id, o.name, o.join_code, o.join_policy, o.billing_terms,
                   o.invoice_approved_at,
                   (SELECT count(*) FROM users u WHERE u.org_id = o.id
                     AND u.role = 'student' AND u.is_active
                     AND u.membership_status = 'active') AS students,
                   (SELECT count(*) FROM users u WHERE u.org_id = o.id
                     AND u.membership_status = 'pending') AS pending,
                   (SELECT s.status FROM subscriptions s WHERE s.org_id = o.id
                     ORDER BY s.id DESC LIMIT 1) AS sub_status
            FROM orgs o ORDER BY o.id
        """)
        rows = cur.fetchall()

    if not rows:
        print("No organisations yet.")
        return 0

    print(f"{'id':>4}  {'name':28} {'code':9} {'policy':9} {'terms':8} "
          f"{'students':>8} {'pending':>7}  subscription")
    print("-" * 100)
    for r in rows:
        terms = r["billing_terms"] + ("*" if r["invoice_approved_at"] else "")
        print(f"{r['id']:>4}  {r['name'][:28]:28} {r['join_code']:9} {r['join_policy']:9} "
              f"{terms:8} {r['students']:>8} {r['pending']:>7}  {r['sub_status'] or '—'}")
    print("\n* invoice terms approved")
    return 0


def cmd_invoice_requests(cfg, args) -> int:
    rows = db.orgs_awaiting_invoice_approval()
    if not rows:
        print("Nothing waiting for invoice approval.")
        return 0

    for r in rows:
        seats = db.count_billable_seats(r["id"])
        print(f"\n  org {r['id']}: {r['name']}")
        print(f"    requested   {r['invoice_requested_at']:%Y-%m-%d %H:%M}")
        print(f"    billing to  {r['billing_email'] or '—'}")
        print(f"    PO          {r['po_number'] or '—'}")
        print(f"    tax exempt  {'yes' if r['tax_exempt'] else 'no'}")
        print(f"    seats       {seats}")
        print(f"    approve:    python manage.py approve-invoice {r['id']}")
    print()
    return 0


def cmd_overdue(cfg, args) -> int:
    rows = db.overdue_invoices()
    if not rows:
        print("No overdue invoices.")
        return 0

    print(f"{'invoice':16} {'org':26} {'amount':>12}  due")
    print("-" * 76)
    for r in rows:
        print(f"{r['number'] or r['stripe_invoice_id'][:16]:16} "
              f"{(r['org_name'] or '—')[:26]:26} "
              f"{money(r['amount_due'], r['currency']):>12}  "
              f"{r['due_date']:%Y-%m-%d}"
              + (f"  PO {r['po_number']}" if r["po_number"] else ""))
    print(f"\n{len(rows)} overdue. Chase the billing contact before cutting access — "
          f"the grace window is {cfg.GRACE_DAYS_INVOICE} days.")
    return 0


# ── Billing actions ─────────────────────────────────────────────────────────────

def cmd_approve_invoice(cfg, args) -> int:
    org = db.org_by_id(args.org_id)
    if not org:
        print(f"No org with id {args.org_id}.", file=sys.stderr)
        return 1

    if not db.approve_invoice_terms(org["id"]):
        print("Could not approve.", file=sys.stderr)
        return 1

    print(f"  {org['name']} approved for invoice billing, net {cfg.INVOICE_DUE_DAYS}.")
    print("  Start the subscription with:")
    print(f"    python manage.py start-invoice-subscription {org['id']}")
    return 0


def cmd_start_invoice_subscription(cfg, args) -> int:
    """
    Create the Stripe subscription that bills by invoice.

    Separate from approve-invoice on purpose: approving the terms and
    starting the clock are different decisions, and a school often wants
    the second to line up with the start of a term.
    """
    org = db.org_by_id(args.org_id)
    if not org:
        print(f"No org with id {args.org_id}.", file=sys.stderr)
        return 1
    if not org["invoice_approved_at"]:
        print(f"{org['name']} is not approved for invoice terms. "
              f"Run:  python manage.py approve-invoice {org['id']}", file=sys.stderr)
        return 1
    if not billing.enabled(cfg):
        print("Stripe is not configured (STRIPE_SECRET_KEY).", file=sys.stderr)
        return 1

    existing = db.subscription_for_org(org["id"])
    if existing and existing.get("stripe_subscription_id"):
        print(f"{org['name']} already has subscription "
              f"{existing['stripe_subscription_id']} ({existing['status']}).", file=sys.stderr)
        return 1

    seats = args.seats or db.count_billable_seats(org["id"])
    if seats < 1:
        print("That org has no active students, so there is nothing to bill for.",
              file=sys.stderr)
        return 1

    metadata = {"account_kind": "org", "org_id": org["id"], "ref": f"org:{org['id']}"}
    customer_id = billing.ensure_customer(
        cfg,
        existing_id=existing["stripe_customer_id"] if existing else None,
        email=org["billing_email"],
        name=org["name"],
        metadata=metadata,
    )

    subscription = billing.create_invoice_subscription(
        cfg,
        customer_id=customer_id,
        price_lookup_key=cfg.PRICE_ORG_SEAT,
        quantity=seats,
        metadata=metadata,
        po_number=org["po_number"],
    )
    billing.record_subscription(subscription)

    print(f"  {org['name']}: subscription {subscription['id']} created")
    print(f"    {seats} seat(s), net {cfg.INVOICE_DUE_DAYS}, invoices to "
          f"{org['billing_email'] or 'the Stripe customer email'}")
    return 0


def cmd_comp(cfg, args) -> int:
    if bool(args.org) == bool(args.user):
        print("Give exactly one of --org or --user.", file=sys.stderr)
        return 1

    until = billing.now() + timedelta(days=args.days)
    user_id = None

    if args.user:
        user = db.user_by_username(args.user)
        if not user:
            print(f"No user {args.user!r}.", file=sys.stderr)
            return 1
        if user["role"] != "parent":
            print("Comp a parent account or an org — a student's access comes "
                  "from one of those.", file=sys.stderr)
            return 1
        user_id = user["id"]
        who = f"{user['name']} ({user['username']})"
    else:
        org = db.org_by_id(args.org)
        if not org:
            print(f"No org with id {args.org}.", file=sys.stderr)
            return 1
        who = org["name"]

    db.set_comp_until(org_id=args.org, user_id=user_id, until=until)
    print(f"  {who}: complimentary access until {until:%Y-%m-%d}.")
    return 0


def cmd_sync_seats(cfg, args) -> int:
    """
    Reconcile Stripe quantities with the actual rosters.

    Seat updates during approval and removal are best-effort — a Stripe
    outage must not stop a teacher letting a student in — so something has
    to catch what those calls dropped. Run it nightly.
    """
    if not billing.enabled(cfg):
        print("Stripe is not configured.", file=sys.stderr)
        return 1

    with db.query() as cur:
        cur.execute("SELECT id, org_id, stripe_subscription_id, seats FROM subscriptions "
                    "WHERE org_id IS NOT NULL AND stripe_subscription_id IS NOT NULL "
                    "AND status NOT IN ('canceled','incomplete_expired')")
        rows = cur.fetchall()

    changed = 0
    for row in rows:
        actual = db.count_billable_seats(row["org_id"])
        if actual == row["seats"]:
            continue
        if args.dry_run:
            print(f"  org {row['org_id']}: {row['seats']} → {actual} (dry run)")
            changed += 1
            continue
        try:
            billing.update_seats(cfg,
                                 stripe_subscription_id=row["stripe_subscription_id"],
                                 quantity=actual)
            print(f"  org {row['org_id']}: {row['seats']} → {actual}")
            changed += 1
        except Exception as exc:
            print(f"  org {row['org_id']}: FAILED ({exc})", file=sys.stderr)

    print(f"\n{changed} subscription(s) {'would be ' if args.dry_run else ''}resized "
          f"out of {len(rows)}.")
    return 0


# ── Account actions ─────────────────────────────────────────────────────────────

def cmd_deactivate(cfg, args) -> int:
    user = db.user_by_username(args.username)
    if not user:
        print(f"No user {args.username!r}.", file=sys.stderr)
        return 1

    with db.write() as cur:
        # Bumping the epoch as well as clearing the flag ends any session
        # they already have, rather than letting a live cookie run on.
        cur.execute("UPDATE users SET is_active = false, "
                    "session_epoch = session_epoch + 1 WHERE id = %s", (user["id"],))
    print(f"  {user['name']} ({user['username']}) deactivated and signed out.")
    print("  Their work is kept. Delete the row to remove it entirely — "
          "everything cascades.")
    return 0


def cmd_make_admin(cfg, args) -> int:
    user = db.user_by_username(args.username)
    if not user:
        print(f"No user {args.username!r}.", file=sys.stderr)
        return 1
    if not db.set_org_admin(user["id"], user["org_id"], True):
        print("Only teacher accounts can be org admins.", file=sys.stderr)
        return 1
    print(f"  {user['name']} is now an admin of org {user['org_id']}.")
    return 0


def cmd_purge(cfg, args) -> int:
    tokens = db.purge_expired_tokens()
    events = db.purge_stripe_events()
    rates = db.purge_rate_events(cfg.RL_WINDOW)
    print(f"  expired tokens removed: {tokens}")
    print(f"  old webhook events removed: {events}")
    print(f"  old rate-limit events removed: {rates}")
    return 0


# ── Entry point ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("orgs", help="List organisations.")
    sub.add_parser("invoice-requests", help="Orgs waiting for invoice terms.")
    sub.add_parser("overdue", help="Open invoices past their due date.")
    sub.add_parser("purge", help="Delete expired tokens and old event rows.")

    p = sub.add_parser("approve-invoice", help="Grant net-30 terms to an org.")
    p.add_argument("org_id", type=int)

    p = sub.add_parser("start-invoice-subscription",
                       help="Create the invoice-billed Stripe subscription.")
    p.add_argument("org_id", type=int)
    p.add_argument("--seats", type=int, help="Override the seat count.")

    p = sub.add_parser("comp", help="Grant free access for a period.")
    p.add_argument("--org", type=int, help="Org id.")
    p.add_argument("--user", help="Parent username.")
    p.add_argument("--days", type=int, default=90)

    p = sub.add_parser("sync-seats", help="Reconcile Stripe seat counts with rosters.")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("deactivate", help="Disable an account and end its sessions.")
    p.add_argument("username")

    p = sub.add_parser("make-admin", help="Make a teacher an org admin.")
    p.add_argument("username")

    args = parser.parse_args()

    cfg = load_config()
    configure_logging(cfg)
    db.init_pool(cfg)

    handlers = {
        "orgs": cmd_orgs,
        "invoice-requests": cmd_invoice_requests,
        "overdue": cmd_overdue,
        "approve-invoice": cmd_approve_invoice,
        "start-invoice-subscription": cmd_start_invoice_subscription,
        "comp": cmd_comp,
        "sync-seats": cmd_sync_seats,
        "deactivate": cmd_deactivate,
        "make-admin": cmd_make_admin,
        "purge": cmd_purge,
    }
    try:
        return handlers[args.command](cfg, args)
    finally:
        db.close_pool()


if __name__ == "__main__":
    sys.exit(main())
