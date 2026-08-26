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
