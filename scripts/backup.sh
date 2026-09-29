#!/usr/bin/env bash
#
# backup.sh — nightly logical backup of the Ignite Academy database.
#
#   ./scripts/backup.sh                       # write one dump, prune old ones
#   BACKUP_DIR=/mnt/backups ./scripts/backup.sh
#
# Cron it:
#   15 3 * * *  cd /srv/ignite && ./scripts/backup.sh >> /var/log/ignite-backup.log 2>&1
#
# THIS IS THE FLOOR, NOT THE CEILING. A nightly dump on the same machine
# survives "someone dropped a table"; it does not survive losing the
# machine. Ship these somewhere else — object storage with versioning —
# and on managed Postgres turn on point-in-time recovery, which recovers
# to the minute instead of to last night.
#
# A backup you have never restored is a hypothesis. See DEPLOY.md for the
# restore drill, and actually run it.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/ignite-${STAMP}.dump"

mkdir -p "$BACKUP_DIR"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not set." >&2
  exit 1
fi

echo "→ dumping to ${OUT}"

# Custom format (-Fc): compressed, and pg_restore can pull out a single
# table from it, which is what you actually want at 2am.
# Written to a .partial and renamed only on success, so an interrupted run
# never leaves a truncated file that looks like a good backup.
pg_dump --dbname="$DATABASE_URL" --format=custom --no-owner --no-privileges \
        --file="${OUT}.partial"
mv "${OUT}.partial" "$OUT"

SIZE="$(du -h "$OUT" | cut -f1)"
echo "→ wrote ${OUT} (${SIZE})"

# Verify the dump is readable before trusting it enough to prune anything.
if ! pg_restore --list "$OUT" > /dev/null 2>&1; then
  echo "!! ${OUT} is not a readable dump — keeping every older backup." >&2
  exit 1
fi
echo "→ verified table of contents"

echo "→ pruning dumps older than ${KEEP_DAYS} days"
find "$BACKUP_DIR" -name 'ignite-*.dump' -type f -mtime "+${KEEP_DAYS}" -print -delete

echo "→ done"
