#!/usr/bin/env python3
"""
config.py — every knob this app reads from the environment.

Nothing here touches the filesystem for state.  A container can be
destroyed and recreated with no data loss, because the only durable
things are Postgres and the object store the art is served from.

Required in production (APP_ENV=production):

    SECRET_KEY      64 hex chars — signs session cookies.  Generate with
                    `python -c "import secrets;print(secrets.token_hex(32))"`
    DATABASE_URL    postgresql://user:pass@host:5432/dbname

Everything else has a working default.  See DEPLOY.md.
"""

import os
import secrets
import sys


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        sys.exit(f"Config error: {name}={raw!r} is not an integer.")


class Config:
    # ── Environment ─────────────────────────────────────────────────────────
    #
    # Three values, and almost everything else hangs off which one is set:
    #
    #   development  a bare `python app.py`. Everything relaxed.
    #   local        the whole stack on one machine — real Postgres, real
    #                gunicorn, real migrations — but no TLS anywhere and
    #                mail to the log. For proving it works before it is
    #                anywhere near AWS.
    #   production   a real deployment. Every guard on, no exemptions.
    #
    # A typo here used to fall through to development in silence, which
    # switched off secure cookies, proxy handling and every boot check at
    # once. validate() now refuses anything it does not recognise.
    ENVIRONMENTS = ("development", "local", "production")

    ENV        = os.environ.get("APP_ENV", "development").strip().lower()
    IS_PROD    = ENV == "production"
    # Production-shaped, but running on somebody's laptop: no certificate,
    # no managed database, no mail provider.
    IS_LOCAL   = ENV == "local"
    BASE_URL   = os.environ.get("BASE_URL", "http://localhost:5000").rstrip("/")

    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL  = os.environ.get("DATABASE_URL", "")
    DB_POOL_MIN   = _int("DB_POOL_MIN", 1)
    # Each gunicorn worker opens its own pool, so the ceiling on Postgres
    # connections is WEB_CONCURRENCY * DB_POOL_MAX.  Keep the product under
    # your server's max_connections (default 100).
    DB_POOL_MAX   = _int("DB_POOL_MAX", 5)
    DB_TIMEOUT    = _int("DB_TIMEOUT", 10)
    # How long migrations keep retrying a database that is not answering
    # yet. Only relevant when RUN_MIGRATIONS is on; production should be
    # applying them in a pre-deploy step instead. See docs/AWS_READINESS.md.
    DB_BOOT_RETRY = _int("DB_BOOT_RETRY", 30)

    # ── Sessions ────────────────────────────────────────────────────────────
    SECRET_KEY        = os.environ.get("SECRET_KEY", "")
    SESSION_DAYS      = _int("SESSION_DAYS", 14)
    # Behind a TLS-terminating proxy the cookie must still be Secure; set
    # this to false only for plain-HTTP local development.
    # Off for local: a Secure cookie is never returned over plain http,
    # so leaving it on would make signing in silently impossible.
    COOKIE_SECURE     = _bool("COOKIE_SECURE", IS_PROD)
    # How many proxies sit in front of us.  Wrong values here let a client
    # spoof its own IP via X-Forwarded-For, which would defeat rate limiting.
    TRUSTED_PROXIES   = _int("TRUSTED_PROXIES", 1 if IS_PROD else 0)

    # ── Signup / verification ───────────────────────────────────────────────
    REQUIRE_EMAIL_VERIFICATION = _bool("REQUIRE_EMAIL_VERIFICATION", IS_PROD)
    # Students must attest to this age at signup.  Below 13, US COPPA
    # applies and this app is not built for it — see DEPLOY.md.
    MIN_AGE           = _int("MIN_AGE", 13)
    TOKEN_HOURS       = _int("TOKEN_HOURS", 24)      # verify + reset link life

    # ── Rate limiting (all windows in seconds) ──────────────────────────────
    RL_WINDOW         = _int("RL_WINDOW", 900)       # 15 minutes
    RL_LOGIN_USER     = _int("RL_LOGIN_USER", 10)    # failures per username
    RL_LOGIN_IP       = _int("RL_LOGIN_IP", 30)      # failures per IP
    RL_SIGNUP_IP      = _int("RL_SIGNUP_IP", 10)     # signups per IP
    RL_RESET_IP       = _int("RL_RESET_IP", 10)      # reset requests per IP

    # ── Email ───────────────────────────────────────────────────────────────
    # Backend "console" prints the message to stdout, which is what local
    # development and the test suite use.  "smtp" needs the SMTP_* values.
    EMAIL_BACKEND     = os.environ.get("EMAIL_BACKEND", "console").strip().lower()
    EMAIL_FROM        = os.environ.get("EMAIL_FROM", "Ignite Academy <no-reply@localhost>")
    SMTP_HOST         = os.environ.get("SMTP_HOST", "")
    SMTP_PORT         = _int("SMTP_PORT", 587)
    SMTP_USER         = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD     = os.environ.get("SMTP_PASSWORD", "")
    SMTP_STARTTLS     = _bool("SMTP_STARTTLS", True)

    # ── Billing (Stripe) ────────────────────────────────────────────────────
    # Card data never reaches this server: Checkout and the Customer Portal
    # are pages on Stripe's own domain, and we only ever hold their ids.
    STRIPE_SECRET_KEY      = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET  = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    # Price lookup keys, not price ids — a lookup key survives you creating
    # a new price for a rate change, so a price rise is a Stripe dashboard
    # task rather than a deploy.
    PRICE_FAMILY           = os.environ.get("STRIPE_PRICE_FAMILY", "family_monthly")
    PRICE_ORG_SEAT         = os.environ.get("STRIPE_PRICE_ORG_SEAT", "org_seat_monthly")
    TRIAL_DAYS             = _int("STRIPE_TRIAL_DAYS", 14)

    # How long access survives a payment that has not landed. Card failures
    # resolve in days; a school paying a net-30 invoice through a purchase
    # order routinely takes longer than the terms, and cutting a classroom
    # off mid-term over an invoice in someone's approval queue is the wrong
    # trade.
    GRACE_DAYS_CARD        = _int("GRACE_DAYS_CARD", 14)
    GRACE_DAYS_INVOICE     = _int("GRACE_DAYS_INVOICE", 45)
    INVOICE_DUE_DAYS       = _int("INVOICE_DUE_DAYS", 30)

    # Physical goods live in an Amazon storefront, which runs its own
    # checkout. Nothing about it touches this app or its PCI scope — it is
    # a link.
    STORE_URL              = os.environ.get("STORE_URL", "").rstrip("/")

    # ── Legal pages ─────────────────────────────────────────────────────────
    # The Terms and Privacy pages are built from Markdown in
    # content/legal/, with these values substituted in. They ship as
    # boilerplate: a starting point drafted for this product's actual
    # shape, NOT reviewed by a lawyer and not legal advice.
    #
    # LEGAL_REVIEWED is the switch that says a lawyer has been over them.
    # Until it is set, every legal page carries a visible banner saying so,
    # which is the honest thing to show and also very hard to forget about.
    LEGAL_ENTITY      = os.environ.get("LEGAL_ENTITY", "").strip()
    LEGAL_EMAIL       = os.environ.get("LEGAL_EMAIL", "").strip()
    LEGAL_ADDRESS     = os.environ.get("LEGAL_ADDRESS", "").strip()
    # Where disputes are heard, e.g. "the State of Ohio, USA".
    LEGAL_JURISDICTION = os.environ.get("LEGAL_JURISDICTION", "").strip()
    LEGAL_EFFECTIVE   = os.environ.get("LEGAL_EFFECTIVE", "").strip()
    LEGAL_REVIEWED    = _bool("LEGAL_REVIEWED", False)

    # ── Static assets ───────────────────────────────────────────────────────
    # Set to a CDN origin (https://cdn.example.com) to serve /static from it.
    # Empty means Flask serves the files, which is fine for a single box.
    CDN_URL           = os.environ.get("CDN_URL", "").rstrip("/")
    STATIC_MAX_AGE    = _int("STATIC_MAX_AGE", 60 * 60 * 24 * 30)

    # ── Logging ─────────────────────────────────────────────────────────────
    LOG_LEVEL         = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    # Readable lines on a laptop, machine-parseable in production.
    LOG_JSON          = _bool("LOG_JSON", IS_PROD)


