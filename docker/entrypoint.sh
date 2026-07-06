#!/bin/sh
set -e

python manage.py collectstatic --noinput

python manage.py migrate --noinput

if [ "$RUN_SEED" = "1" ]; then
  python manage.py seed_all
fi

exec "$@"