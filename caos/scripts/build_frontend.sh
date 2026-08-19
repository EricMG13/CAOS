#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(cd "$script_dir/../.." && pwd)"
frontend_dir="$root_dir/caos/frontend"

cd "$frontend_dir"
npm ci
npm run build
mkdir -p "$root_dir/caos/server/static"
cp -R "$frontend_dir/out/." "$root_dir/caos/server/static/."
