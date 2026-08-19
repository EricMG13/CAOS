---
target: caos/frontend/src/app/model
total_score: 24
p0_count: 0
p1_count: 2
timestamp: 2026-06-30T02-59-12Z
slug: caos-frontend-src-app-model-page-tsx
---
# Design Critique: Model Builder UI

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | "SAVE MODEL" action has no visual pending/saving feedback. Seeded vs live engine status is tucked in small metadata headers. |
| 2 | Match System / Real World | 4 | Excellent vocabulary match for buy-side analysis (sponsor haircuts, stress tests, cash flow items, EBITDA margins). |
| 3 | User Control and Freedom | 3 | Toggle panels and rails prevent jarring reflows. However, cell-level overrides lack a granular undo/redo; you can only reset from the formula bar or clear all. |
| 4 | Consistency and Standards | 3 | Fits the refined terminal aesthetic perfectly. Toggles and actions in the header are styled identically, and a dotted underline for cell overrides is a non-standard metaphor. |
| 5 | Error Prevention | 2 | "RESET OVERRIDES" and Assumptions reset trigger immediately on a single click with zero confirmation, risking massive loss of input. |
| 6 | Recognition Rather Than Recall | 2 | Double-click for override cell editing and horizontal click-drag scrubbing for assumptions are highly valuable but completely hidden (zero discoverability). |
| 7 | Flexibility and Efficiency | 1 | Spreadsheet lacks keyboard focus traversal. Arrow keys, Tab, Enter, and Esc are standard for data entry but unavailable; users must click every cell. |
| 8 | Aesthetic and Minimalist Design | 3 | Reconciled Bloomberg-like terminal density, but the Assumptions panel is a giant wall of sliders/inputs that can feel overwhelming. Warning banner is permanently visible. |
| 9 | Error Recovery | 2 | Invalid cell inputs are silently ignored (input reverts) without providing visual error feedback or explaining input rules. |
| 10 | Help and Documentation | 2 | Heavy reliance on hover tooltips to explain complex calculations and formulas. No inline documentation or onboarding guide exists. |
| **Total** | | **24/40** | **[Acceptable]** |

## Anti-Patterns Verdict

**Start here.** Does this look AI-generated?

**LLM assessment**: The interface successfully avoids standard SaaS pastel cards, generic landing page eyebrows, and round pill shapes. It has a focused, dense, and professional look. However, it falls into "input-grid fatigue" where dozens of slider scrubbers are displayed at once without visual grouping or variation. The double-click gesture for cell entry and horizontal drag scrubber are non-standard and lack discoverability, making them look like a missed opportunity for deliberate UI guidance.

**Deterministic scan**:
The automated design system scan flagged issues related to undocumented literal colors leaking into component files:
- **`ModelSheet.tsx` (Line 206)**: Hardcoded color `#15202f` is used to simulate row highlight background overlaying `--caos-bg` in the sticky row header. It should use a `color-mix` with `--caos-accent` and `--caos-bg`.
- **`cell-style.ts` (Line 42)**: Hardcoded color `rgba(79,140,255,0.9)` is used for styling percentage text values.
- **`cell-style.ts` (Line 47)**: Hardcoded color `rgba(230,230,239,0.82)` is used for default cell text.

**Visual overlays**: Overlay presentation is not active because the browser subagent ran in sequential mode and script injection was bypassed.

## Overall Impression
The Model Builder successfully delivers a high-density, professional financial workbench that feels terminal-native. It fits the institutional requirements of buy-side credit analysis. However, it treats the spreadsheet grid as a static mouse-clicked component rather than a live, keyboard-traversable workspace, which severely limits workflow efficiency.

## What's Working
- **Visual Recalculation Cues**: Flashing cells using CSS `caos-flash` when values update provides immediate, intuitive feedback during assumptions adjustments.
- **Calculated Formula Tracing**: The Formula Bar is clear and helpful, immediately communicating the data provenance, base rate details, and evidence links for the active cell.
- **Stable Pane Collapsing**: Collapsed Rails (`CollapsedRail` component) maintain stable page layout bounds, avoiding jarring spreadsheet reflows when side panels are collapsed.

