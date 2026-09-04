# ── Build ─────────────────────────────────────────────────────────────────────
# Wheels are built in a throwaway stage so the runtime image carries no
# compiler and no build caches.
FROM python:3.12-slim AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY requirements.txt .
RUN python -m venv /venv \
 && /venv/bin/pip install --upgrade pip \
 && /venv/bin/pip install -r requirements.txt


# ── Runtime ───────────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH" \
    APP_ENV=production

# Runs as a non-root user: a container escape should not start from uid 0.
RUN useradd --system --create-home --uid 10001 ignite

COPY --from=build /venv /venv

WORKDIR /app
COPY --chown=ignite:ignite game/ ./game/
COPY --chown=ignite:ignite gunicorn.conf.py ./

USER ignite
EXPOSE 8000

# Liveness only, deliberately. This decides whether the orchestrator KILLS
# the container, so it must not fail just because the database is briefly
# away — the pool reconnects by itself, and restarting every task during an
# RDS failover turns a two-second blip into an outage.
# Readiness (/healthz) is for dashboards and deploy checks.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/livez', timeout=4).status == 200 else 1)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "--chdir", "game", "wsgi:app"]
