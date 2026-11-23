#!/bin/bash
# ==============================================================================
# QuoteFlow AI - Automated PostgreSQL Backup Script
# ==============================================================================
# Usage:
#   ./scripts/backup_db.sh
# Cron Schedule Example (daily at 02:00 AM):
#   0 2 * * * /opt/quoteflow/scripts/backup_db.sh >> /var/log/quoteflow_backup.log 2>&1
# ==============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups/postgresql}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/quoteflow_db_${TIMESTAMP}.sql.gz"

# Database Credentials (defaults to Docker Compose service name or env)
PGHOST="${DB_HOST:-localhost}"
PGPORT="${DB_PORT:-5432}"
PGUSER="${DB_USER:-${POSTGRES_USER:-postgres}}"
PGDATABASE="${DB_NAME:-${POSTGRES_DB:-quoteflow_db}}"
export PGPASSWORD="${DB_PASSWORD:-${POSTGRES_PASSWORD:-postgres_secure_password}}"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] Starting database backup for '${PGDATABASE}' on host '${PGHOST}'..."

# Execute pg_dump with gzip compression
if pg_dump -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -F c -b -v "${PGDATABASE}" | gzip -c > "${BACKUP_FILE}"; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] SUCCESS: Backup created at '${BACKUP_FILE}' (Size: ${BACKUP_SIZE})"
else
    echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] ERROR: pg_dump failed!" >&2
    exit 1
fi

# Rotate old backups
echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] Purging backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "quoteflow_db_*.sql.gz" -mtime +"${RETENTION_DAYS}" -delete

echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] Backup workflow completed successfully."
