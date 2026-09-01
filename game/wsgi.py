#!/usr/bin/env python3
"""
wsgi.py — production entry point.

    gunicorn -c ../gunicorn.conf.py wsgi:app

Import happens once per worker process, and init_app() gives that worker
its own connection pool.  Migrations run under an advisory lock, so it
does not matter that every worker calls it.
"""

from app import app, init_app

init_app()

# gunicorn resolves the target as wsgi:app.
__all__ = ["app"]
