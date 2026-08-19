<!-- REF_CP-4D_06 (T2) | PROPOSED | 2026-06-22 -->
<step_reference module="CP-4D" step="06" name="Leakage-Route Register">
<input>T4D.2–T4D.5; CP-4 findings on restricted payments, investments, asset transfers, and unrestricted-subsidiary capacity; basket definitions; designation provisions.</input>
<gate>Step 5 complete.</gate>

## Instructions
1. Enumerate asset-leakage routes out of the credit group. Standard routes: (a) drop-down via investment / RP capacity into an unrestricted subsidiary; (b) asset sale or contribution out of the group; (c) designation of a restricted subsidiary as unrestricted; (d) transfer to a non-guarantor.
2. For each route record: entity path, **enabling provision** (cite the CP-4 finding ID — do not re-derive covenant terms here), value exposed, and recovery/priority implication.
3. Score each route on Leakage-Route Severity (1 Sealed · 2 Bounded · 3 Market-Standard · 4 Open · 5 Trapdoor). Score only where document-level capacity evidence supports it; else [Not Scorable].
4. Separate demonstrated/used capacity from theoretical capacity.
5. If a CP-4 enabling finding is unavailable, mark the route [Insufficient Information] — do not assume capacity.

## Output
T4D.6: Drop-down / Transfer Capacity Register — `Route`|`Entity Path`|`Enabling Provision (CP-4 ref)`|`Value Exposed`|`Severity (1–5)`|`Recovery / Priority Implication`|`Demonstrated vs Theoretical`|`Evidence ID`
</step_reference>
