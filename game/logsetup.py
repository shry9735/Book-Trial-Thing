#!/usr/bin/env python3
"""
logsetup.py — one place that decides what the logs look like.

Development gets readable lines.  Production gets one JSON object per
line on stdout, which is what every log shipper expects and what makes
"show me every failed login for this username" a query rather than a
grep.

Nothing here logs a password, a token, or a session cookie.  Usernames
and org ids are logged because an incident is unanswerable without them.
"""

import json
import logging
import sys
import time

# Attributes LogRecord always carries; anything else on a record came
# from an `extra=` and is worth emitting.
_STANDARD = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":      time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + "Z",
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(cfg) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if cfg.LOG_JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s  %(message)s", "%H:%M:%S"))

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(cfg.LOG_LEVEL)

    # Werkzeug's per-request line duplicates the access log the proxy
    # already writes, and it is noisy at INFO.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
