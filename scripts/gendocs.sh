#!/usr/bin/env bash
#
# gendocs.sh — build the browsable API reference and refresh the call graph.
#
#   ./scripts/gendocs.sh            # build into docs/api/
#   ./scripts/gendocs.sh --serve    # live-reloading server on :8080
#
# Two different artefacts, for two different moments:
#
#   docs/api/        Every module, function and signature, rendered from the
#                    docstrings already in the source. Read it when you want
#                    to know what a function does.
#
#   docs/CALLGRAPH.md   Which route touches which module, and whether the
#                    layering still holds. Read it when you want to know what
#                    a change will break. Committed, because GitHub renders
#                    its Mermaid inline and its diff is reviewable.
#
# docs/api/ is NOT committed — generated HTML makes diffs unreadable. Build
# it locally, or publish it with .github/workflows/docs.yml.

set -euo pipefail

cd "$(dirname "$0")/.."

# Prefer the project virtualenv, fall back to whatever python is on PATH.
PY="./.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"

if ! "$PY" -c "import pdoc" 2>/dev/null; then
  echo "pdoc is not installed. Install the docs extras:" >&2
  echo "    $PY -m pip install -r requirements-dev.txt" >&2
  exit 1
fi

# The modules are a flat directory rather than an installed package, so
# point the import path at it and name them individually.
export PYTHONPATH="game:${PYTHONPATH:-}"

# pdoc imports each module to read its signatures. app.py builds its config
# at import time, so give it enough environment to succeed — nothing here
# connects to anything, and APP_ENV stays development so the production
# checks do not fire.
export APP_ENV="${APP_ENV:-development}"
export SECRET_KEY="${SECRET_KEY:-0000000000000000000000000000000000000000000000000000000000000000}"
export DATABASE_URL="${DATABASE_URL:-postgresql://localhost/ignite_docs}"

# wsgi.py is left out on purpose: it calls init_app() at import, which
# opens a database connection. A docs build must not need a live database.
MODULES=(app db billing security config emailer logsetup manage migrate_json)

if [[ "${1:-}" == "--serve" ]]; then
  echo "→ serving API docs at http://localhost:8080 (ctrl-c to stop)"
  exec "$PY" -m pdoc --docformat google "${MODULES[@]}"
fi

echo "→ building API reference into docs/api/"
rm -rf docs/api
"$PY" -m pdoc --docformat google \
      --output-directory docs/api \
      --logo-link "https://github.com/shry9735/Book-Trial-Thing" \
      "${MODULES[@]}"

echo "→ refreshing docs/CALLGRAPH.md"
"$PY" scripts/callgraph.py

echo
echo "  API reference : docs/api/index.html"
echo "  Call graph    : docs/CALLGRAPH.md"
echo
echo "  Open the reference with:  open docs/api/index.html"
