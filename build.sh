#!/usr/bin/env bash
# =============================================================================
# build.sh — Render build hook (запускається при кожному деплої)
# =============================================================================
set -o errexit
set -o nounset
set -o pipefail

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py compilemessages

# ── Сідування даних ───────────────────────────────────────────────────────────
# Якщо задано DATA_ARCHIVE_URL — запускає повний seed_all.sh
# (скачує архів з даними + статичний сід + import_all).
#
# Якщо DATA_ARCHIVE_URL не задано — запускає тільки seed_production
# (статичні дані: пріоритети, команда, орг-ції, секційні сторінки).
# Повторні деплої: обидва варіанти ідемпотентні — вже наявні дані пропускаються.
# ─────────────────────────────────────────────────────────────────────────────
if [[ -n "${DATA_ARCHIVE_URL:-}" ]]; then
    echo "DATA_ARCHIVE_URL задано — запуск повного seed_all.sh …"
    chmod +x seed_all.sh
    ./seed_all.sh
else
    echo "DATA_ARCHIVE_URL не задано — запуск seed_production (статичні дані) …"
    python manage.py seed_production
fi
