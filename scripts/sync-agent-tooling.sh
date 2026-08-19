#!/usr/bin/env bash
# Sync CAOS agent skills and hooks across Claude, Codex, Cursor, Gemini, and Copilot.
# Canonical skill source: .agents/skills/
set -euo pipefail

ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
AGENTS_SKILLS="$ROOT/.agents/skills"
CLAUDE_SKILLS="$ROOT/.claude/skills"

# Skills with agent-specific variants under .claude/skills/ (do not replace with symlinks).
CLAUDE_LOCAL_SKILLS=(
  commit
  impeccable
  outstanding
  refresh-preview
  gitnexus
)

link_skill() {
  local target_dir="$1"
  local name="$2"
  local dest="$target_dir/$name"
  local src="$AGENTS_SKILLS/$name"

  [[ -d "$src" ]] || return 0
  mkdir -p "$target_dir"

  if [[ -L "$dest" ]]; then
    local current
    current="$(readlink "$dest")"
    if [[ "$current" == "../../.agents/skills/$name" ]]; then
      return 0
    fi
    rm "$dest"
  elif [[ -e "$dest" ]]; then
    return 0
  fi

  local rel="../../.agents/skills/$name"
  ln -s "$rel" "$dest"
  echo "  linked $dest -> $rel"
}

sync_skill_tree() {
  local target_dir="$1"
  local exclude_csv="${2:-}"
  echo "Syncing skills -> $target_dir"
  for name in "$AGENTS_SKILLS"/*/; do
    name="$(basename "$name")"
    [[ "$name" == _* ]] && continue
  if [[ ",$exclude_csv," == *",$name,"* ]]; then
      continue
    fi
    link_skill "$target_dir" "$name"
  done
}

echo "==> Agent tooling sync (root: $ROOT)"

# Claude: keep agent-specific skill copies; symlink the rest.
sync_skill_tree "$CLAUDE_SKILLS" "$(IFS=,; echo "${CLAUDE_LOCAL_SKILLS[*]}")"

# Cursor / Codex / Gemini / Copilot: full mirror of canonical skills.
for dir in \
  "$ROOT/.cursor/skills" \
  "$ROOT/.codex/skills" \
  "$ROOT/.gemini/skills" \
  "$ROOT/.github/skills"; do
  sync_skill_tree "$dir" ""
done

# Shared git safety hook for Codex (single copy under .claude/hooks).
mkdir -p "$ROOT/.codex/hooks"
if [[ ! -e "$ROOT/.codex/hooks/block-dangerous-git.sh" ]] \
  || [[ ! -L "$ROOT/.codex/hooks/block-dangerous-git.sh" ]]; then
  rm -f "$ROOT/.codex/hooks/block-dangerous-git.sh"
  ln -s ../../.claude/hooks/block-dangerous-git.sh "$ROOT/.codex/hooks/block-dangerous-git.sh"
  echo "  linked .codex/hooks/block-dangerous-git.sh -> .claude/hooks/block-dangerous-git.sh"
fi

# Portable Codex PreToolUse hook path (no machine-specific absolute paths).
CODEX_HOOKS="$ROOT/.codex/hooks.json"
if [[ -f "$CODEX_HOOKS" ]]; then
  python3 - "$CODEX_HOOKS" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text())
pre = data.get("hooks", {}).get("PreToolUse", [])
for entry in pre:
    if entry.get("matcher") != "Bash":
        continue
    for hook in entry.get("hooks", []):
        if hook.get("type") == "command":
            hook["command"] = '"$(git rev-parse --show-toplevel)/.codex/hooks/block-dangerous-git.sh"'
path.write_text(json.dumps(data, indent=2) + "\n")
print("  updated .codex/hooks.json PreToolUse path")
PY
fi

# Install / repair Impeccable hook manifests (Cursor, Copilot, Claude local, Codex).
if [[ -f "$AGENTS_SKILLS/impeccable/scripts/hook-admin.mjs" ]]; then
  echo "==> Repairing Impeccable hook manifests"
  node "$AGENTS_SKILLS/impeccable/scripts/hook-admin.mjs" on
fi

echo "==> Done"
