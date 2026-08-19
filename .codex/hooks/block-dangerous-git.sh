#!/bin/bash
# Blocks destructive git working-tree ops before Claude Code runs them.
# Guards the CAOS parallel-WIP rule: the user edits this tree alongside Claude,
# so reset --hard / clean -f / checkout . / restore . / branch -D can wipe their
# uncommitted work. `git push` is intentionally NOT blocked — push is delegated.
# ponytail: clean pattern is flag-order-independent (`-fd`, `-df`, `-xf` all hit);
#          tighten checkout/restore to the `-- .` forms only if they ever bite.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

DANGEROUS_PATTERNS=(
  "git reset --hard"
  "git clean.*-[a-z]*f"
  "git branch -D"
  "git checkout \."
  "git restore \."
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qE "$pattern"; then
    echo "BLOCKED: '$COMMAND' matches dangerous pattern '$pattern'. The user has prevented you from doing this — ask them to run it manually." >&2
    exit 2
  fi
done

exit 0
