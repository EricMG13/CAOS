# CAOS Credit Analysis

CAOS turns source-bound credit analysis into defensible models and committee-ready conclusions.

## Model Language

**Model Build**:
An immutable, application-built model anchored to accepted analytical authority. Analyst inputs never alter it.
_Avoid_: Base model, system model, canonical workbook

**Analyst Model Revision**:
A recoverable recalculation of a Model Build reflecting one committed set of analyst assumptions.
_Avoid_: Edited model, modified build

**Checkpoint**:
A named Analyst Model Revision retained as a durable reference for review, comparison, or a committee decision.
_Avoid_: Snapshot

**Draft Revision**:
Temporary unreleased assumption work that is visible only to its author and is not retained by CAOS.
_Avoid_: Unsaved model

**Signed-Off Revision**:
An Analyst Model Revision deliberately released by its author with notes explaining its assumptions. It is retained and visible to every authorized member of the case.
_Avoid_: Approved model, published model

**Sign-Off**:
An authorized case writer’s self-release of an Analyst Model Revision into the shared case record. It is distinct from independent report approval.
_Avoid_: Approval, ratification, publication

**Active Analyst Model**:
The latest Signed-Off Revision anchored to the current Model Build and the default analyst model for the case. Older and stale Signed-Off Revisions remain recoverable.
_Avoid_: Latest model, current build

**Sign-Off Note**:
The author’s single rationale for the assumptions represented by a Signed-Off Revision.
_Avoid_: Assumption note, model comment, change message

**Assumption Registry**:
The methodology-owned catalogue of model inputs that analysts may change. Calculated outputs and formulas are not assumptions and never belong to the registry.
_Avoid_: Editable cells, override catalogue

**Assumption Guardrail**:
The methodology-owned unit, default range, step, and hard bounds governing an assumption’s valid values.
_Avoid_: Input validation, UI limit

**Base Case**:
The analyst’s underwritten forecast within an Analyst Model Revision.
_Avoid_: Expected case, central case

**Downside Case**:
The adverse but decision-relevant forecast paired with the Base Case in an Analyst Model Revision.
_Avoid_: Worst case, stress case

**Stale Revision**:
A Signed-Off Revision whose Model Build no longer matches the case’s current accepted analytical authority. It remains visible but cannot be the Active Analyst Model.
_Avoid_: Expired model, old model

**Rebase Candidate**:
A temporary recalculation that carries compatible assumptions from a Stale Revision onto the current Model Build for analyst review. It becomes shared model history only through Sign-Off.
_Avoid_: Migrated model, automatic update

**Scenario Run**:
A temporary what-if recalculation that changes registered assumptions without changing shared model history.
_Avoid_: Saved scenario, model revision

**One-Way Sensitivity**:
A Scenario Run that varies one registered assumption across a range while holding all other assumptions constant.
_Avoid_: Scenario table

**Multi-Driver Scenario**:
A Scenario Run that combines changes to multiple registered assumptions in one comparison.
_Avoid_: Saved case, custom case

**Apply to Draft**:
The deliberate transfer of selected Scenario Run assumptions into the author’s Draft Revision. It does not sign off or share those assumptions.
_Avoid_: Save scenario, commit scenario

**Liquidity Headroom**:
The accessible liquidity remaining above the model’s minimum-cash requirement.
_Avoid_: Cash buffer, available cash

**Covenant Headroom**:
The remaining capacity before a forecast credit metric breaches its binding covenant threshold.
_Avoid_: Covenant cushion

**Breakpoint**:
The first assumption value and forecast period at which a defined liquidity or covenant threshold is breached.
_Avoid_: Failure point, stress limit

## Deliverable Language

**Deliverable**:
A committee-ready document produced for one CAOS analytical pathway.
_Avoid_: Report type, output pack

**Pathway Template**:
The defined structure for a pathway’s Deliverable: Investment Committee Credit Memo, Earnings Update, Covenant and Refinancing Brief, Relative Value Note, Scenario and Recovery Pack, or Evidence-Bound Research Memorandum.
_Avoid_: Archetype, report template

**Credit Snapshot**:
The opening summary section of a Deliverable, not a separate Deliverable.
_Avoid_: Snapshot report

**Deliverable Appendix**:
A reusable evidence, scenario, or model section attached to a Deliverable when relevant.
_Avoid_: Standalone report

**Deliverable Draft**:
A shared, revisioned working Deliverable assembled from a Pathway Template before its exact content is frozen.
_Avoid_: Report draft, working paper

**Generated Block**:
A Deliverable block whose analytical values and identity come from frozen CAOS authority rather than author prose.
_Avoid_: Locked text, system section

**Narrative Block**:
An author-editable Deliverable block used to explain, interpret, or qualify the underlying analysis.
_Avoid_: Free text, rich-text field

**Scenario Exhibit**:
A reproducible Deliverable block capturing the exact assumptions, outputs, model identity, and methodology identity of a temporary Scenario Run.
_Avoid_: Saved scenario, scenario screenshot

**Evidence Citation**:
A reference connecting a material narrative claim to case evidence.
_Avoid_: Source note, footnote

**Analyst Judgment**:
An explicit label for a material narrative claim that is not supported by case evidence.
_Avoid_: Unsupported claim, assumption

**Frozen Deliverable**:
An immutable Deliverable version materialized for exact review and approval.
_Avoid_: Final draft, report snapshot

**Filed Deliverable**:
An approved Frozen Deliverable available for governed export.
_Avoid_: Published report, final report
