#!/usr/bin/env sh
set -eu
dump_path="${1:?dump path required}"
test -s "$dump_path"
dump_dir=$(CDPATH= cd -- "$(dirname -- "$dump_path")" && pwd)
vault_archive=${2:-$dump_dir/vault.tgz}
test -s "$vault_archive"
standard_pair=0
if [ "$(basename -- "$dump_path")" = "caos.dump" ] && [ "$(basename -- "$vault_archive")" = "vault.tgz" ] && [ "$(CDPATH= cd -- "$(dirname -- "$vault_archive")" && pwd)" = "$dump_dir" ]; then
    standard_pair=1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
drill_db=${RESTORE_DRILL_DB:-caos_restore_drill}
drill_volume=${RESTORE_DRILL_VOLUME:-caos_restore_vault}
is_safe_name() {
    case "$1" in
        *[!A-Za-z0-9_-]*) return 1 ;;
        *) return 0 ;;
    esac
}
case "$drill_db" in
    caos_restore_drill|caos_restore_drill_*)
        is_safe_name "$drill_db" || {
            echo "RESTORE_DRILL_DB must contain only safe name characters" >&2
            exit 2
        }
        ;;
    * )
        echo "RESTORE_DRILL_DB must be a safe isolated database name" >&2
        exit 2
        ;;
esac
case "$drill_volume" in
    caos_restore_vault|caos_restore_vault_*)
        is_safe_name "$drill_volume" || {
            echo "RESTORE_DRILL_VOLUME must contain only safe name characters" >&2
            exit 2
        }
        ;;
    * )
        echo "RESTORE_DRILL_VOLUME must be a safe isolated volume name" >&2
        exit 2
        ;;
esac

compose() {
    docker compose -f "$script_dir/docker-compose.yml" "$@"
}

if docker volume inspect "$drill_volume" >/dev/null 2>&1; then
    echo "RESTORE_DRILL_VOLUME must not already exist" >&2
    exit 2
fi
if ! existing_db=$(compose exec -T db psql -Atq -U caos -d postgres -c "SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = '$drill_db');"); then
    echo "could not verify RESTORE_DRILL_DB" >&2
    exit 2
fi
case "$existing_db" in
    f) ;;
    t)
        echo "RESTORE_DRILL_DB must not already exist" >&2
        exit 2
        ;;
    *)
        echo "could not verify RESTORE_DRILL_DB" >&2
        exit 2
        ;;
esac

if [ "$standard_pair" -eq 1 ]; then
    manifest="$dump_dir/caos.backup.manifest"
    if ! test -s "$manifest"; then
        echo "standard backup pair requires caos.backup.manifest" >&2
        exit 2
    fi
    expected_dump=$(sed -n 's/^caos\.dump //p' "$manifest")
    expected_vault=$(sed -n 's/^vault\.tgz //p' "$manifest")
    if [ "$expected_dump" != "$(cksum < "$dump_path")" ] || [ "$expected_vault" != "$(cksum < "$vault_archive")" ]; then
        echo "backup manifest does not match dump and vault pair" >&2
        exit 2
    fi
fi

volume_created=0
db_created=0
drill_token="$(date +%s)-$$"
cleanup() {
    if [ "$db_created" -eq 1 ]; then
        compose exec -T db dropdb -U caos --if-exists "$drill_db" >/dev/null 2>&1 || true
    fi
    if [ "$volume_created" -eq 1 ]; then
        docker volume rm "$drill_volume" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

docker volume create "$drill_volume" >/dev/null
docker run --rm -v "$drill_volume:/vault" alpine:3.20 sh -c 'set -C; printf "%s\\n" "$1" > /vault/.caos-restore-drill-owner' sh "$drill_token"
volume_created=1
docker run --rm -i -v "$drill_volume:/vault" alpine:3.20 tar -xzf - -C /vault < "$vault_archive"
docker run --rm -v "$drill_volume:/vault:ro" alpine:3.20 sh -c 'test -n "$(find /vault -mindepth 1 -maxdepth 1 -print -quit)"'
compose exec -T db createdb -U caos "$drill_db"
db_created=1
compose exec -T db pg_restore --exit-on-error --no-owner --no-acl -U caos -d "$drill_db" < "$dump_path"
compose exec -T db psql -v ON_ERROR_STOP=1 -U caos -d "$drill_db" -c "SELECT to_regclass('public.caos_state') IS NOT NULL AS state_table_present;"
echo "restore drill passed for isolated database $drill_db"
