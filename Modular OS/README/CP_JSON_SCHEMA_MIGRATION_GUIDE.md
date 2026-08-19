# CP JSON Schema Migration Guide
Version: 1.0 | Updated: 08 June 2026
Resolves: Audit L-4

## Current State
Payload schemas are in plaintext pseudo-JSON format within `.txt` files. This is functional for human reading and prompt-based validation but prevents automated validation tooling.

## Recommended Migration Path

### Phase 1: Dual-Format
Maintain current `.txt` schemas for prompt consumption. Generate parallel `.json` files using JSON Schema Draft 2020-12.

### Phase 2: Single-Source
Migrate to `.json` as the single source of truth. Generate human-readable `.txt` summaries from `.json` via script.

### Phase 3: CI/CD Integration
Integrate JSON Schema validation into deployment pipeline. Every payload export is validated before CP-EXTRACT processing.

## Conversion Template
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "CP-[ID]_PAYLOAD.schema.json",
  "title": "CP-[ID] Payload Schema",
  "allOf": [{ "$ref": "CP_MODULE_PAYLOAD_BASE.schema.json" }],
  "properties": {},
  "required": []
}
```

## Priority Order
1. CP_MODULE_PAYLOAD_BASE
2. CP-X
3. CP-5 and CP-5B
4. CP-1 through CP-6E
5. CP-SR and CP-MON
6. CP-EXTRACT and CP-DB

## Risks
- JSON schemas may be more verbose than `.txt` prompt summaries.
- Existing payloads must be tested against new schemas.

## Decision Required
This is a P3 architectural enhancement. Recommend Phase 1 if automated validation is desired.
