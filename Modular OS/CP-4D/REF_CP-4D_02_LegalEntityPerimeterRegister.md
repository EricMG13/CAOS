<!-- REF_CP-4D_02 (T2) | PROPOSED | 2026-06-22 -->
<step_reference module="CP-4D" step="02" name="Legal Entity Perimeter Register">
<input>T4D.1; credit-agreement / indenture definitions of Restricted Subsidiary, Unrestricted Subsidiary, Guarantor, Material Subsidiary; org chart; subsidiary list (Ex-21); CP-1A ownership facts.</input>
<gate>Step 1 complete and not Blocked.</gate>

## Instructions
1. Build the entity register. For each material legal entity record: name, role (borrower / issuer / holdco / intermediate holdco / restricted subsidiary / unrestricted subsidiary / guarantor / non-guarantor / finance sub / JV), jurisdiction, parent, and ownership %.
2. Record designation status: currently restricted vs unrestricted, and whether the documents permit designating it unrestricted (capacity, not just current state).
3. Where sourced, record material assets / EBITDA / debt held at each entity; mark [Insufficient Information] where not disclosed — do not estimate.
4. Flag entities holding material value **outside** the credit/guarantee group — these are the structural-subordination candidates carried into Step 5.
5. Separate documentary fact (definition, schedule) from analyst interpretation (which entities are economically significant).

## Output
T4D.2: Restricted / Unrestricted Entity Register — `Entity`|`Role`|`Jurisdiction`|`Parent`|`Designation (Restricted/Unrestricted + can-be-designated)`|`Material Value Held`|`Inside Credit Group?`|`Evidence ID`
</step_reference>
