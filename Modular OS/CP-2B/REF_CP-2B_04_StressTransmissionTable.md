<!-- REF_CP-2B_04 (T2) | 2026-06-03 -->
<step_reference module="CP-2B" step="04" name="Stress Transmission Table">
<input>Steps 1-3 outputs</input>
<gate>Step 3 complete.</gate>

## Instructions
Use strict directional vector logic. Format every entry as: [Operating Stress] → [Cash Flow Impact] → [Leverage/Liquidity Result] → [Credit Consequence].

Rules:
- Each row must be a causal chain, not a list of unrelated risks.
- If a link is unproven, label [Analyst Inference] or [Insufficient Information].
- Include source-backed operating stress first, then cash-flow consequence, then credit consequence.
- Apply Cash-Flow Conversion Discipline: every path must translate into cash-flow effects.

## Directional Vector Examples (calibration only — tailor to issuer evidence)
- Volume decline → operating deleverage → EBITDA decline → leverage increases and FCF weakens → refinancing risk rises.
- Price pressure → gross margin compression → EBITDA and cash generation weaken → liquidity buffer erodes → PD increases.
- Customer loss → revenue step-down → working-capital unwind uncertainty and lower EBITDA → covenant headroom tightens → monitoring escalation.
- Input-cost inflation without pass-through → margin compression → FCF reduction → revolver reliance increases → liquidity risk increases.
- Capex inflexibility → cash outflow persists despite EBITDA pressure → FCF turns negative → cash burn accelerates → refinancing risk increases.
- Working-capital absorption → near-term cash drain → accessible liquidity falls → revolver / covenant pressure rises → PD increases.
- Floating-rate debt exposure → cash interest increases → FCF and coverage weaken → deleveraging slows → RV / refinancing risk increases.
- Maturity wall plus EBITDA decline → leverage remains elevated → refinancing window narrows → A&E / LME risk increases.
- Covenant EBITDA inflation → apparent headroom exceeds cash-based capacity → creditor cushion is overstated → covenant / RV risk increases.
- Sponsor dividend or aggressive M&A → leverage tolerance rises → deleveraging capacity falls → PD / RV monitoring escalates.

## Output
**T2B.4 Stress Transmission Table:** `Operating Stress`|`Cash-Flow Impact`|`Leverage / Liquidity Result`|`Credit Consequence`|`Evidence Status`|`Source Trace`
- Evidence Status: Source Fact / Calculation / Analyst Inference / Insufficient Information / Directional Only
</step_reference>
