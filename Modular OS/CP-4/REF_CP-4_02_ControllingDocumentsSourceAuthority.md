<!-- REF_CP-4_02 (T2) | 2026-06-03 -->
<step_reference module="CP-4" step="02" name="Controlling Documents and Source Authority">
<input>T4.1 Source Gate output; all legal documents identified in Step 1.</input>
<gate>Step 1 complete; Module Status ≠ Blocked.</gate>

## Instructions
1. Build a controlling-document register for all legal sources.
2. For each document: record Authority Rank (1–6), Document name, Document Type, Version/Date, Status (executed/draft/posting/etc.), Governing Role, Credit Relevance, and Evidence ID.
3. Explain which documents control the analysis and which are summaries, marketing materials, posting versions, or third-party interpretations.
4. If source conflicts exist between authority levels, note the conflict and state which document governs.
5. If key documents are missing (e.g., no ICA, no compliance cert), flag the gap and downstream impact.

## Output
T4.2: `Authority Rank`|`Document`|`Document Type`|`Version / Date`|`Status`|`Governing Role`|`Credit Relevance`|`Evidence ID`
</step_reference>
