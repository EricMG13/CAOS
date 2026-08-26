#!/usr/bin/env bash
set -euo pipefail

GATE="$(cd "$(dirname "$0")" && pwd)/fallow-gate.sh"

git() {
  [ "$1" = diff ] || return 2
  case "$TEST_DIFF" in
    clean) [ "$*" = "diff --quiet HEAD" ] && return 0 ;;
    dirty) [ "$*" = "diff --quiet HEAD" ] && return 1 ;;
  esac
  return 2
}

fallow() {
  case "$1" in
    --version) printf '%s\n' 'fallow 2.85.0' ;;
    audit)
      case "$TEST_MODE" in
        commit) [[ " $* " == *' --changed-since HEAD '* && " $* " != *' --diff-stdin '* ]] || return 1 ;;
        push) [[ " $* " != *' --changed-since HEAD '* ]] || return 1 ;;
        clean) return 1 ;;
      esac
      printf '%s\n' '{"verdict":"pass"}'
      ;;
    *) return 1 ;;
  esac
}

run_gate() {
  printf '{"tool_input":{"command":"%s"}}\n' "$1" | "$GATE"
}

export -f git fallow
TEST_DIFF=dirty TEST_MODE=commit run_gate 'git commit -am gate-test'
TEST_DIFF=clean TEST_MODE=clean run_gate 'git commit -m empty'
TEST_DIFF=dirty TEST_MODE=push run_gate 'git commit -m gate-test && git push origin codex/fix'

# Target-dir detection: `git -C <dir>` and a leading `cd <dir> &&` must both
# audit <dir>, not the gate's own cwd — and `-C` must still be recognized as
# a push by the top-level filter (an empty evidence file means it wasn't).
assert_ran_in() {
  local evidence="$1" expected="$2" label="$3"
  local seen; seen="$(cat "$evidence" 2>/dev/null || true)"
  [ "$seen" = "$expected" ] || { echo "FAIL ($label): fallow ran in [$seen], expected [$expected]" >&2; exit 1; }
}

TARGET_C="$(mktemp -d)"; export EVIDENCE_C="$(mktemp)"
fallow() {
  case "$1" in
    --version) printf '%s\n' 'fallow 2.85.0' ;;
    audit) printf '%s' "$PWD" >"$EVIDENCE_C"; printf '%s\n' '{"verdict":"pass"}' ;;
    *) return 1 ;;
  esac
}
export -f fallow
run_gate "git -C $TARGET_C push origin main"
assert_ran_in "$EVIDENCE_C" "$TARGET_C" "git -C"
rm -f "$EVIDENCE_C"; rmdir "$TARGET_C"

TARGET_CD="$(mktemp -d)"; export EVIDENCE_CD="$(mktemp)"
fallow() {
  case "$1" in
    --version) printf '%s\n' 'fallow 2.85.0' ;;
    audit) printf '%s' "$PWD" >"$EVIDENCE_CD"; printf '%s\n' '{"verdict":"pass"}' ;;
    *) return 1 ;;
  esac
}
export -f fallow
run_gate "cd $TARGET_CD && git push origin main"
assert_ran_in "$EVIDENCE_CD" "$TARGET_CD" "cd-prefix"
rm -f "$EVIDENCE_CD"; rmdir "$TARGET_CD"

echo "fallow-gate.test.sh: all checks passed" >&2
