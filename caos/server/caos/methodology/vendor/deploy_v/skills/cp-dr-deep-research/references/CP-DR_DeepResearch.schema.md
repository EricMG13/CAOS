# CP-DR | Deep Research Contract Schema
# Version: 1.0 | 2026-07-21

## Identity

| Field | Value |
|---|---|
| module_id | CP-DR |
| module_name | DeepResearch |
| module_type | Analytical — issuer or sector research |
| owned_object | research_dossier |
| layer | L7 |

## Required input

`scope_type`, `scope_key`, `subject_name`, `research_question`, `decision_context`, `as_of_date`, `time_horizon`, `exclusions`, `source_mode`, `freshness_requirement`, `research_budget`, and `plan_approval`. CP-0 is optional advisory input.

## Required output-envelope extension

| Field | Type / enum |
|---|---|
| scope_type | `issuer` or `sector` |
| scope_key | non-empty scalar used in filenames |
| subject_name | non-empty string |
| research_question | non-empty string |
| source_mode | `supplied_only`, `web_only`, or `hybrid` |
| approved_plan_hash | `sha256:` plus 64 lowercase hex characters |
| coverage_score | integer 0–100 |
| research_status | `Complete`, `Complete with Gaps`, or `Blocked` |
| research_stop_reason | `coverage_satisfied`, `budget_exhausted`, `sources_exhausted`, `blocked`, or `user_stopped` |

For issuer scope, `issuer_name` and `issuer_id` may also be supplied. They are not required for sector scope. `qa_status: Blocked` remains the fail-closed projection gate and caps confidence at 39.

## Artifacts

| Artifact | Filename | Rule |
|---|---|---|
| canonical Markdown handoff | `[ScopeKey]_CP-DR_[YYYYMMDD].md` | Sole analytical output; author and validate fail-closed |

The handoff uses the six canonical H2 headings. New CP-SR outputs are prohibited; prior CP-SR reports may appear only in the source registry with historical provenance.

## Routing

Optional upstream: CP-0 and user-supplied sources. Downstream analytical handoffs: CP-X, CP-1, CP-2, CP-5A, CP-6 and CP-6A.
