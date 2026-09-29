#!/usr/bin/env python3
"""
security.py — the request-level guards.

Four separate concerns that all have to be right before this is on the
open internet:

  CSRF        A signed session cookie alone means any site can make the
              browser POST to us with the user's credentials attached.
  RATE LIMIT  Login is a slow (deliberately slow) password check, so an
              unthrottled login endpoint is both a brute-force target and
              a cheap way to exhaust the worker pool.
  REDIRECTS   ?next= is user input and has to be proven local.
  HEADERS     Clickjacking, MIME sniffing and referrer leakage.

The rate-limit counters live in Postgres (see db.rate_events) because
they must be shared across gunicorn workers and containers.  An
in-process counter resets on deploy and is sidestepped by landing on a
different worker.
"""

from __future__ import annotations

import gzip
import hashlib
import hmac
import logging
import re
import secrets
from urllib.parse import urlparse

from flask import abort, request, session

import db

log = logging.getLogger("ignite.security")

CSRF_SESSION_KEY = "_csrf"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


# ── CSRF ────────────────────────────────────────────────────────────────────────

def csrf_token() -> str:
    """The per-session token.  Exposed to Jinja as csrf_token()."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def rotate_csrf_token() -> str:
    """Issue a fresh token — called on login and logout."""
    session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    return session[CSRF_SESSION_KEY]


def _submitted_token() -> str:
    return (request.form.get(CSRF_FORM_FIELD)
            or request.headers.get(CSRF_HEADER)
            or "")


def csrf_exempt(fn):
    """
    Mark a view as exempt from the CSRF check.

    Only for endpoints that authenticate the *request itself* rather than
    the session — the Stripe webhook proves origin with a signature over
    the raw body, and has no session or form to carry a token. Anything
    that relies on a cookie for authority must not use this.
    """
    fn._csrf_exempt = True
    return fn


def check_csrf(view_func=None) -> None:
    """
    Reject any unsafe request that cannot prove it came from our own page.

    HTML forms carry a token.  JSON endpoints are held to a different but
    equally strict test: they must be sent as application/json, which a
    cross-origin page cannot do without a CORS preflight that we never
    answer.  That closes the gap without every lesson's iframe having to
    learn about tokens.

    SameSite=Lax on the session cookie is the belt to this pair of braces:
    a cross-site POST does not get the cookie in the first place.
    """
    if request.method in SAFE_METHODS:
        return

    # Exempt by explicit decoration, never by URL shape: a path-prefix rule
    # would silently exempt any future route that happened to match it.
    if getattr(view_func, "_csrf_exempt", False):
        return

    if request.path.startswith("/api/"):
        if not request.is_json:
            log.warning("api rejected: content-type %r", request.content_type)
            abort(415, "API requests must be sent as application/json.")
        return

    expected = session.get(CSRF_SESSION_KEY)
    supplied = _submitted_token()
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        log.warning("csrf rejected on %s", request.path)
        abort(400, "Your session expired. Go back, reload the page and try again.")


# ── Client identity ─────────────────────────────────────────────────────────────

# Latched so the misconfiguration below is reported once per process
# rather than on every single request.
_warned_about_proxy = False


def client_ip(trusted_proxies: int) -> str:
    """
    The caller's address, honouring X-Forwarded-For only as far as we
    actually trust it.

    With one proxy in front, the last entry is the one our proxy wrote and
    every entry before it is client-supplied and forgeable.  Reading the
    leftmost value — the common mistake — would let anyone set their own
    rate-limit bucket with a header.

    If a forwarding header is present while trusted_proxies is 0, we are
    behind a proxy that nobody told us about, and remote_addr is that
    proxy — meaning every user in the world would share one rate-limit
    bucket and a single wrong password would lock out everybody. That is
    almost always APP_ENV not being set to "production", which silently
    switches off this setting along with secure cookies and every
    boot-time check. It is worth a loud line in the log.
    """
    global _warned_about_proxy

    if trusted_proxies > 0:
        forwarded = request.headers.get("X-Forwarded-For", "")
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= trusted_proxies:
            return parts[-trusted_proxies]
    elif request.headers.get("X-Forwarded-For") and not _warned_about_proxy:
        _warned_about_proxy = True
        log.error(
            "X-Forwarded-For is present but TRUSTED_PROXIES=0, so every request "
            "looks like it came from the proxy and all users share one rate-limit "
            "bucket. Set TRUSTED_PROXIES (and check APP_ENV=production).")

    return request.remote_addr or "unknown"


# ── Rate limiting ───────────────────────────────────────────────────────────────

def _bucket(kind: str, value: str) -> str:
    # Hashed so the table never holds a raw username or address.
    digest = hashlib.sha256(value.lower().encode("utf-8")).hexdigest()[:32]
    return f"{kind}:{digest}"


def over_limit(kind: str, value: str, limit: int, window: int) -> bool:
    """Whether this bucket has already used up its allowance.

    Fails OPEN. If the rate-limit lookup itself errors, the request is let
    through and the failure is logged — a database hiccup should not lock
    every user out of signing in. That trade is deliberate: the limiter
    protects against brute force, and brute force is a worse outcome than
    a brief window of no limiting, but not worse than a total outage.
    """
    try:
        return db.rate_count(_bucket(kind, value), window) >= limit
    except Exception:
        # A rate-limit lookup that fails should not take the site down;
        # log it and let the request through.
        log.exception("rate limit check failed for %s", kind)
        return False


def record_attempt(kind: str, value: str) -> None:
    """Count one attempt against a bucket.

    Swallows its own errors for the same reason as over_limit(): failing to
    record an attempt must not turn into a failed login for the user.
    """
    try:
        db.rate_hit(_bucket(kind, value))
    except Exception:
        log.exception("rate limit record failed for %s", kind)


def clear_attempts(kind: str, value: str) -> None:
    """Empty a bucket, after a success.

    One good login wipes the failure count, so a user who mistypes their
    password four times and then gets it right is not still half-way to a
    lockout.
    """
    try:
        db.rate_clear(_bucket(kind, value))
    except Exception:
        log.exception("rate limit clear failed for %s", kind)


# ── Redirects ───────────────────────────────────────────────────────────────────

def safe_next(target: str | None, fallback: str = "/") -> str:
    """
    Only ever redirect somewhere on this site.

    `target.startswith("/")` is not enough on its own: "//evil.example.com"
    starts with a slash and browsers read it as a protocol-relative URL to
    another host, which is an open redirect and a ready-made phishing step.
    """
    if not target:
        return fallback
    if not target.startswith("/") or target.startswith("//") or target.startswith("/\\"):
        return fallback
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return fallback
    return target


# ── Response headers ────────────────────────────────────────────────────────────

# Types worth compressing. Everything else is either already compressed
# (webp, png, woff2) or too small to be worth the CPU.
COMPRESSIBLE = (
    "text/html", "text/css", "text/plain", "text/markdown",
    "application/javascript", "text/javascript",
    "application/json", "image/svg+xml",
)

# Matches nginx's gzip_min_length. Below roughly this, the gzip header and
# trailer eat the saving and a small response gets slower, not smaller.
COMPRESS_MIN_BYTES = 1024

# Ceiling for buffering a streamed file in order to compress it. send_file()
# hands back a response in direct-passthrough mode so a large file is never
# held in memory; overriding that is right for a 60KB stylesheet and wrong
# for a video, so it only happens below this size.
COMPRESS_MAX_BUFFER = 512 * 1024


def compress(response, request):
    """
    gzip a response when the client asked for it and it is worth doing.

    This lives in the app because the default deployment has nothing in
    front of it: `docker compose up` publishes gunicorn straight onto a
    port, and nginx only appears under `--profile tls`. Measured across
    the real pages, HTML compresses about 81% and the stylesheet 80%, for
    0.2-0.5ms of CPU — which is the difference between a snappy demo and a
    sluggish one over conference wifi or a phone hotspot.

    Behind nginx this is not wasted: nginx sees a Content-Encoding it did
    not set and passes the body straight through rather than compressing
    it a second time.

    Vary is appended rather than set, because some responses already vary
    on Cookie and clobbering that would let a shared cache serve one
    account's page to another.
    """
    if response.status_code < 200 or response.status_code >= 300:
        return response
    if "Content-Encoding" in response.headers:
        return response
    if "gzip" not in request.headers.get("Accept-Encoding", "").lower():
        return response
    if response.mimetype not in COMPRESSIBLE:
        return response
    if response.content_length is not None and response.content_length < COMPRESS_MIN_BYTES:
        return response

    if response.direct_passthrough:
        # send_file() streams rather than buffering, which is right for
        # media and wrong for the 60KB stylesheet that every page loads.
        # Take it out of passthrough only when we know the size and it is
        # small enough to hold; anything larger keeps streaming uncompressed.
        if response.content_length is None or response.content_length > COMPRESS_MAX_BUFFER:
            return response
        response.direct_passthrough = False

    body = response.get_data()
    if len(body) < COMPRESS_MIN_BYTES:
        return response
    packed = gzip.compress(body, 6)
    if len(packed) >= len(body):
        # Already-dense content. Shipping it larger would be absurd.
        return response

    response.set_data(packed)
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Content-Length"] = str(len(packed))
    vary = response.headers.get("Vary")
    if not vary:
        response.headers["Vary"] = "Accept-Encoding"
    elif "accept-encoding" not in vary.lower():
        response.headers["Vary"] = f"{vary}, Accept-Encoding"
    return response


def apply_headers(response, cfg):
    """
    Defaults for every response.

    frame-ancestors 'self' rather than a blanket DENY: lessons are
    deliberately rendered in same-origin iframes, and that is the whole
    isolation model, so it has to keep working while still blocking any
    other site from framing us.
    """
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
    )
    if cfg.IS_PROD:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


# ── Input rules ─────────────────────────────────────────────────────────────────

USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,32}$")
# Deliberately permissive. Real validation is "we sent mail and they
# clicked the link"; a clever regex only rejects valid addresses.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD = 10


def username_problem(username: str) -> str | None:
    """Explain what is wrong with a username, or None if nothing is.

    Returns the message rather than raising, so the caller can put it
    straight in front of the person who typed it.
    """
    if not username:
        return "Pick a username."
    if not USERNAME_RE.match(username):
        return ("Usernames are 3–32 characters, letters and numbers plus "
                "dot, dash or underscore.")
    return None


def email_problem(email: str, required: bool = True) -> str | None:
    """Explain what is wrong with an email address, or None if nothing is.

    Deliberately permissive: the real validation is that we sent mail and
    they clicked the link. A stricter regex only rejects valid addresses
    belonging to real people.
    """
    if not email:
        return "Enter an email address." if required else None
    if len(email) > 254 or not EMAIL_RE.match(email):
        return "That doesn't look like an email address."
    return None


def password_problem(password: str, confirm: str | None = None) -> str | None:
    """
    Length over character classes.  Composition rules push people toward
    "Password1!" and NIST stopped recommending them years ago.
    """
    if len(password) < MIN_PASSWORD:
        return f"Passwords need at least {MIN_PASSWORD} characters."
    if len(password) > 256:
        return "That password is too long."
    if confirm is not None and password != confirm:
        return "The two passwords don't match."
    if password.lower() in COMMON_PASSWORDS:
        return "That password is too common — pick something else."
    return None


COMMON_PASSWORDS = {
    "password", "password1", "password123", "1234567890", "12345678910",
    "qwertyuiop", "letmein123", "iloveyou1", "welcome123", "admin12345",
    "abc123456", "spark12345", "ignite1234", "changeme123", "passw0rd123",
}


# ── Tokens ──────────────────────────────────────────────────────────────────────

def new_token() -> tuple[str, str]:
    """
    Return (token_for_the_link, hash_for_the_database).

    Only the hash is stored, so a database leak does not hand over working
    password-reset links.
    """
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── Handed-out passwords ────────────────────────────────────────────────────────

# No 0/O/1/I/L/5/S: this gets printed on a slip of paper and typed by an
# eleven-year-old. The same reasoning as db._CODE_ALPHABET, one character
# stricter, because a join code is read back to a teacher who can correct
# it and this is not.
_TEMP_ALPHABET = "abcdefghjkmnpqrstuvwxyz"
_TEMP_DIGITS = "23456789"


def temp_password() -> str:
    """
    A first password for an account somebody else created.

    Three lowercase syllables and two digits — "loper-fadu-nizo-47" —
    which is long enough to clear MIN_PASSWORD and to survive being read
    off a printout without a support call. It is not meant to be strong
    for long: whoever receives it can only reach the page that replaces
    it, and the account carries must_change_password until they do.

    Roughly 23^9 * 8^2 combinations, which is far past guessing range for
    a value that is single-use and rate limited on the login form anyway.
    """
    chunks = ["".join(secrets.choice(_TEMP_ALPHABET) for _ in range(3))
              for _ in range(3)]
    digits = "".join(secrets.choice(_TEMP_DIGITS) for _ in range(2))
    return "-".join(chunks) + "-" + digits