def validate() -> Config:
    """
    Fail loudly at boot rather than quietly at 9am on a school day.

    In development the missing pieces get safe stand-ins; in production
    they are hard errors, because a generated secret key would silently
    log every user out on each restart and each worker would disagree
    about cookie signatures.
    """
    cfg = Config()
    problems: list[str] = []

    # Everything below keys off this, so a typo — APP_ENV=prod, say — used
    # to silently land in development and switch off secure cookies, proxy
    # handling and every check in this function at once.
    if cfg.ENV not in Config.ENVIRONMENTS:
        sys.exit(f"Configuration error:\n  - APP_ENV={cfg.ENV!r} is not one of "
                 f"{', '.join(Config.ENVIRONMENTS)}.")

    if not cfg.DATABASE_URL:
        if cfg.IS_PROD:
            problems.append("DATABASE_URL is required.")
        else:
            cfg.DATABASE_URL = "postgresql://ignite:ignite@localhost:5432/ignite"
            print(f"  config: DATABASE_URL unset, using {cfg.DATABASE_URL}", file=sys.stderr)

    if not cfg.SECRET_KEY:
        if cfg.IS_PROD:
            problems.append("SECRET_KEY is required (64 hex chars).")
        else:
            cfg.SECRET_KEY = secrets.token_hex(32)
            print("  config: SECRET_KEY unset, generated a temporary one —", file=sys.stderr)
            print("          sessions will not survive a restart.", file=sys.stderr)
    elif len(cfg.SECRET_KEY) < 32:
        problems.append("SECRET_KEY is too short; use at least 32 characters.")

    if cfg.EMAIL_BACKEND == "smtp" and not cfg.SMTP_HOST:
        problems.append("EMAIL_BACKEND=smtp needs SMTP_HOST.")

    if cfg.EMAIL_BACKEND not in ("console", "smtp"):
        problems.append(f"EMAIL_BACKEND={cfg.EMAIL_BACKEND!r} is not 'console' or 'smtp'.")

    # Billing is optional: with no key the app runs with every lesson open,
    # which is what development and a free pilot want. But a half-configured
    # Stripe is worse than none — an unverifiable webhook would let anyone
    # POST themselves a subscription.
    if cfg.STRIPE_SECRET_KEY and not cfg.STRIPE_WEBHOOK_SECRET:
        problems.append("STRIPE_SECRET_KEY is set but STRIPE_WEBHOOK_SECRET is not — "
                        "webhook signatures could not be verified.")
    if cfg.STRIPE_WEBHOOK_SECRET and not cfg.STRIPE_SECRET_KEY:
        problems.append("STRIPE_WEBHOOK_SECRET is set but STRIPE_SECRET_KEY is not.")
    if cfg.IS_PROD and cfg.STRIPE_SECRET_KEY.startswith("sk_test_"):
        problems.append("A Stripe test key is configured in production.")

    # A production box that requires email verification but cannot send
    # email boots perfectly happily and lets nobody finish signing up. That
    # used to be a warning on stderr, which is to say invisible.
    if cfg.IS_PROD and cfg.EMAIL_BACKEND == "console":
        if cfg.REQUIRE_EMAIL_VERIFICATION:
            problems.append(
                "EMAIL_BACKEND=console with REQUIRE_EMAIL_VERIFICATION=true in "
                "production: verification links would only reach the logs, so no "
                "one could finish signing up. Configure SMTP, or set "
                "REQUIRE_EMAIL_VERIFICATION=false deliberately.")
        else:
            print("  config: EMAIL_BACKEND=console in production — password-reset",
                  file=sys.stderr)
            print("          links will only appear in the logs.", file=sys.stderr)

    # Behind a load balancer with TRUSTED_PROXIES=0, request.remote_addr is
    # the balancer's own address, so every user in the world shares one
    # rate-limit bucket and one wrong password locks out everybody.
    if cfg.IS_PROD and cfg.TRUSTED_PROXIES < 1:
        problems.append(
            "TRUSTED_PROXIES=0 in production. Set it to the number of proxies in "
            "front of the app (1 for a bare ALB, 2 behind CloudFront), or every "
            "request will look like it came from the load balancer.")

    # psycopg defaults to sslmode=prefer, which silently falls back to
    # plaintext when the server allows it — and RDS allows it unless
    # rds.force_ssl is set. This is student data.
    if cfg.IS_PROD and cfg.DATABASE_URL:
        mode = ""
        if "sslmode=" in cfg.DATABASE_URL:
            mode = cfg.DATABASE_URL.split("sslmode=", 1)[1].split("&")[0].strip()
        if mode not in ("require", "verify-ca", "verify-full"):
            problems.append(
                f"DATABASE_URL has sslmode={mode or '(unset)'}. In production it must "
                "be require, verify-ca or verify-full — anything else lets the "
                "connection quietly fall back to plaintext.")

    if cfg.IS_PROD and not cfg.COOKIE_SECURE:
        problems.append("COOKIE_SECURE=false in production would send session cookies over plain HTTP.")

    if cfg.IS_PROD and cfg.BASE_URL.startswith("http://"):
        problems.append("BASE_URL must be https:// in production — it is used to build email links.")

    # Signup requires ticking a box that says "I agree to the terms". If the
    # pages behind it still say [YOUR COMPANY], that consent is worthless and
    # the box is worse than not having one. Unfilled placeholders in
    # production are a mistake, not a decision, so they stop the boot.
    if cfg.IS_PROD:
        missing = [name for name in ("LEGAL_ENTITY", "LEGAL_EMAIL", "LEGAL_JURISDICTION")
                   if not getattr(cfg, name)]
        if missing:
            problems.append(
                f"{', '.join(missing)} unset in production. The Terms and Privacy "
                "pages are linked from the signup consent checkbox and would render "
                "with unfilled placeholders. See docs/LEGAL.md.")

    if problems:
        sys.exit("Configuration errors:\n" + "\n".join(f"  - {p}" for p in problems))

    if cfg.IS_PROD and not cfg.LEGAL_REVIEWED:
        # A warning, not an error: shipping a pilot on boilerplate is a
        # decision somebody is allowed to make. Every legal page says so in
        # a banner, so nobody is misled while it is switched off.
        print("  config: LEGAL_REVIEWED=false — the Terms and Privacy pages are",
              file=sys.stderr)
        print("          unreviewed boilerplate and say so to every visitor.",
              file=sys.stderr)

    if cfg.IS_LOCAL:
        # Loud on purpose. Local waives the checks that a laptop cannot
        # satisfy, and nobody should be able to run this by accident and
        # think they are looking at a production-equivalent box.
        print("  config: APP_ENV=local — running with laptop exemptions:", file=sys.stderr)
        print("          no TLS to the database, cookies not marked Secure,",
              file=sys.stderr)
        print("          email to the log. Never use this on a real deployment.",
              file=sys.stderr)

    return cfg
