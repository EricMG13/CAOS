# Deploy V

Deploy V provides 22 physical skills for enterprise leveraged-finance credit analysis and governed publication.

## Deployment

Folder grounding via a saved Copilot memory prompt, not native Cowork install -- ground a conversation on this package's root folder (the one directly containing `skills/`, `CANON_SHARED.md`, and the retrieval index), then follow `DEPLOY_V_COPILOT_MEMORY_PROMPT.md`.

## Verify

This is the distributed package; the build system and its test suite are not shipped inside it. To check that a copy of this package is intact, recompute each file's sha256 and compare against `DEPLOY_V_INTEGRITY_v1.json` (per-file hashes, `relative_file_hashes`) and `DEPLOY_V_BASELINE.json` (`baseline_digest`). The `build_id` in `CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json` must match `DEPLOY_V_INTEGRITY_v1.json` and the `INDEX_BUILD_ID` quoted in both memory prompts.

## Contents

22 physical skills under `skills/`. `CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json` is the retrieval authority and carries routing fields only -- module IDs, aliases and entry paths -- because it is read on every dispatch; per-file hashes live beside it in `DEPLOY_V_INTEGRITY_v1.json`. `DEPLOY_V_MANIFEST.json` and `DEPLOY_V_BASELINE.json` are regenerated from this exact tree.
