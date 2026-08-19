---
name: commit
description: Commit (and optionally push) the working tree the safe CAOS way — stage only the files Codex touched, never the user's parallel WIP. Use when the user says "commit", "commit the working tree", "commit with a sensible message", "commit and push", "push", or "commit then <next task>".
user-invokable: true
---

# commit

The single most frequent ask in this repo. The user edits the **same working
tree in parallel**, so a blind `git add -A` would sweep up their unfinished WIP.
This skill encodes the staging discipline so that never happens.

## Hard rules

1. **Stage explicit paths only — NEVER `git add -A` / `git add .`.** Add only
   the files Codex created or edited this session.
2. **Branch first if on `main`.** Trunk is `main`; never commit straight to it.
   Create/switch to a feature branch, then commit.
3. **Trailer on every commit message:**
   `Co-Authored-By: Codex Opus 4.8 <noreply@anthropic.com>`
4. **Push only when asked.** "commit" ≠ "push". If the user said push (or
   "commit and push"), push after committing.

## Steps

1. `git status --porcelain` + `git diff --stat` — list every changed path.
2. Split the list: **Codex's files** (touched this session) vs **user's WIP**
   (everything else). When unsure whether a path is Codex's, treat it as the
   user's and leave it.
3. `git add <explicit Codex paths>` — one by one, no globs that catch WIP.
4. Commit with a terse Conventional-Commits subject + the Co-Authored trailer.
5. If push was requested: `git push` (set upstream if the branch is new).
6. **Report the untouched WIP** you deliberately left unstaged, so the user
   knows it's still theirs to handle: `left unstaged (your WIP): <paths>`.

## Don't

- Don't `git commit -a`, don't `git add -A`, don't stage a directory that mixes
  Codex + user files.
- Don't amend or force-push unless explicitly told.
- Don't open a PR unless asked.
