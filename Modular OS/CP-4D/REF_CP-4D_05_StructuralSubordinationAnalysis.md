<!-- REF_CP-4D_05 (T2) | PROPOSED | 2026-06-22 -->
<step_reference module="CP-4D" step="05" name="Structural Subordination Analysis">
<input>T4D.2–T4D.4; CP-1 debt-by-entity schedule; non-guarantor material-entity list from Step 3.</input>
<gate>Step 4 complete.</gate>

## Instructions
1. Identify structural gaps: debt or claims sitting at entities whose value is not reachable by creditors of another entity (opco/holdco subordination, non-guarantor value, finance-sub conduits).
2. For each tranche / creditor class, assign a Structural-Priority Label: Structurally Senior | Pari (same entity, same lien) | Structurally Subordinated — Non-Guarantor Value | Contractually Subordinated | Leakage-Exposed (drop-down capable) | Priming-Exposed (uptier capable) | Insufficient Information.
3. For every structural-subordination finding, **name the entity gap and the unguaranteed / unsecured value it strands** — a label without a named stranded value is not a finding.
4. Rank claims by structural position by entity, not just by stated lien — a 1L lien at a value-empty entity ranks behind unsecured debt at the operating entity.
5. Apply the Standard Finding Format. Translate each gap into a recovery-access implication (qualitative).

## Output
T4D.5: Structural Priority Table — `Claim / Tranche`|`Obligor Entity`|`Reachable Value`|`Structural-Priority Label`|`Stranded Value Named`|`Recovery-Access Implication`|`Confidence`|`Evidence ID`
</step_reference>
