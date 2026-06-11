#!/usr/bin/env bash
set -euo pipefail

echo "==> Waiting for PostgreSQL..."
python <<'PY'
import os, sys, time
try:
    import psycopg2
except ImportError:
    sys.exit(0)
url = os.environ.get("DATABASE_URL", "")
if not url:
    sys.exit(0)
for i in range(30):
    try:
        psycopg2.connect(url)
        print("==> DB ready")
        break
    except psycopg2.OperationalError:
        time.sleep(2)
else:
    print("FATAL: DB not ready after 60s")
    sys.exit(1)
PY

echo "==> migrate"
python manage.py migrate --noinput

echo "==> collectstatic"
python manage.py collectstatic --noinput

echo "==> compilemessages"
python manage.py compilemessages -l uk 2>/dev/null || true
python manage.py compilemessages -l en 2>/dev/null || true

echo "==> seed (idempotent)"
./seed_all.sh

_static_count=$(find "${STATIC_ROOT:-/app/staticfiles}" -type f 2>/dev/null | wc -l | tr -d ' ')
echo "==> static files: ${_static_count}"

exec "$@"
