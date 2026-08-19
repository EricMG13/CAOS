<!-- REF_CP-5B_02 (T2) | 2026-06-03 -->
<step_reference module="CP-5B" step="02" name="Top 5 Material Credit Drivers">
<input>T5B.1; QA-cleared module outputs.</input>
<gate>Step 1 complete; Module Status ≠ Blocked.</gate>

## Instructions
1. Identify the Top 5 most material credit drivers from QA-cleared outputs (or full population if Full traceability requested).
2. For each driver: record Rank, Credit Driver, Originating Module, Source-Supported Basis, Why Material (risk mechanic), Committee Relevance (credit implication), Source Trace, and Limitation.
3. Materiality = impact on PD, LGD, liquidity, refinancing, recovery, relative value, recommendation, monitoring, security selection, position sizing, or committee decision.
4. If materiality ranking cannot be supported → state [Insufficient Information] and explain the missing basis.
5. Do not rank beyond Top 5 unless Full traceability is requested.

## Output
T5B.2: `Rank`|`Credit Driver`|`Originating Module`|`Source-Supported Basis`|`Why Material`|`Committee Relevance`|`Source Trace`|`Limitation`
</step_reference>
