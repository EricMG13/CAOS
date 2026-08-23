#!/usr/bin/env sh
set -eu
umask 077
out="${1:?backup destination required}"
mkdir -p "$out"
out_path=$(CDPATH= cd -- "$out" && pwd)
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
lock_dir="$out/.caos-backup.lock"
if ! mkdir "$lock_dir"; then
    echo "backup already running or lock requires operator review: $lock_dir" >&2
    exit 75
fi
dump_tmp=""
vault_tmp=""
manifest_tmp=""
cleanup() {
    rm -f -- "$dump_tmp" "$vault_tmp" "$manifest_tmp"
    rmdir "$lock_dir" 2>/dev/null || true
}
trap cleanup EXIT
dump_tmp=$(mktemp "$out/.caos.dump.XXXXXX")
compose() {
    docker compose -f "$script_dir/docker-compose.yml" "$@"
}
compose exec -T db pg_dump -U caos -d caos --format=custom > "$dump_tmp"
test -s "$dump_tmp"
project_name=${COMPOSE_PROJECT_NAME:-deploy}
vault_volume=$(docker volume ls -q --filter "label=com.docker.compose.project=$project_name" --filter "label=com.docker.compose.volume=vault-data" | head -n 1)
test -n "$vault_volume"
vault_tmp=$(mktemp "$out/.vault.tgz.XXXXXX")
docker run --rm -v "$vault_volume:/vault:ro" alpine:3.20 tar -C /vault -czf - . > "$vault_tmp"
test -s "$vault_tmp"
manifest_tmp=$(mktemp "$out/.caos.backup.manifest.XXXXXX")
{
    printf 'caos.dump %s\n' "$(cksum < "$dump_tmp")"
    printf 'vault.tgz %s\n' "$(cksum < "$vault_tmp")"
} > "$manifest_tmp"
mv -f -- "$dump_tmp" "$out/caos.dump"
mv -f -- "$vault_tmp" "$out/vault.tgz"
mv -f -- "$manifest_tmp" "$out/caos.backup.manifest"
echo "backup written to $out_path"
