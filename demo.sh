#!/usr/bin/env bash
#
# demo.sh — clone, run, demo. One command, from nothing to a seeded school.
#
#     git clone <repo> && cd Book-Trial-Thing
#     ./demo.sh
#
# Brings up Postgres and the app in Docker, waits for the app to say it is
# ready, loads a demo school with a fortnight of history, and prints the
# URL and the logins. Safe to run again: it will not clobber a database
# that already has the demo in it unless you ask.
#
#     ./demo.sh            start, seeding only if the demo is not there yet
#     ./demo.sh --reset    wipe the demo data and rebuild it
#     ./demo.sh --fresh    destroy the database volume and start over
#     ./demo.sh --stop     stop everything, keep the data
#     ./demo.sh --logins   reprint the accounts and the URL
#
# Runs on a Raspberry Pi 5 (64-bit Raspberry Pi OS), on Linux and macOS
# laptops, and on Windows from inside WSL2. It needs Docker with the
# Compose v2 plugin and nothing else — no Python on the host, no Postgres
# on the host.

set -euo pipefail
cd "$(dirname "$0")"

BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'
YELLOW=$'\033[33m'; RESET=$'\033[0m'
[ -t 1 ] || { BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; RESET=""; }

say()  { printf '%s\n' "$*"; }
step() { printf '\n%s==>%s %s%s%s\n' "$GREEN" "$RESET" "$BOLD" "$*" "$RESET"; }
warn() { printf '%s !%s %s\n' "$YELLOW" "$RESET" "$*"; }
die()  { printf '\n%serror:%s %s\n\n' "$RED" "$RESET" "$*" >&2; exit 1; }

# ── Preflight ───────────────────────────────────────────────────────────────
# Every check below exists because failing here with a sentence beats
# failing four minutes into a build with a stack trace.

preflight() {
  command -v docker >/dev/null 2>&1 || die \
"Docker is not installed.

  Raspberry Pi OS / Debian / Ubuntu:
      curl -fsSL https://get.docker.com | sh
      sudo usermod -aG docker \$USER     # then log out and back in

  macOS: install Docker Desktop."

  docker compose version >/dev/null 2>&1 || die \
"Docker is installed but the Compose v2 plugin is not.

  Raspberry Pi OS / Debian / Ubuntu:
      sudo apt install docker-compose-plugin

  'docker-compose' (with a hyphen) is the old v1 and is not enough."

  docker info >/dev/null 2>&1 || die \
"Docker is installed but this user cannot talk to it.

      sudo usermod -aG docker \$USER     # then log out and back in
  or run this script with sudo."

  # 32-bit is the one platform that will waste your afternoon: there is no
  # aarch64 wheel for psycopg on armv7, so pip falls back to compiling libpq
  # from source, which needs a toolchain this image does not carry.
  local arch; arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64|aarch64|arm64) ;;
    armv7l|armv6l) die \
"This is a 32-bit ARM userland ($arch).

  The app's Postgres driver ships wheels for 64-bit only, so the build
  would try to compile libpq from source and fail.

  On a Pi 4 or 5, reflash with the 64-bit Raspberry Pi OS and this works.
  Check with: getconf LONG_BIT   (want 64)" ;;
    *) warn "Unrecognised architecture '$arch' — carrying on, but this is untested." ;;
  esac

  # Postgres plus a Python image plus the build needs room. 3GB is tight
  # but workable; below that the build dies halfway with a confusing error.
  local free_kb; free_kb="$(df -Pk . | awk 'NR==2 {print $4}')"
  if [ "${free_kb:-0}" -lt 3000000 ]; then
    warn "Only $((free_kb / 1024))MB free here. The images want about 2GB."
  fi
}

# ── Configuration ───────────────────────────────────────────────────────────

# A LAN address, so the demo works from a phone or a second laptop rather
# than only from the machine it runs on. Falls back to localhost.
lan_ip() {
  local ip=""
  if command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')" || true
  fi
  if [ -z "$ip" ] && command -v ip >/dev/null 2>&1; then
    ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')" || true
  fi
  # macOS. Ask the routing table which interface actually carries traffic
  # rather than assuming en0: that is Wi-Fi on most MacBooks, but a docked
  # or Ethernet-connected one answers on a different en*, and guessing
  # wrong silently drops BASE_URL back to localhost — which still demos on
  # the laptop itself, but nothing else on the wifi can reach it.
  if [ -z "$ip" ] && command -v ipconfig >/dev/null 2>&1; then
    local iface
    iface="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')" || true
    [ -n "$iface" ] && ip="$(ipconfig getifaddr "$iface" 2>/dev/null)" || true
    if [ -z "$ip" ]; then
      for iface in en0 en1 en2 en3 en4 en5; do
        ip="$(ipconfig getifaddr "$iface" 2>/dev/null)" && [ -n "$ip" ] && break
      done
    fi
  fi
  printf '%s' "${ip:-127.0.0.1}"
}

