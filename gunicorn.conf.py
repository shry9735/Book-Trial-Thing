#!/usr/bin/env python3
"""
gunicorn.conf.py — production WSGI server settings.

    gunicorn -c gunicorn.conf.py --chdir game wsgi:app

The Flask development server this replaces is single-threaded and has no
request timeouts; it must never face users.
"""

import multiprocessing
import os


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


bind = os.environ.get("BIND", "0.0.0.0:8000")

# Each worker is a process with its own database pool, so the ceiling on
# Postgres connections is workers * DB_POOL_MAX. Keep that product under
# the server's max_connections (100 by default) — the arithmetic is in
# DEPLOY.md.
workers = _int("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 8))

# Threads, not async workers: the work is Postgres round-trips and
# password hashing, and gthread handles that without every library in the
# stack having to be non-blocking.
worker_class = "gthread"
threads = _int("THREADS", 4)

# Slow client protection. Nginx buffers requests in front of this, so a
# request that takes longer than this is our own bug, not a slow phone.
timeout = _int("TIMEOUT", 30)
graceful_timeout = 30
# Must exceed the load balancer's idle timeout or the balancer will hand
# a connection to a worker that has already closed it (the classic
# intermittent 502).
keepalive = _int("KEEPALIVE", 75)

# Recycle workers periodically. Cheap insurance against a slow leak in any
# dependency; jitter stops every worker restarting at the same moment.
max_requests = _int("MAX_REQUESTS", 2000)
max_requests_jitter = 200

preload_app = False       # each worker builds its own pool after forking
accesslog = None          # nginx writes the access log
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

# Where the proxy's forwarded headers are trusted from. "*" is correct
# when nothing but the local reverse proxy can reach this port; on a
# shared network, name the proxy's address instead.
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "*")


def on_starting(server):
    # Read back off the resolved config, not the module globals, so a
    # command-line override is reported accurately.
    server.log.info("ignite academy starting: %s workers, %s threads",
                    server.cfg.workers, server.cfg.threads)
