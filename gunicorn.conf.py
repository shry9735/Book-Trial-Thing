#!/usr/bin/env python3
"""
gunicorn.conf.py — production WSGI server settings.

    gunicorn -c gunicorn.conf.py --chdir game wsgi:app

The Flask development server this replaces is single-threaded and has no
request timeouts; it must never face users.
"""

import multiprocessing
import os
import pathlib


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
def _available_cpus() -> int:
    """
    CPUs this container may actually use — not the host's.

    multiprocessing.cpu_count() reports the machine, so a 0.5-vCPU task on
    a 16-core ECS instance would size itself for sixteen: too many workers
    thrashing one slice of CPU, and each one carrying its own database
    pool, which is how a small task opens forty connections.

    cgroup quota first (what the orchestrator actually enforces), then CPU
    affinity, then the host count as a last resort.
    """
    try:
        quota, period = pathlib.Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if quota != "max":
            return max(1, int(int(quota) / int(period)))
    except Exception:
        pass
    try:                                            # cgroup v1
        quota = int(pathlib.Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        period = int(pathlib.Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if quota > 0 and period > 0:
            return max(1, int(quota / period))
    except Exception:
        pass
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except AttributeError:
        return max(1, multiprocessing.cpu_count())


# Set WEB_CONCURRENCY explicitly in production anyway: the connection
# arithmetic in DEPLOY.md (workers x DB_POOL_MAX under the server's
# max_connections) only holds if you know this number.
workers = _int("WEB_CONCURRENCY", min(_available_cpus() * 2 + 1, 8))

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
