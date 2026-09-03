#!/usr/bin/env python3
"""
emailer.py — verification and password-reset mail.

Two backends.  "console" writes the message to the log, which is what
local development uses: the reset link is right there in the terminal, no
mail server needed.  "smtp" sends for real.

Sending is best-effort by design.  A signup must not 500 because the mail
provider is having a bad afternoon — the account is already created and
the user can ask for another link.  Failures are logged, loudly.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger("ignite.email")


def _send_smtp(cfg, to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = cfg.EMAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=10) as smtp:
        if cfg.SMTP_STARTTLS:
            smtp.starttls(context=ssl.create_default_context())
        if cfg.SMTP_USER:
            smtp.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
        smtp.send_message(msg)


def send(cfg, to: str, subject: str, body: str) -> bool:
    """Deliver one message, or log why it could not be.

    Always returns rather than raising. A signup must not 500 because the
    mail provider is having a bad afternoon — the account already exists
    and the person can ask for another link.
    """
    if not to:
        return False
    try:
        if cfg.EMAIL_BACKEND == "smtp":
            _send_smtp(cfg, to, subject, body)
            log.info("email sent", extra={"to": to, "subject": subject})
        else:
            log.info(
                "email (console backend)\n"
                "  To:      %s\n"
                "  Subject: %s\n"
                "%s", to, subject,
                "\n".join(f"  | {line}" for line in body.splitlines()),
            )
        return True
    except Exception:
        # Deliberately swallowed: see the module docstring.
        log.exception("email delivery failed", extra={"to": to, "subject": subject})
        return False


def send_verification(cfg, to: str, name: str, link: str) -> bool:
    return send(cfg, to, "Confirm your Ignite Academy email", f"""Hi {name},

Confirm this address to finish setting up your Ignite Academy account:

    {link}

The link works for {cfg.TOKEN_HOURS} hours. If you didn't sign up, you can
ignore this message — no account will be usable without confirming.
""")


def send_reset(cfg, to: str, name: str, link: str) -> bool:
    return send(cfg, to, "Reset your Ignite Academy password", f"""Hi {name},

Someone asked to reset the password on your Ignite Academy account. If it
was you, set a new one here:

    {link}

The link works for {cfg.TOKEN_HOURS} hours and can only be used once.

If it wasn't you, nothing has changed and you can ignore this message.
Your current password still works.
""")
