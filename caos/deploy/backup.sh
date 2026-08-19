#!/usr/bin/env sh
set -eu
umask 077
out="${1:?backup destination required}"
mkdir -p "$out"
out_path=$(CDPATH= cd -- "$out" && pwd)
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
compose() {
    docker compose -f "$script_dir/docker-compose.yml" "$@"
}
compose exec -T db pg_dump -U caos -d caos --format=custom > "$out/caos.dump"
project_name=${COMPOSE_PROJECT_NAME:-deploy}
vault_volume=$(docker volume ls -q --filter "label=com.docker.compose.project=$project_name" --filter "label=com.docker.compose.volume=vault-data" | head -n 1)
test -n "$vault_volume"
docker run --rm -v "$vault_volume:/vault:ro" alpine:3.20 tar -C /vault -czf - . > "$out/vault.tgz"
echo "backup written to $out_path"
