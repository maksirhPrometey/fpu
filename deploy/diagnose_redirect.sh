#!/bin/sh
# Run on the FreeBSD server as root to trace HTTP 301 sources.
set -eu

echo "=== 1. Disk / listeners ==="
df -h /
sockstat -4 -l | grep ':80 \|:443 ' || true

echo ""
echo "=== 2. nginx active config (return/rewrite) ==="
nginx -T 2>/dev/null | grep -inE 'return 301|rewrite.*https|listen 80|listen 443|server_name|well-known' || true

echo ""
echo "=== 3. fpu.conf on disk ==="
cat /usr/local/etc/nginx/fpu.conf 2>/dev/null || echo "MISSING fpu.conf"

echo ""
echo "=== 4. sites-enable (should be empty) ==="
ls -la /usr/local/etc/nginx/sites-enable/ 2>/dev/null || true

echo ""
echo "=== 5. Let's Encrypt cert SAN ==="
if [ -f /usr/local/etc/letsencrypt/live/fpsu.org.ua/fullchain.pem ]; then
    openssl x509 -in /usr/local/etc/letsencrypt/live/fpsu.org.ua/fullchain.pem -noout -text | grep DNS || true
else
    echo "No fpsu.org.ua cert"
fi

echo ""
echo "=== 6. Bypass nginx → gunicorn ==="
curl -s -o /dev/null -w "gunicorn healthz: %{http_code}\n" http://127.0.0.1:8001/healthz/ || echo "gunicorn down"

echo ""
echo "=== 7. nginx localhost (Host: testwww) ==="
echo test > /var/www/letsencrypt/.well-known/acme-challenge/test 2>/dev/null || true
curl -s -o /dev/null -w "acme via nginx: %{http_code}\n" \
  -H "Host: testwww.fpsu.org.ua" \
  http://127.0.0.1/.well-known/acme-challenge/test || true
curl -sI -H "Host: testwww.fpsu.org.ua" http://127.0.0.1/healthz/ | head -5

echo ""
echo "=== 8. Public hostname ==="
host testwww.fpsu.org.ua 2>/dev/null || true
curl -s -o /dev/null -w "public acme: %{http_code}\n" \
  http://testwww.fpsu.org.ua/.well-known/acme-challenge/test || true
curl -sI http://testwww.fpsu.org.ua/healthz/ | head -8

echo ""
echo "=== 9. Django settings (if venv exists) ==="
if [ -f /mnt_data/fpsu/manage.py ]; then
    cd /mnt_data/fpsu
    . venv/bin/activate 2>/dev/null || true
    python manage.py shell -c "
from django.conf import settings
print('SETTINGS_MODULE=', settings.SETTINGS_MODULE)
print('SECURE_SSL_REDIRECT=', getattr(settings, 'SECURE_SSL_REDIRECT', None))
print('SECURE_PROXY_SSL_HEADER=', getattr(settings, 'SECURE_PROXY_SSL_HEADER', None))
" 2>/dev/null || echo "manage.py shell failed"
fi

echo ""
echo "=== done ==="
