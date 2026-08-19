<!-- REF_CP-1_02_EntityPeriodScope (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="2" name="Entity/Period Scope Register">
<input>T4.1 Source Register + source document content.</input>
<gate>Source-supported only. No entity inference from filenames.</gate>

## Detailed Instructions
1. Establish issuer entity scope: issuer name (legal entity), borrower, guarantor group, restricted group. Note ambiguity.
2. Establish all reporting periods: annual, interim, quarterly. Record FY end, stub/short periods.
3. Record reporting basis: currency, unit, consolidation perimeter, accounting basis.
4. Cross-reference against Source Register — ensure all sources mapped to entities and periods.

## Output — T4.2 Entity Period Key Register
`Entity Name` | `Entity Role` | `Fiscal Year End` | `Reporting Currency` | `Reporting Unit` | `Consolidation Perimeter` | `Accounting Basis` | `Available Periods`

## Warnings
- Entity names from content, not filenames. Flag ambiguity.
- If consolidation perimeter differs across sources, flag — affects Step 3.
</step_reference>
