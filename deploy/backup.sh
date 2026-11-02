#!/bin/sh
# Create a PostgreSQL 18 custom-format backup, atomically and without overwriting files.
# Usage: PGDATABASE=... PGUSER=... [PG_CONTAINER=...] deploy/backup.sh OUTPUT.dump
# Credentials use libpq env/PGPASSFILE; they are never accepted as command-line URLs.
set -eu
umask 077
[ "$#" -eq 1 ] || { echo 'Usage: backup.sh OUTPUT.dump' >&2; exit 2; }
: "${PGDATABASE:?Set the source database}" "${PGUSER:?Set the database user}"
case "$PGDATABASE" in *[!A-Za-z0-9_]*|'') echo 'Use a database name, not a connection URL' >&2; exit 2 ;; esac
target=$1
[ ! -e "$target" ] || { echo 'Backup target already exists' >&2; exit 2; }

pg_command() {
    # Run PostgreSQL tools locally or inside an explicitly chosen existing DB container.
    # Forward libpq environment names, including secrets, without printing their values.
    if [ -n "${PG_CONTAINER:-}" ]; then
        docker exec -i --env PGDATABASE --env PGUSER --env PGHOST --env PGPORT \
            --env PGPASSFILE --env PGPASSWORD "$PG_CONTAINER" "$@"
    else
        "$@"
    fi
}

case "$(pg_command pg_dump --version)" in
    'pg_dump (PostgreSQL) 18.'*) ;;
    *) echo 'PostgreSQL 18 client tools are required' >&2; exit 2 ;;
esac
temporary=$(mktemp -d "${target}.tmp.XXXXXX")
# Only remove files inside the private directory allocated by this invocation.
trap 'rm -f "$temporary/archive.dump"; rmdir "$temporary"' EXIT
trap 'exit 1' HUP INT TERM
pg_command pg_dump --format=custom --no-owner --no-acl > "$temporary/archive.dump"
pg_command pg_restore --list < "$temporary/archive.dump" > /dev/null
# A hard link is an atomic non-overwriting publication on the same filesystem.
ln "$temporary/archive.dump" "$target"
echo 'Backup created; store it encrypted outside the application host.'
