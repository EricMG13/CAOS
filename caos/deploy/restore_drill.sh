#!/usr/bin/env sh
set -eu
dump_path="${1:?dump path required}"
test -s "$dump_path"
dump_dir=$(CDPATH= cd -- "$(dirname -- "$dump_path")" && pwd)
vault_archive=${2:-$dump_dir/vault.tgz}
test -s "$vault_archive"
vault_dir=$(CDPATH= cd -- "$(dirname -- "$vault_archive")" && pwd)
vault_name=$(basename -- "$vault_archive")

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
drill_db=${RESTORE_DRILL_DB:-caos_restore_drill}
drill_volume=${RESTORE_DRILL_VOLUME:-caos_restore_vault}
case "$drill_db" in
    ""|caos|postgres|template0|template1|*[!A-Za-z0-9_]* )
        echo "RESTORE_DRILL_DB must be a safe isolated database name" >&2
        exit 2
        ;;
esac
case "$drill_volume" in
    ""|caos_vault-data|*[!A-Za-z0-9_-]* )
        echo "RESTORE_DRILL_VOLUME must be a safe isolated volume name" >&2
        exit 2
        ;;
esac

compose() {
    docker compose -f "$script_dir/docker-compose.yml" "$@"
}
cleanup() {
    compose exec -T db dropdb -U caos --if-exists "$drill_db" >/dev/null 2>&1 || true
    docker volume rm "$drill_volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker volume create "$drill_volume" >/dev/null
docker run --rm -i -v "$drill_volume:/vault" alpine:3.20 tar -xzf - -C /vault < "$vault_archive"
docker run --rm -v "$drill_volume:/vault:ro" alpine:3.20 sh -c 'test -n "$(find /vault -mindepth 1 -maxdepth 1 -print -quit)"'
compose exec -T db dropdb -U caos --if-exists "$drill_db"
compose exec -T db createdb -U caos "$drill_db"
compose exec -T db pg_restore --exit-on-error --no-owner --no-acl -U caos -d "$drill_db" < "$dump_path"
compose exec -T db psql -v ON_ERROR_STOP=1 -U caos -d "$drill_db" -c "SELECT to_regclass('public.caos_state') IS NOT NULL AS state_table_present;"
echo "restore drill passed for isolated database $drill_db"
