#!/usr/bin/env bash
#
# stop-demo.sh — shut down what demo.sh started.
#
#     ./stop-demo.sh           stop the app and database, keep the demo data
#     ./stop-demo.sh --wipe    stop and delete the database too
#
# After a plain stop, ./demo.sh brings the same school back with the same
# logins. After --wipe, ./demo.sh builds a fresh one from scratch.

set -euo pipefail
cd "$(dirname "$0")"

BOLD=$'\033[1m'; RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
[ -t 1 ] || { BOLD=""; RED=""; GREEN=""; YELLOW=""; RESET=""; }

say()  { printf '%s\n' "$*"; }
die()  { printf '\n%serror:%s %s\n\n' "$RED" "$RESET" "$*" >&2; exit 1; }

case "${1:-}" in
  ""|--wipe) ;;
  -h|--help) sed -n '3,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) die "Unknown option '$1'. Try ./stop-demo.sh or ./stop-demo.sh --wipe." ;;
esac

command -v docker >/dev/null 2>&1 || die "Docker is not installed, so there is no demo running."
docker info >/dev/null 2>&1 || die \
"This user cannot talk to Docker. Run it the same way you ran demo.sh,
  e.g.  sudo ./stop-demo.sh"

case "${1:-}" in
  "")
    docker compose down --remove-orphans
    say ""
    say "${GREEN}Demo stopped.${RESET} Data kept — ${BOLD}./demo.sh${RESET} brings it back."
    ;;
  --wipe)
    printf '%s !%s Deleting the demo database as well.\n' "$YELLOW" "$RESET"
    docker compose down --volumes --remove-orphans
    # demo.sh writes .env with the database password on first run. The
    # volume that password belonged to is gone, so let the next run make
    # a new pair rather than point at a database that does not exist.
    rm -f .env
    say ""
    say "${GREEN}Demo stopped and wiped.${RESET} ${BOLD}./demo.sh${RESET} starts a fresh one."
    ;;
esac
