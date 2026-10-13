#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static..."
python manage.py collectstatic --noinput

# Склейка дублей Steam (можно убрать после одного удачного деплоя)
echo "Fixing steam accounts..."
python manage.py fix_steam_accounts || echo "fix_steam_accounts skipped/failed"

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Creating superuser..."
  python manage.py createsuperuser --noinput \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "$DJANGO_SUPERUSER_EMAIL" 2>/dev/null || echo "Superuser already exists"
fi

echo "Steam snapshot (startup)..."
python manage.py snapshot_steam || echo "snapshot_steam failed"

# Фоновый цикл: снимок каждые 6 часов (update_or_create, дублей за день не будет)
(
  while true; do
    sleep 21600
    echo "Steam snapshot (loop)..."
    python manage.py snapshot_steam || echo "snapshot_steam failed"
  done
) &

echo "Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3