#!/usr/bin/env python3
"""
billing.py — Stripe, and the question "is this account paid up?".

CARD DATA NEVER REACHES THIS SERVER.  Both places a card gets typed —
Checkout and the Customer Portal — are pages on Stripe's own domain.  We
hold customer and subscription ids and nothing else, which keeps this
application in PCI SAQ A rather than SAQ D.

Two ways to pay, because two very different customers:

    charge_automatically   a parent's card, charged on renewal
    send_invoice           a school's purchase order, net 30

The second is not a variation on the first.  A district cannot put a
classroom on a personal card; it raises a PO, someone approves it, and a
cheque or ACH arrives weeks later.  Refusing that is refusing the sale.

ENTITLEMENT IS DECIDED HERE AND NOWHERE ELSE.  entitlement_for() is the
one function that answers whether an account has access, so there is one
place to look when someone is locked out who should not be.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import db

log = logging.getLogger("ignite.billing")

# Stripe subscription statuses that mean "paid up right now".
LIVE_STATUSES = frozenset({"active", "trialing"})
# Owed but not yet abandoned. These get a grace window rather than an
# instant cut-off — see entitlement_for().
GRACE_STATUSES = frozenset({"past_due", "unpaid"})


class BillingUnavailable(RuntimeError):
    """Raised when a billing action is attempted with Stripe unconfigured."""


def _stripe(cfg):
    if not cfg.STRIPE_SECRET_KEY:
        raise BillingUnavailable(
            "Stripe is not configured. Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET.")
    import stripe
    stripe.api_key = cfg.STRIPE_SECRET_KEY
    return stripe


def enabled(cfg) -> bool:
    """
    With no Stripe key the app runs with everything open.

    That is deliberate: local development, a free pilot and the test suite
    should not need a payment provider, and a half-configured Stripe is
    worse than none.
    """
    return bool(cfg.STRIPE_SECRET_KEY)


def now() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(obj):
    """
    Normalise a Stripe object into a plain dict.

    The SDK returns StripeObject, which deliberately raises on .get() to
    stop exactly the dict-shaped assumption the rest of this module makes.
    Converting once, here at the boundary, means everything downstream can
    treat an event object and a hand-built test payload identically.
    """
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj


def _ts(value) -> datetime | None:
    """Stripe sends unix seconds; the database wants an aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


# ── Entitlement ─────────────────────────────────────────────────────────────────

def _grace_days(cfg, subscription: dict) -> int:
    if subscription.get("collection_method") == "send_invoice":
        return cfg.GRACE_DAYS_INVOICE
    return cfg.GRACE_DAYS_CARD


def _evaluate(cfg, subscription: dict | None, source: str) -> dict | None:
    """Turn one subscription row into an entitlement, or None if it gives none."""
    if not subscription:
        return None

    comp_until = subscription.get("comp_until")
    if comp_until and comp_until > now():
        return {"active": True, "source": source, "status": "comped",
                "until": comp_until, "in_grace": False,
                "collection_method": subscription.get("collection_method")}

    status = subscription.get("status")

    if status in LIVE_STATUSES:
        return {"active": True, "source": source, "status": status,
                "until": subscription.get("current_period_end"), "in_grace": False,
                "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
                "collection_method": subscription.get("collection_method")}

    if status in GRACE_STATUSES:
        # Owed, not gone. The window runs from the end of the period that
        # was not paid for, so a school on net 30 does not lose access the
        # morning after an invoice is issued.
        period_end = subscription.get("current_period_end")
        deadline = (period_end or now()) + timedelta(days=_grace_days(cfg, subscription))
        if deadline > now():
            return {"active": True, "source": source, "status": status,
                    "until": deadline, "in_grace": True,
                    "collection_method": subscription.get("collection_method")}
        return {"active": False, "source": source, "status": status,
                "until": deadline, "in_grace": False,
                "collection_method": subscription.get("collection_method")}

    return {"active": False, "source": source, "status": status or "none",
            "until": subscription.get("current_period_end"), "in_grace": False,
            "collection_method": subscription.get("collection_method")}


