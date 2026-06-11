#!/usr/bin/env bash
# =============================================================================
# deploy.sh — запустити/оновити проєкт на сервері
#
# Перший деплой (HTTP):
#   bash deploy/docker/deploy.sh
#
# Після certbot (HTTPS):
#   USE_HTTPS=true bash deploy/docker/deploy.sh
#
# Оновлення коду:
#   git pull origin main && bash deploy/docker/deploy.sh
# =============================================================================
set -euo pipefail

USE_HTTPS="${USE_HTTPS:-false}"
COMPOSE_BASE="docker compose -f docker-compose.yml"

if [[ "$USE_HTTPS" == "true" ]]; then
    COMPOSE_CMD="$COMPOSE_BASE -f docker-compose.prod.yml"
    echo "==> Production (HTTPS) mode"
else
    COMPOSE_CMD="$COMPOSE_BASE"
    echo "==> HTTP mode (no SSL)"
fi

echo "==> Freeing host ports 80/443..."
systemctl stop nginx 2>/dev/null || true
systemctl disable nginx 2>/dev/null || true

echo "==> Building and starting containers..."
$COMPOSE_CMD up -d --build

echo "==> Health check..."
for i in $(seq 1 12); do
    if curl -sf http://127.0.0.1/healthz/ > /dev/null 2>&1; then
        echo "==> /healthz/ OK"
        break
    fi
    if [[ $i -eq 12 ]]; then
        echo "FATAL: /healthz/ not responding after 60s"
        $COMPOSE_CMD logs web --tail=50
        exit 1
    fi
    echo "  waiting... ($i/12)"
    sleep 5
done

echo ""
echo "✓ Deploy complete"
echo "  HTTP:  http://$(hostname -I | awk '{print $1}')/"
[[ "$USE_HTTPS" == "true" ]] && echo "  HTTPS: https://testwww.fpsu.org.ua/"
echo ""
echo "  Logs:   docker compose logs -f web"
echo "  Shell:  docker compose exec web python manage.py shell"
echo "  Admin:  docker compose exec web python manage.py createsuperuser"
