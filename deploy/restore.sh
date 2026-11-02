#!/bin/sh
# Restore only into an existing EMPTY, separate local database ending in _restore.
# Usage: SOURCE_DATABASE=... PGDATABASE=..._restore PGUSER=... [PG_CONTAINER=...] \
#        deploy/restore.sh INPUT.dump
# No --clean/--create: errors roll back the complete restore, never drop existing data.
set -eu
umask 077
[ "$#" -eq 1 ] || { echo 'Usage: restore.sh INPUT.dump' >&2; exit 2; }
: "${PGDATABASE:?Set the destination database}" "${PGUSER:?Set the database user}"
: "${SOURCE_DATABASE:?Identify the backup source database}"
case "$PGDATABASE" in *[!A-Za-z0-9_]*|'') echo 'Use a database name, not a connection URL' >&2; exit 2 ;; esac
[ -r "$1" ] && [ -s "$1" ] || { echo 'Backup must be a readable nonempty file' >&2; exit 2; }
case "$PGDATABASE" in *_restore) ;; *) echo 'Destination must end in _restore' >&2; exit 2 ;; esac
[ "$PGDATABASE" != "$SOURCE_DATABASE" ] || { echo 'Source and destination must differ' >&2; exit 2; }
case "${PGHOST:-}" in
    ''|localhost|127.0.0.1|::1|db) ;;
    *) echo 'Use a separate local destination for restoration verification' >&2; exit 2 ;;
esac

pg_command() {
    # Execute libpq tools with environment credentials; never print connection secrets.
    if [ -n "${PG_CONTAINER:-}" ]; then
        docker exec -i --env PGDATABASE --env PGUSER --env PGHOST --env PGPORT \
            --env PGPASSFILE --env PGPASSWORD "$PG_CONTAINER" "$@"
    else
        "$@"
    fi
}

case "$(pg_command pg_restore --version)" in
    'pg_restore (PostgreSQL) 18.'*) ;;
    *) echo 'PostgreSQL 18 client tools are required' >&2; exit 2 ;;
esac
relations=$(pg_command psql -X -v ON_ERROR_STOP=1 -Atc \
    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_' AND c.relkind IN ('r','p','v','m','S','f')")
[ "$relations" = 0 ] || { echo 'Destination must be empty; nothing was restored' >&2; exit 2; }
pg_command pg_restore --dbname="$PGDATABASE" --exit-on-error --single-transaction --no-owner --no-acl < "$1"
echo 'Restored. Compare evidence, constraints and Alembic revision before switching any application.'