NO_ENTITLEMENT = {"active": False, "source": "none", "status": "none",
                  "until": None, "in_grace": False, "collection_method": None}


def entitlement_for(cfg, user: dict) -> dict:
    """
    Does this account have paid access, and because of whom?

    A student is covered if their school pays *or* any one linked parent
    does — the school and the family should never both have to buy, and
    whichever exists first wins. Teachers and parents are covered by their
    own org or subscription respectively.
    """
    if not enabled(cfg):
        return {"active": True, "source": "billing_disabled", "status": "open",
                "until": None, "in_grace": False, "collection_method": None}

    role = user["role"]

    if role == "student":
        best = _evaluate(cfg, db.subscription_for_org(user["org_id"]), "org")
        if best and best["active"]:
            return best
        for parent_sub in db.subscriptions_for_parents_of(user["id"]):
            result = _evaluate(cfg, parent_sub, "parent")
            if result and result["active"]:
                return result
        return best or NO_ENTITLEMENT

    if role == "parent":
        own = _evaluate(cfg, db.subscription_for_parent(user["id"]), "parent")
        if own and own["active"]:
            return own
        org = _evaluate(cfg, db.subscription_for_org(user["org_id"]), "org")
        if org and org["active"]:
            return org
        return own or org or NO_ENTITLEMENT

    # Teachers ride on the org. A teacher is never billed personally: they
    # are the person who buys, not the thing bought.
    return _evaluate(cfg, db.subscription_for_org(user["org_id"]), "org") or NO_ENTITLEMENT


def lesson_is_free(lesson: dict) -> bool:
    """
    Lessons are free unless a manifest opts out with "free": false.

    Defaulting the other way would have silently locked every existing
    lesson the moment a Stripe key appeared in the environment.
    """
    return lesson.get("free", True) is not False


# ── Customers ───────────────────────────────────────────────────────────────────

def ensure_customer(cfg, *, existing_id: str | None, email: str | None,
                    name: str, metadata: dict) -> str:
    """
    Reuse the Stripe customer we already have, or make one.

    Reusing matters: a second customer for the same payer splits their
    invoice history in two and makes the Customer Portal show them half
    their own account.
    """
    stripe = _stripe(cfg)
    if existing_id and existing_id != "comp":
        try:
            customer = stripe.Customer.retrieve(existing_id)
            if not getattr(customer, "deleted", False):
                return existing_id
        except Exception:
            log.warning("stripe customer %s could not be retrieved; making a new one",
                        existing_id)

    customer = stripe.Customer.create(
        email=email or None,
        name=name,
        metadata={k: str(v) for k, v in metadata.items()},
    )
    return customer.id


# ── Checkout (card) ─────────────────────────────────────────────────────────────

def checkout_session(cfg, *, customer_id: str, price_lookup_key: str,
                     quantity: int, success_url: str, cancel_url: str,
                     metadata: dict, trial_days: int | None = None) -> str:
    """
    A hosted Checkout session; returns the URL to send the browser to.

    Prices are resolved by lookup key rather than hardcoded price id, so
    changing what you charge is a Stripe dashboard change and not a deploy.
    """
    stripe = _stripe(cfg)

    prices = stripe.Price.list(lookup_keys=[price_lookup_key], active=True, limit=1)
    if not prices.data:
        raise BillingUnavailable(
            f"No active Stripe price with lookup key {price_lookup_key!r}. "
            "Create it in the Stripe dashboard.")

    subscription_data: dict = {"metadata": {k: str(v) for k, v in metadata.items()}}
    if trial_days:
        subscription_data["trial_period_days"] = trial_days

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": prices.data[0].id, "quantity": max(1, quantity)}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(metadata.get("ref", "")),
        subscription_data=subscription_data,
        metadata={k: str(v) for k, v in metadata.items()},
        allow_promotion_codes=True,
    )
    return session.url


