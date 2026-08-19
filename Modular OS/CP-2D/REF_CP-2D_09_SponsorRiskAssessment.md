<!-- REF_CP-2D_09 (T2) | 2026-06-03 -->
<step_reference module="CP-2D" step="09" name="Sponsor Risk Assessment">
<input>T2D.2–T2D.8; cumulative evidence from all prior steps.</input>
<gate>Steps 2–8 complete.</gate>

## Instructions
1. Assign one Sponsor / Governance Risk Level: Low | Medium | High | Insufficient Information.
2. Build risk-level driver table: for each driver, record Evidence, Risk Mechanic, Credit Implication (PD / LGD / liquidity / refinancing / RV / monitoring), Evidence Quality, Source Trace, Countervailing Evidence, Limitation.
3. Before assigning risk level, run Required Gate Tests:
   - Is issuer identity supported?
   - Is ownership / sponsor / shareholder identity supported?
   - Is relevant behavior issuer-specific (not sponsor-generic)?
   - Is timing of the behavior disclosed?
   - Is funding source disclosed where distributions, acquisitions, refinancings, support, or value transfers are discussed?
   - Is credit impact traceable to leverage, liquidity, FCF, refinancing, recovery, legal capacity, disclosure, creditor control, or RV?
   - Are legal capacity and willingness evidence separated?
   - Are unsupported facts marked [Insufficient Information]?
   - Are external claims labelled [External]?
   - Are source_quality and source_trace preserved?
   - Are structured-export records mapped to correct record_type and database target?
4. Provide required explanation: "The risk level is driven by [evidence], because [risk mechanic], which implies [credit implication]. Countervailing evidence is [evidence / Insufficient Information]."
5. Risk Level Guide:
   - **Low:** No documented extraction / creditor-adverse behavior, creditor-aligned financial policy, adequate disclosure, no LME history, low legal-capacity concerns.
   - **Medium:** Mixed / incomplete evidence, some distributions / releveraging but moderate impact, adequate disclosure with gaps, support and extraction coexist.
   - **High:** Documented extraction, aggressive leverage tolerance, documented LME / priming / uptier, weak disclosure blocking monitoring, governance materially reducing creditor protection.
   - **Insufficient Information:** Cannot assign decision-useful level.

## Output
T2D.9: `Risk-Level Driver`|`Evidence`|`Risk Mechanic`|`Credit Implication`|`Evidence Quality`|`Source Trace`|`Countervailing Evidence`|`Limitation`  
\+ Sponsor / Governance Risk Level: [Low / Medium / High / Insufficient Information]
</step_reference>
