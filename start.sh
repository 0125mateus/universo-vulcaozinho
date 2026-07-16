#!/usr/bin/env bash
# Start script para Render (migrate + seed opcional + Daphne/ASGI)
set -o errexit

mkdir -p media

python manage.py migrate --no-input

# Garante logins demo (não apaga dados operacionais — só cria/atualiza usuários).
python manage.py seed_superuser
python manage.py seed_usuarios_demo

if [ "$RUN_SEED" = "1" ]; then
  python manage.py seed_all
fi

exec daphne -b 0.0.0.0 -p "$PORT" config.asgi:application
