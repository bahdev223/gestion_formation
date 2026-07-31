#!/bin/sh
set -eu
MEDIA_PATH="${APP_MEDIA_ROOT:-/app/media}"
STATIC_PATH="${APP_STATIC_ROOT:-/app/static/dist}"
LOG_PATH="/app/logs"

mkdir -p "$MEDIA_PATH" "$STATIC_PATH" "$LOG_PATH"
chown -R django:django "$MEDIA_PATH" "$STATIC_PATH" "$LOG_PATH" || true
chmod -R 775 "$MEDIA_PATH" "$STATIC_PATH" "$LOG_PATH" || true

if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    echo "ERROR: DJANGO_SECRET_KEY is missing."
    echo "Create a secret variable in Coolify before starting Formix."
    exit 1
fi

if [ -z "${DATABASE_URL:-}" ]; then
    missing_database_variables=""
    for variable_name in DB_NAME DB_USER DB_PASSWORD DB_HOST; do
        eval "variable_value=\${$variable_name:-}"
        if [ -z "$variable_value" ]; then
            missing_database_variables="$missing_database_variables $variable_name"
        fi
    done
    if [ -n "$missing_database_variables" ]; then
        echo "ERROR: PostgreSQL is not configured."
        echo "Set DATABASE_URL or provide:$missing_database_variables"
        echo "In Coolify, connect a PostgreSQL resource and map its connection URL."
        exit 1
    fi
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ] || [ "${RUN_MIGRATE:-false}" = "true" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
fi

if [ "${SEED_DEFAULT_PLANS:-true}" = "true" ]; then
    echo "Ensuring default subscription plans..."
    python manage.py seed_plans
fi

if [ "${COLLECT_STATIC:-${RUN_COLLECTSTATIC:-true}}" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

exec "$@"
