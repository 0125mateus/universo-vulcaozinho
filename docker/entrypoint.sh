#!/bin/sh
set -e

python manage.py collectstatic --noinput

python manage.py migrate --noinput

python manage.py seed_hoteis

if [ "$SEED_DEMO_USERS" != "0" ]; then
  python manage.py seed_superuser
  python manage.py seed_usuarios_demo
fi

if [ "$RUN_SEED" = "1" ]; then
  python manage.py seed_all
fi

exec "$@"