## Priority Issues

### [P1] Missing Keyboard Navigation for Spreadsheet Grid
- **Why it matters**: Financial analysts live in spreadsheets and navigate with arrow keys and Tab. Forcing them to click every single cell to check formulas or select fields is tedious and slows down analysis.
- **Fix**: Bind arrow keys, Tab, Enter, and Escape keydowns to the spreadsheet wrapper. Traverse row and column indices to update the `sel` cell state, and trigger the edit mode (`editing`) on Enter.
- **Suggested command**: `$impeccable layout`

### [P1] No Confirmation on Destructive Resets
- **Why it matters**: A user can easily lose their entire custom scenario (which may involve carefully dialing in 10+ overrides) with a single accidental click on "RESET" in the subheader or the Assumptions panel.
- **Fix**: Wrap the reset functions in a confirmation gate (`confirm()` or an inline warning popover) to verify the analyst's intent before wiping overrides.
- **Suggested command**: `$impeccable harden`

### [P2] Hidden Power-User Gestures (Discoverability)
- **Why it matters**: Double-clicking a historical cell to override it and horizontal drag-scrubbing on Assumptions sliders are critical features that are currently invisible. Analysts will assume the cells are static and the assumptions require typing.
- **Fix**: Render a subtle edit indicator (like a tiny pencil icon or corner indicator) on hover for editable cells. For scrubber cells, add a dotted drag-border or a double-headed arrow cursor/handle to signify horizontal drag capability.
- **Suggested command**: `$impeccable clarify`

### [P2] Save Model Pending Feedback
- **Why it matters**: Clicking "SAVE MODEL" initiates an asynchronous API call. Without a loading spinner, disabled state, or "SAVING..." text indicator, the user is left wondering if their work has been saved or if the button failed.
- **Fix**: Maintain a `saving` state when the save button is clicked, disable the button, display "SAVING...", and flash green on success.
- **Suggested command**: `$impeccable polish`

### [P3] Hardcoded Non-Token Colors
- **Why it matters**: Hardcoded color values like `#15202f` and `rgba(79,140,255, 0.9)` drift away from the central theme configuration, making it difficult to maintain theme compliance.
- **Fix**: Standardize on `var(--caos-accent)`, `var(--caos-text)`, or `color-mix` functions to derive highlight shades.
- **Suggested command**: `$impeccable polish`

## Persona Red Flags

### Alex (Power User - Credit Analyst)
- **Primary Action**: Inputs a custom downside scenario with 5 overrides and scrubs interest assumptions.
- **Red Flags**:
  - **No Keyboard flow**: Alex tries to hit `Down-Arrow` to move to the next cell to input an override, but nothing happens. Alex has to grab the mouse, click, click again, type, press enter, and grab the mouse again.
  - **Accidental Wipe**: Alex attempts to click the active assumptions tab but slips and clicks "RESET" on the Assumptions panel, wiping all inputs instantly. High frustration.

### PM / CIO (Investment Committee Reader)
- **Primary Action**: Reviews the best/base/worst net leverage trajectories and downside fragility metrics.
- **Red Flags**:
  - **Active Overrides Invisibility**: The PM cannot quickly tell if the model is showing the base sponsor scenario or if the analyst has overridden numbers, unless they notice the tiny orange "RESET" button in the header.

## Minor Observations
- The warning banner `forecast cells unaudited — CP-5 scope is actuals only` is highly prominent. Since this is static text, it does not need a full warning-colored block that competes with live semantic alerts.
- Cells that fail to evaluate due to degenerate denominators show empty cells, which is safe, but the tooltip could explain *why* the value is undefined (e.g. "EBITDA is 0, division by zero").

## Questions to Consider
- What would a version of the spreadsheet grid look like if we added standard spreadsheet borders and row/col indices (A1, B2) to make cell coordinates instantly clear?
- Can we group the Assumptions panels into collapsible accordion groups to reduce the cognitive load of a 20-slider grid?
