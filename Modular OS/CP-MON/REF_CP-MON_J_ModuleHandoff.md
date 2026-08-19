# REF_CP-MON_J — Module Handoff
Common envelope fields: module_id, run_id, issuer_name, issuer_id, reporting_period, sources, upstream_artifacts, key_claims, evidence_trace, confidence, limitations, qa_status, downstream_consumers, module_payload.

Downstream consumers (orchestration edges, authoritative per SYSTEM_ROUTE_MAP_v2): CP-X, CP-SR, CP-1, CP-3D.

Content-typed signal handoff packets route VIA CP-X to: CP-1B (earnings signals); CP-2B (downside/distress triggers); CP-3 (market/RV signals); CP-4 (legal/covenant alerts); CP-6A (Critical-tier clusters). These are packet recipients, not direct orchestration edges — CP-X owns routing.

Issuer-registry maintenance is CP-MON-internal (SCHEMA_CP-MON_IssuerRegistry); CP-MON does NOT write back to CP-0 (no backward edge). Only the CP-SR<->CP-MON loop is bidirectional. (Audit F-5 resolved.)
