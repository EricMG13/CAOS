---
name: commit
description: Commit (and optionally push) the working tree the safe CAOS way — stage only the files Claude touched, never the user's parallel WIP. Use when the user says "commit", "commit the working tree", "commit with a sensible message", "commit and push", "push", or "commit then <next task>".
user-invokable: true
---

# commit

The single most frequent ask in this repo. The user edits the **same working
tree in parallel**, so a blind `git add -A` would sweep up their unfinished WIP.
This skill encodes the staging discipline so that never happens.

## Hard rules

1. **Stage explicit paths only — NEVER `git add -A` / `git add .`.** Add only
   the files Claude created or edited this session.
2. **Branch first if on `main`.** Trunk is `main`; never commit straight to it.
   Create/switch to a feature branch, then commit.
3. **Trailer on every commit message:** use the trailer the running harness
   specifies for the current model — do not hardcode a model version here, it
   goes stale (this line used to pin 4.8).
4. **Push only when asked.** "commit" ≠ "push". If the user said push (or
   "commit and push"), push after committing.
5. **Cut new branches from `origin/main`, never from local `main`.** Local
   `main` is routinely tens of commits stale, and a branch cut from it is born
   behind. `git fetch origin && git switch -c <name> origin/main`.
6. **A commit is not the finish line.** Unmerged branches are the single
   biggest source of pain in this repo: they rot at roughly the rate main
   moves, and a branch tens of commits behind is a conflict waiting to happen.
   Before starting new work, check `caos/scripts/git_rot.sh` and land or close
   what is already open.

## Steps

1. `git status --porcelain` + `git diff --stat` — list every changed path.
2. Split the list: **Claude's files** (touched this session) vs **user's WIP**
   (everything else). When unsure whether a path is Claude's, treat it as the
   user's and leave it.
3. `git add <explicit Claude paths>` — one by one, no globs that catch WIP.
4. Commit with a terse Conventional-Commits subject + the Co-Authored trailer.
5. If push was requested: `git push` (set upstream if the branch is new).
6. **Report the untouched WIP** you deliberately left unstaged, so the user
   knows it's still theirs to handle: `left unstaged (your WIP): <paths>`.

## Landing it (when the user says push / open a PR / merge)

Rebase before you push. `git fetch origin && git rebase origin/main` — a PR
opened from a stale base is red on arrival, and CI failures you did not cause
are indistinguishable from ones you did.

Then push, and say plainly whether the PR is landable or needs a follow-up. Do
not open a PR and walk away: an abandoned PR is worse than no PR, because it
looks like progress while it rots. If the work is not going to land now, say so
and leave the branch unpushed instead.

## Don't

- Don't `git commit -a`, don't `git add -A`, don't stage a directory that mixes
  Claude + user files.
- Don't amend or force-push unless explicitly told.
- Don't open a PR unless asked.
- Don't open a new branch for work that belongs on one already open — check
  `caos/scripts/git_rot.sh` first.
