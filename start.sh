#!/usr/bin/env bash
# Start script para Render (migrate + seed opcional + Daphne/ASGI)
set -o errexit

python manage.py migrate --no-input

if [ "$RUN_SEED" = "1" ]; then
  python manage.py seed_all
fi

exec daphne -b 0.0.0.0 -p "$PORT" config.asgi:application
