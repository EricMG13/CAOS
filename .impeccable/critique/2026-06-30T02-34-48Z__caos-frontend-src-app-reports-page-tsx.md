---
target: report builder
total_score: 30
p0_count: 0
p1_count: 2
timestamp: 2026-06-30T02-34-48Z
slug: caos-frontend-src-app-reports-page-tsx
---
# Design Critique: Report Builder (CP-RENDER)

#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Good indicator for reference templates and warning watermarks; minor lag in hydration state. |
| 2 | Match System / Real World | 4 | Layout is perfectly aligned with physical credit research desk binders and report queues. |
| 3 | User Control and Freedom | 2 | Lack of single-field revert or fine-grained undo forces all-or-nothing resets. |
| 4 | Consistency and Standards | 3 | Inline styles and hardcoded color strings bypass CSS variables (e.g. background and overlays). |
| 5 | Error Prevention | 4 | Pasted inputs are filtered/truncated and real issuer run leakage is blocked on mock layouts. |
| 6 | Recognition Rather Than Recall | 4 | Comprehensive source lineage mapping and visual omit/include section indicators. |
| 7 | Flexibility and Efficiency | 1 | No keyboard shortcuts for key toggles (edit/sources/print); zoom relies on multiple click targets. |
| 8 | Aesthetic and Minimalist Design | 3 | Beautiful document counterpoint, but sub-header is cluttered and layout relies on non-standard CSS zoom. |
| 9 | Error Recovery | 3 | Good recovery from contenteditable errors using ESC to blur and revert text. |
| 10 | Help and Documentation | 3 | Descriptive tooltips and clear inline details on QA-117 watermark status. |
| **Total** | | **30/40** | **Good** |

#### Anti-Patterns Verdict

**LLM Assessment:**
The interface successfully avoids generic consumer SaaS dashboard tropes. The design is dense, professional, and looks like a specialized institutional terminal. The cream paper layout provides a stark, pleasant contrast against the dark background. 

However, two design-model tells remain:
1. **Fragile CSS Zoom Usage:** The center canvas uses a browser-level `zoom` style. In real web development, `zoom` is a legacy, non-standard property that fails or behaves inconsistently on Firefox and Safari. Real frontend code would use transform scaling or responsive flex layouts.
2. **Action Bar Clutter:** The top header packs too many tiny buttons in a raw row, suggesting the LLM stacked them sequentially to fulfill user features without grouping them under a clear visual hierarchy.

**Deterministic Scan:**
The CLI design detector scanned all files in `caos/frontend/src/app/reports` and `caos/frontend/src/components/reports` and returned `0` syntactic layout violations, confirming strict adherence to basic tokens.

**Visual Overlays:**
No live browser injection report is available because the CDP connection failed to launch browser context. Static file and code inspections served as the fallback audit.

#### Overall Impression
The Report Studio successfully bridges the gap between a dark analytical cockpit and a light paper publication format. It is a highly readable, specialized institutional screen. The main opportunities lie in standardizing the scaling mechanism, adding page-level keyboard accelerators, and cleaning up the header control layout.

#### What's Working
1. **Lineage Mapping:** The lineage panel is a powerful implementation of the "Show your work" rule. It shows exactly which evidence IDs (e.g., E-09) built each section and traces them to specific modules.
2. **Intuitive Edit Mode:** Clicking `✎ EDIT` makes the document inline-editable while scrubbing rich formatting on paste and preserving text length limits, making it safe and robust.

#### Priority Issues

##### [P1] Non-Standard CSS Zoom Scaling
- **Why it matters:** The document preview relies on the non-standard `zoom` CSS property. This is a severe cross-browser risk: Firefox ignores it, and web views or older Safari versions render it with clipping bugs.
- **Fix:** Replace browser-level `zoom` scaling with a standard CSS `transform: scale()` wrapper or dynamic responsive container query classes.
- **Suggested command:** `$impeccable layout`

##### [P1] All-or-Nothing Edit Discarding
- **Why it matters:** If an analyst overrides multiple values across a large document and makes a mistake on one, there is no way to revert that specific field. They must click reset, discarding all other edits and manual work on that report.
- **Fix:** Render a tiny "revert" badge or hover option on modified fields when Edit Mode is active to let users reset individual fields.
- **Suggested command:** `$impeccable polish`

##### [P2] Cluttered Sub-Header layout
- **Why it matters:** The sub-header has 8 different button sections grouped horizontally. On standard laptop viewports, this bar wraps or clips, violating the "Aesthetic and Minimalist Design" heuristic.
- **Fix:** Consolidate secondary adjustments (like paper color presets and zoom percentages) into compact dropdown selectors.
- **Suggested command:** `$impeccable layout`

##### [P2] Hardcoded Colors and Style Leaks
- **Why it matters:** Hardcoded colors like `#08080c`, `#f7f5ee`, and `rgba(5,5,7,0.72)` bypass the token system. Changes to theme values in CSS will not apply here, risking visual bugs.
- **Fix:** Refactor these style rules to use `var(--caos-bg)`, `var(--caos-panel)`, and semantic overlay classes.
- **Suggested command:** `$impeccable colorize`

##### [P3] Low-Affordance Sidebar Rails
- **Why it matters:** When collapsed, the sidebars shrink to a very narrow, vertical text button with no icons or clear hover indications. It is hard to hit and easy to miss for new users.
- **Fix:** Add a small hover slide-out indicator or visual chevron to improve the collapse/expand affordance.
- **Suggested command:** `$impeccable layout`

#### Persona Red Flags

##### Alex (Impatient Power User)
- **Red Flag:** Alex wants to quickly toggle edit mode and compile the report. However, there are no keyboard accelerators (e.g., `Alt+E` for edit, `Alt+P` to print). Alex is forced to target tiny buttons in the header row.
- **Red Flag:** The all-or-nothing edit reset forces Alex to lose minutes of text customizations because one edit was wrong.

##### Jordan (Confused First-Timer)
- **Red Flag:** Jordan clicks `✎ EDIT` but is afraid to type since there are no visible input boundaries or cursor prompts on the document text until a block is hovered over.
- **Red Flag:** The left list shows "HELD" in orange warnings but does not guide Jordan on *what* is wrong or how to clear it until they read a small paragraph at the bottom of the column.

##### Credit Research Director (Institutional Audit Role)
- **Red Flag:** The Director needs to audit why a report is held by QA-117. The lineage panel displays evidence IDs, but they are not categorized by validation state, forcing the auditor to inspect each chip manually to locate the open warning.

#### Minor Observations
- The paper tone button borders hover transitions are clean but lack focus outlines for keyboard users.
- The `fitToWidth` client logic works well, but it should be auto-triggered on page mount or window resize to prevent the document from loading overflowed.

#### Questions to Consider
- What if modified fields showed a small indicator dot that reverts the change when clicked?
- Can we group paper colors and zoom controls into a single "Document Settings" popover to simplify the header?
- Should the QA validation gate list its blockages directly in the Lineage or Export panels for faster debugging?
