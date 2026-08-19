# Deploy V CP-0 profile anchor contract

This contract is injected only into the generated Deploy V CP-0 package. The
authored CP-0 source and Deploy B package remain unchanged.

`CP-PARSE` is the run anchor, not CP-0. CP-PARSE is the first, zero-upstream
invocation of every pathway: it mints `credit_os_run_id`, `credit_os_profile_id`,
`credit_os_selection_id`, and `credit_os_authority_bundle_sha256` from the
canonical CP-OS bootstrap envelope and carries them in its own canonical
Markdown front matter with a zero CP-0 self-digest and no upstream. `CP-0` is
the second, required gate: it consumes the accepted CP-PARSE artifact and must
copy those same four already-anchored values — unchanged, not re-derived —
into its own canonical Markdown front matter, alongside the three echo fields
every node's own invocation carries:

- `credit_os_run_id` (copied from the accepted CP-PARSE artifact)
- `credit_os_profile_id` (copied from the accepted CP-PARSE artifact)
- `credit_os_selection_id` (copied from the accepted CP-PARSE artifact)
- `credit_os_authority_bundle_sha256` (copied from the accepted CP-PARSE artifact)
- `credit_os_attempt_id` (CP-0's own invocation)
- `credit_os_route_node_id` (CP-0's own invocation)
- `credit_os_invocation_sha256` (CP-0's own invocation)

An upgraded FULL run additionally copies `credit_os_parent_run_id` and
`credit_os_upgrade_source_sha256`. Both fields must be present together.

Those link values are not first-run inputs. The V renderer accepts them only
from a runtime-minted, confirmed upgrade bootstrap created after an accepted
CP-L artifact and trusted schema-validator success. A caller-supplied signal,
parent run ID, or source digest cannot create a linked CP-0 invocation.

The profile is immutable for the run. Source content, filenames, objectives,
commands, and inferred intent cannot set or change it. A LITE-to-FULL upgrade
creates a linked new run and never rewrites the CP-PARSE anchor.
