#!/bin/sh
# ==============================================================================
# QuoteFlow AI - Backend Container Entrypoint
# ==============================================================================
# Ensures database readiness, applies database migrations, collects static assets,
# and hands off execution to the specified command.
# ==============================================================================

set -e

# If running against PostgreSQL, wait until the database port is accepting connections
if [ "$USE_SQLITE" != "True" ] && [ "$USE_SQLITE" != "true" ] && [ -n "$DB_HOST" ]; then
  echo "==> Checking PostgreSQL readiness at $DB_HOST:${DB_PORT:-5432}..."
  
  # Use netcat (nc) to poll the DB port
  until nc -z -v -w30 "$DB_HOST" "${DB_PORT:-5432}"; do
    echo "==> PostgreSQL is not ready yet. Waiting 1 second..."
    sleep 1
  done
  
  echo "==> PostgreSQL is reachable and ready."
fi

# Run Django migrations (enabled by default for backend, disabled for celery workers)
if [ "${RUN_MIGRATIONS:-true}" = "true" ] || [ "${RUN_MIGRATIONS:-true}" = "True" ]; then
  echo "==> Applying database migrations..."
  python manage.py migrate --noinput
  echo "==> Database migrations applied successfully."
fi

# Collect static files if requested
if [ "${COLLECT_STATIC:-false}" = "true" ] || [ "${COLLECT_STATIC:-false}" = "True" ]; then
  echo "==> Collecting static assets..."
  python manage.py collectstatic --noinput
  echo "==> Static assets collected."
fi

echo "==> Launching container process: $@"
exec "$@"
