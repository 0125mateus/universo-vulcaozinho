#!/usr/bin/env bash
# Start script para Render (migrate + seed opcional + Daphne/ASGI)
set -o errexit

mkdir -p media

python manage.py migrate --no-input

# Garante hotéis da rede (idempotente; não apaga ponto/hóspedes).
python manage.py seed_hoteis

# Usuários demo só em dev/staging (SEED_DEMO_USERS=0 em produção).
if [ "$SEED_DEMO_USERS" != "0" ]; then
  python manage.py seed_superuser
  python manage.py seed_usuarios_demo
fi

if [ "$RUN_SEED" = "1" ]; then
  python manage.py seed_all
fi

exec daphne -b 0.0.0.0 -p "$PORT" config.asgi:application
