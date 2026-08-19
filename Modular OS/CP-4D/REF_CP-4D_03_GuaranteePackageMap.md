<!-- REF_CP-4D_03 (T2) | PROPOSED | 2026-06-22 -->
<step_reference module="CP-4D" step="03" name="Guarantee Package Map">
<input>T4D.2; guarantor schedule, guarantee provisions, guarantee release mechanics, intercreditor agreement; tranche/debt schedule from CP-1.</input>
<gate>Step 2 complete.</gate>

## Instructions
1. Map which entities guarantee which tranches. Build an entity × tranche matrix.
2. For each guarantee record: type (senior / subordinated / limited), direction (upstream / downstream / cross-stream), and any cap or local-law limitation.
3. Record guarantee **release** triggers (e.g., release on disposal, on designation as unrestricted, on rating event, on covenant fall-away). Flag releases available without full-lender consent.
4. Identify material **non-guarantor** subsidiaries — entities with material assets/EBITDA that do not guarantee — and carry them to Step 5.
5. Note foreign-subsidiary guarantee limitations (e.g., CFC/financial-assistance constraints) where sourced.
6. Apply the Standard Finding Format to each material guarantee provision.

## Output
T4D.3: Guarantor Coverage Matrix (entity × tranche) + non-guarantor material-entity list + release-trigger findings.
</step_reference>