def portal_session(cfg, *, customer_id: str, return_url: str) -> str:
    """
    Stripe's own account-management page: change card, cancel, download
    invoices. Hosted, so none of that is UI we build or card data we touch.
    """
    stripe = _stripe(cfg)
    session = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=return_url)
    return session.url


# ── Invoice subscriptions (net 30) ──────────────────────────────────────────────

def create_invoice_subscription(cfg, *, customer_id: str, price_lookup_key: str,
                                quantity: int, metadata: dict,
                                po_number: str | None = None):
    """
    A subscription billed by invoice on terms, with no card involved.

    Stripe emails the invoice and the school pays it by ACH, cheque or
    card at their end. days_until_due is the "net 30" — Stripe marks the
    invoice open until it is paid, and we keep serving through the grace
    window in entitlement_for().
    """
    stripe = _stripe(cfg)

    prices = stripe.Price.list(lookup_keys=[price_lookup_key], active=True, limit=1)
    if not prices.data:
        raise BillingUnavailable(
            f"No active Stripe price with lookup key {price_lookup_key!r}.")

    description = f"Ignite Academy — {quantity} seat(s)"
    if po_number:
        description += f" — PO {po_number}"

    return stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": prices.data[0].id, "quantity": max(1, quantity)}],
        collection_method="send_invoice",
        days_until_due=cfg.INVOICE_DUE_DAYS,
        description=description,
        metadata={k: str(v) for k, v in metadata.items()},
    )


def update_seats(cfg, *, stripe_subscription_id: str, quantity: int) -> None:
    """
    Resize a seat-based subscription when the roster changes.

    proration_behavior is left at Stripe's default so a mid-term addition
    is prorated rather than silently free until renewal.
    """
    stripe = _stripe(cfg)
    subscription = stripe.Subscription.retrieve(stripe_subscription_id)
    if not subscription.get("items", {}).get("data"):
        return
    item = subscription["items"]["data"][0]
    if item.get("quantity") == quantity:
        return
    stripe.Subscription.modify(
        stripe_subscription_id,
        items=[{"id": item["id"], "quantity": max(1, quantity)}],
    )


# ── Webhooks ────────────────────────────────────────────────────────────────────

def verify_webhook(cfg, payload: bytes, signature: str | None):
    """
    Verify a webhook against the signing secret.

    This signature IS the authentication for that endpoint — it is
    unauthenticated otherwise, and anyone who found the URL could POST
    themselves a subscription. It must run against the exact raw body, so
    the caller has to hand over bytes that nothing has re-encoded.
    """
    stripe = _stripe(cfg)
    if not cfg.STRIPE_WEBHOOK_SECRET:
        raise BillingUnavailable("STRIPE_WEBHOOK_SECRET is not set.")
    return stripe.Webhook.construct_event(
        payload, signature, cfg.STRIPE_WEBHOOK_SECRET)


def _subscription_fields(subscription) -> dict:
    """Pull the handful of fields worth storing out of a Stripe subscription."""
    subscription = _as_dict(subscription)
    items = _as_dict(subscription.get("items") or {}).get("data") or [{}]
    first = _as_dict(items[0]) if items else {}
    price = _as_dict(first.get("price") or {})

    # current_period_end moved onto the item in recent API versions; read
    # whichever this account's version provides.
    period_end = subscription.get("current_period_end") or first.get("current_period_end")

    return {
        "status":               subscription.get("status", "incomplete"),
        "plan":                 price.get("lookup_key") or price.get("nickname") or price.get("id"),
        "seats":                first.get("quantity") or 1,
        "collection_method":    subscription.get("collection_method", "charge_automatically"),
        "current_period_end":   _ts(period_end),
        "cancel_at_period_end": bool(subscription.get("cancel_at_period_end")),
        "trial_end":            _ts(subscription.get("trial_end")),
        "stripe_customer_id":   subscription.get("customer"),
    }