secret() {
  if command -v openssl >/dev/null 2>&1; then openssl rand -hex 32
  else head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'; fi
}

write_env() {
  [ -f .env ] && return 0
  local ip; ip="$(lan_ip)"
  step "Writing .env (first run)"
  cat > .env <<EOF
# Generated by demo.sh on $(date -u '+%Y-%m-%d %H:%M UTC'). Safe to edit.
#
# These are demo settings. APP_ENV=local means "production-shaped, but on a
# machine with no certificate": real Postgres, real gunicorn, real
# migrations, no TLS. Never point this file at anything public.

APP_ENV=local
SECRET_KEY=$(secret)
POSTGRES_PASSWORD=$(secret)

# The address other devices will use. demo.sh guessed this machine's LAN
# address; edit it if you are demoing over a different interface.
BASE_URL=http://${ip}:8000
APP_PORT=8000

# A Pi 5 has four cores and no spare RAM for twenty idle Postgres
# connections. Two workers is plenty for a demo and leaves the machine
# responsive while somebody is talking over it.
WEB_CONCURRENCY=2
DB_POOL_MAX=3

# No Stripe keys: the billing screens explain that payments are not
# configured instead of erroring. Add keys when you want to demo checkout.
EOF
  say "  ${DIM}wrote .env — SECRET_KEY and POSTGRES_PASSWORD generated${RESET}"
}

# ── Running ─────────────────────────────────────────────────────────────────

compose() { docker compose "$@"; }

wait_ready() {
  step "Waiting for the app to come up"
  local tries=0
  # Asked from inside the container, using the Python that is certainly
  # there: the host may have no curl, and on a first run the published port
  # is the last thing to start working. /healthz is readiness — it checks
  # the database too, which is what we actually need before seeding.
  # /livez would go green while migrations were still running.
  while [ "$tries" -lt 90 ]; do
    if compose exec -T app python -c \
         "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/healthz', timeout=3)" \
         >/dev/null 2>&1; then
      say "  ${GREEN}ready${RESET}"
      return 0
    fi
    tries=$((tries + 1)); sleep 2
    [ $((tries % 15)) -eq 0 ] && say "  ${DIM}still waiting (~$((tries * 2))s)...${RESET}"
  done
  say ""
  compose logs --tail 40 app || true
  die "The app did not become ready. The last of its log is above."
}

seed() {
  step "Loading the demo school"
  compose exec -T app python game/seed_demo.py "$@" || {
    # Already seeded is not a failure worth stopping for — just show them.
    compose exec -T app python game/seed_demo.py --passwords
  }
}

banner() {
  local base ip port
  base="$(grep -E '^BASE_URL=' .env | cut -d= -f2)"
  port="$(grep -E '^APP_PORT=' .env | cut -d= -f2)"; port="${port:-8000}"
  ip="$(lan_ip)"
  local rule="===================================================================="
  printf '\n%s%s%s\n' "$BOLD" "$rule" "$RESET"
  say "  Open:        ${BOLD}${base}${RESET}"
  say "  On this box: http://localhost:${port}"
  [ "$ip" != "127.0.0.1" ] && say "  From a phone on the same wifi: http://${ip}:${port}"
  printf '%s%s%s\n\n' "$BOLD" "$rule" "$RESET"
  say "  ${DIM}./demo.sh --logins   reprint the accounts"
  say "  ./demo.sh --stop     stop, keeping the data"
  say "  docker compose logs -f app${RESET}"
  say ""
}

main() {
  case "${1:-}" in
    --stop)
      compose down
      say "Stopped. Data kept — ./demo.sh brings it back."
      return 0 ;;
    --fresh)
      warn "Destroying the database volume."
      compose down -v
      rm -f .env
      ;;
    --logins)
      compose exec -T app python game/seed_demo.py --passwords
      banner
      return 0 ;;
    --reset) ;;
    "") ;;
    *) die "Unknown option '$1'. Try --reset, --fresh, --stop or --logins." ;;
  esac

  preflight
  write_env

  step "Building and starting (first run pulls images — a few minutes on a Pi)"
  compose up -d --build

  wait_ready

  if [ "${1:-}" = "--reset" ] || [ "${1:-}" = "--fresh" ]; then
    seed --reset
  else
    seed
  fi

  banner
}

main "$@"
