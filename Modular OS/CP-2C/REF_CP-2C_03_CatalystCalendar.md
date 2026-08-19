<!-- REF_CP-2C_03 (T2) | 2026-06-02 -->
<step_reference module="CP-2C" step="03" name="Catalyst Calendar">
<input>T5.1</input>
<gate>Events identified</gate>

## Instructions
Produce time-ordered calendar of all credit-relevant events within monitoring horizon. Include: date, event description, category, credit relevance summary. Events outside horizon → note in Gaps Ledger.

Date rules:
- Use only explicitly dated, clearly scheduled, or disclosed-period events. Do not infer dates.
- Format full dates as YYYY-MM-DD. If only a month, quarter, fiscal period, or year is disclosed, preserve that granularity — do not convert to a specific date.
- If an event is disclosed but timing is unavailable, include it only in the Gaps Ledger, not the dated Catalyst Calendar.
- If sources conflict on timing, log the conflict; do not choose a date without evidence.

## Output
T5.2: `Date / Window`|`Event Description`|`Event Category`|`Credit Relevance Summary`|`Source`
</step_reference>