def record_subscription(subscription) -> dict | None:
    """
    Persist a Stripe subscription against the account named in its metadata.

    The metadata carries account_kind and the org or user id, written when
    the subscription was created. Falling back to the customer id covers a
    subscription created by hand in the Stripe dashboard.
    """
    subscription = _as_dict(subscription)
    metadata = _as_dict(subscription.get("metadata") or {})
    fields = _subscription_fields(subscription)

    account_kind = metadata.get("account_kind")
    org_id = metadata.get("org_id")
    user_id = metadata.get("user_id")

    if not account_kind:
        known = db.subscription_by_customer(fields["stripe_customer_id"] or "")
        if not known:
            log.warning("subscription %s has no account metadata and no known customer",
                        subscription.get("id"))
            return None
        account_kind = known["account_kind"]
        org_id, user_id = known["org_id"], known["user_id"]

    return db.upsert_subscription(
        account_kind=account_kind,
        org_id=int(org_id) if org_id else None,
        user_id=int(user_id) if user_id else None,
        stripe_subscription_id=subscription.get("id"),
        **fields,
    )


def record_invoice(invoice) -> None:
    invoice = _as_dict(invoice)
    subscription_id = None
    stripe_sub_id = invoice.get("subscription")
    if isinstance(stripe_sub_id, dict):
        stripe_sub_id = stripe_sub_id.get("id")
    if stripe_sub_id:
        known = db.subscription_by_stripe_id(stripe_sub_id)
        if known:
            subscription_id = known["id"]

    db.upsert_invoice(
        stripe_invoice_id=invoice["id"],
        subscription_id=subscription_id,
        number=invoice.get("number"),
        status=invoice.get("status", "draft"),
        amount_due=invoice.get("amount_due", 0),
        amount_paid=invoice.get("amount_paid", 0),
        currency=invoice.get("currency", "usd"),
        due_date=_ts(invoice.get("due_date")),
        hosted_invoice_url=invoice.get("hosted_invoice_url"),
        pdf_url=invoice.get("invoice_pdf"),
    )


# Events worth acting on. Anything else is acknowledged and ignored —
# returning a non-2xx for an event we simply do not care about would make
# Stripe retry it forever and eventually disable the endpoint.
HANDLED_EVENTS = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
    "invoice.finalized",
    "invoice.marked_uncollectible",
}


def handle_event(cfg, event) -> str:
    """
    Apply one verified webhook event. Returns a short description for the log.

    Callers must have claimed the event id first (db.claim_event) — Stripe
    retries, and delivers out of order.
    """
    event_type = event["type"]
    obj = _as_dict(event["data"]["object"])

    if event_type == "checkout.session.completed":
        # The session only tells us a subscription now exists; the
        # subscription object itself is the source of truth for its state,
        # so fetch it rather than inferring from the session.
        stripe_sub_id = obj.get("subscription")
        if not stripe_sub_id:
            return "checkout completed with no subscription"
        stripe = _stripe(cfg)
        subscription = stripe.Subscription.retrieve(stripe_sub_id)
        # Checkout puts our metadata on the session; make sure it reaches
        # the subscription, which is what every later event carries.
        if not _as_dict(_as_dict(subscription).get("metadata") or {}).get("account_kind") \
                and obj.get("metadata"):
            subscription = stripe.Subscription.modify(
                stripe_sub_id, metadata=dict(obj["metadata"]))
        record_subscription(subscription)
        return f"subscription {stripe_sub_id} recorded from checkout"

    if event_type.startswith("customer.subscription."):
        record_subscription(obj)
        return f"subscription {obj.get('id')} → {obj.get('status')}"

    if event_type.startswith("invoice."):
        record_invoice(obj)
        # An invoice reaching a terminal state can change entitlement, so
        # refresh the subscription alongside it.
        stripe_sub_id = obj.get("subscription")
        if isinstance(stripe_sub_id, dict):
            stripe_sub_id = stripe_sub_id.get("id")
        if stripe_sub_id and event_type in ("invoice.paid", "invoice.payment_failed",
                                            "invoice.marked_uncollectible"):
            stripe = _stripe(cfg)
            record_subscription(stripe.Subscription.retrieve(stripe_sub_id))
        return f"invoice {obj.get('id')} → {obj.get('status')}"

    return f"ignored {event_type}"
