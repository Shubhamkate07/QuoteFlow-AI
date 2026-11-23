#!/bin/bash
# ==============================================================================
# QuoteFlow AI - PostgreSQL Database Restore Script
# ==============================================================================
# Usage:
#   ./scripts/restore_db.sh /path/to/quoteflow_db_YYYYMMDD_HHMMSS.sql.gz
# ==============================================================================

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file '${BACKUP_FILE}' does not exist!" >&2
    exit 1
fi

PGHOST="${DB_HOST:-localhost}"
PGPORT="${DB_PORT:-5432}"
PGUSER="${DB_USER:-${POSTGRES_USER:-postgres}}"
PGDATABASE="${DB_NAME:-${POSTGRES_DB:-quoteflow_db}}"
export PGPASSWORD="${DB_PASSWORD:-${POSTGRES_PASSWORD:-postgres_secure_password}}"

echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] WARNING: Restoring will overwrite existing data in '${PGDATABASE}'!"
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore aborted by user."
    exit 0
fi

echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] Restoring database from '${BACKUP_FILE}'..."

# Uncompress and pipe into pg_restore
gunzip -c "${BACKUP_FILE}" | pg_restore -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" --clean --if-exists -v

echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] Database restore finished successfully."
