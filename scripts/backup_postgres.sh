#!/usr/bin/env bash
# Backup do PostgreSQL (Docker Compose ou variáveis POSTGRES_*).
# Uso: ./scripts/backup_postgres.sh
# Cron diário (VPS): 0 3 * * * /caminho/universo_vulcaozinho/scripts/backup_postgres.sh

set -o errexit

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="$BACKUP_DIR/vulcaozinho_${STAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

POSTGRES_DB="${POSTGRES_DB:-vulcaozinho}"
POSTGRES_USER="${POSTGRES_USER:-vulcaozinho}"

if docker compose ps db --status running >/dev/null 2>&1; then
  docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$FILE"
else
  echo "Container db não está rodando. Defina DATABASE_URL ou suba: docker compose up -d db"
  exit 1
fi

find "$BACKUP_DIR" -name 'vulcaozinho_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete 2>/dev/null || true

echo "Backup salvo: $FILE"
