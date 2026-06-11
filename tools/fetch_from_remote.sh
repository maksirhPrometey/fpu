#!/usr/bin/env bash
# =============================================================================
# fetch_from_remote.sh — стягнути актуальні дані з Joomla-сервера fpsu.org.ua
#
# Кроки:
#   1. mysqldump на віддаленому сервері → tools/fpsu_full_dump.sql
#   2. extract_tsv.py → cats/articles/menu/content_bodies + gallery JSON
#   3. import_all --skip-images → оновлення БД Django
#   4. (опційно) rsync зображень з /sites/www.fpsu.org.ua/images/
#
# Env (опційно, є defaults):
#   SSH_HOST   (default: 78.27.236.224)
#   SSH_PORT   (default: 9092)
#   SSH_USER   (default: root)
#   SSH_KEY    (default: ./key_dig_priv.pem)
#   SKIP_RSYNC (default: 0; set 1 to skip image sync)
#
# Usage:
#   ./tools/fetch_from_remote.sh
#   SKIP_RSYNC=1 ./tools/fetch_from_remote.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

SSH_HOST="${SSH_HOST:-78.27.236.224}"
SSH_PORT="${SSH_PORT:-9092}"
SSH_USER="${SSH_USER:-root}"
SSH_KEY="${SSH_KEY:-$ROOT/key_dig_priv.pem}"
REMOTE_IMAGES="${REMOTE_IMAGES:-/sites/www.fpsu.org.ua/images/}"
LOCAL_IMAGES="${LOCAL_IMAGES:-$ROOT/media/joomla_images/images/}"
SKIP_RSYNC="${SKIP_RSYNC:-0}"

SSH=(ssh -p "$SSH_PORT" -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=20 "${SSH_USER}@${SSH_HOST}")
SCP=(scp -P "$SSH_PORT" -i "$SSH_KEY")

log()  { echo ""; echo "  [fetch] $*"; }
ok()   { echo "  ✓  $*"; }
fail() { echo "  ✗  $*" >&2; exit 1; }

[[ -f "$SSH_KEY" ]] || fail "SSH key not found: $SSH_KEY"

log "Upload dump scripts …"
"${SCP[@]}" "$SCRIPT_DIR/_server_dump2.py" "${SSH_USER}@${SSH_HOST}:/tmp/_server_dump2.py"
"${SCP[@]}" "$SCRIPT_DIR/_remote_run_dump.sh" "${SSH_USER}@${SSH_HOST}:/tmp/_remote_run_dump.sh"

log "MySQL dump on remote …"
"${SSH[@]}" 'sh /tmp/_remote_run_dump.sh'

log "Download dump ($(du -sh /tmp/fpsu_full_dump.sql 2>/dev/null || echo remote) on server) …"
"${SCP[@]}" "${SSH_USER}@${SSH_HOST}:/tmp/fpsu_full_dump.sql" "$SCRIPT_DIR/fpsu_full_dump.sql"
ok "Saved $SCRIPT_DIR/fpsu_full_dump.sql ($(du -sh "$SCRIPT_DIR/fpsu_full_dump.sql" | cut -f1))"

log "Extract TSV / JSON …"
python3 "$SCRIPT_DIR/extract_tsv.py" --sql "$SCRIPT_DIR/fpsu_full_dump.sql"

log "Copy to tools/data/ …"
cp "$SCRIPT_DIR/cats.tsv" "$SCRIPT_DIR/articles.tsv" "$SCRIPT_DIR/menu.tsv" \
   "$SCRIPT_DIR/content_bodies.json" "$SCRIPT_DIR/data/"
ok "tools/data/ updated"

log "Import into Django (import_all --skip-images) …"
python3 manage.py import_all --skip-images

log "Link article covers …"
python3 manage.py link_article_covers --skip-missing

if [[ "$SKIP_RSYNC" != "1" ]]; then
  log "Sync images (rsync --update, may take a long time) …"
  mkdir -p "$LOCAL_IMAGES"
  rsync -avz --update \
    -e "ssh -p $SSH_PORT -i $SSH_KEY" \
    "${SSH_USER}@${SSH_HOST}:${REMOTE_IMAGES}" \
    "$LOCAL_IMAGES"
  ok "Images synced to $LOCAL_IMAGES"
else
  log "SKIP_RSYNC=1 — image sync skipped"
fi

ok "fetch_from_remote.sh complete"
