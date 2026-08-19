# Command Center - Portfolio and Sector RV Visual Refinement Spec

Design specification for visual refinement, responsive behaviors, custom vector scaling, and keyboard accessibility for the Command Center Portfolio Table and Sector Relative Value (RV) panels.

![Refined Sector RV Mockup](/Users/ericguei/.gemini/antigravity-ide/brain/d49c9d38-dbe2-44c2-8a94-d4786b897923/sector_rv_refined_mockup_1783308895718.png)

## Goal

Improve layout rhythm, vector rendering logic, premium visual styling, and interaction accessibility across the Command Center views to match the standards of a high-end Credit Operating System terminal:
* Ensure charts and grids scale cleanly on intermediate viewport sizes without label overlaps.
* Upgrade scatter plot indicators and selection feedback to look crisp and deliberate.
* Establish comprehensive keyboard navigation for both tabular views and SVG scatter points.
* Secure full accessibility patterns for column customizations.

---

## Detailed Specifications

### Section 1: Responsive Layout & Spacing (`/arrange`, `/adapt`)
1. **Container Queries (`@container`)**:
   - Wrap the main sections of `SectorRV.tsx` in a `@container` root container.
   - Refactor the grid styling from viewport breakpoints (`xl:grid-cols-[1.6fr_1fr]`) to container queries (`@[60rem]:grid-cols-[1.6fr_1fr]`). This ensures visual columns flow correctly when Command Center sidebar filters collapse or expand.
2. **Scroll Isolation**:
   - Verify all table panels (`PeerTable`, `PortfolioTable`) have explicit `flex-1 min-h-0` constraints.
   - Restrict overflow actions so scrolling occurs locally inside tables, preventing browser outer body scrollbars from breaking the viewport structure.

### Section 2: SVG Chart Dynamic Resize (`/optimize`, `/adapt`)
1. **Resize Observer Hook**:
   - Implement `useResizeObserver` inside `SectorRV.tsx` to actively track parent dimensions.
   - Debounce measurements via `window.requestAnimationFrame` to block layout thrashing.
2. **Dynamic Geometry Scaling**:
   - Pass measured dynamic `width` and `height` coordinates to `<RVScatter />`.
   - Update SVG scaling helper functions (`scaleX`, `scaleY`, `bandX`) to map variables relative to measured width/height, eliminating static viewport limits.
   - Adjust tick density dynamically: on narrow containers, display fewer X/Y grid intervals to prevent overlaps.

### Section 3: Visual Polish & Premium Rendering (`/bolder`, `/polish`)
1. **Double-Ring Highlight**:
   - Replace standard single-color highlights with a nested double-ring system for the selected loan point:
     - Core dot: `r={4}`, colored with sector accent.
     - Buffer layer: `r={6}`, matching panel background (`var(--caos-bg)`).
     - Outer glow: `r={10}`, colored with `var(--caos-accent)`, animated with a slow pulse.
2. **Dashed Level Ticks**:
   - Shift SVG grid coordinates to fine-dashed rules: `strokeDasharray="3 3"` and `strokeOpacity={0.3}`.
3. **Controls Standardization**:
   - Align all buttons, select boxes, and preset filters to share `h-8` heights, identical borders, and matching font scales.

### Section 4: Accessibility Hardening (`/harden`, `/clarify`)
1. **Scatter Point Navigation**:
   - Group scatter point vectors in `<g tabIndex={0} role="button">` wrappers.
   - Map standard attributes: `aria-pressed={isSelected}`, `aria-label="Issuer ticker, price details"`.
   - Bind `onKeyDown` hook to catch `Enter` and `Space` for selecting elements.
   - Render a high-contrast focus outline ring on `focus-visible`.
2. **Accessible Customizer Dialog**:
   - Bind window listener to handle `Escape` key events, closing the open menu.
   - Ensure target trigger buttons recover keyboard focus after closing.

---

## Verification Plan

### Automated Verification
* Execute unit tests:
  ```bash
  cd caos/frontend
  npm test
  ```
* Run local accessibility tests to scan for ARIA compliance:
  ```bash
  node caos/frontend/scripts/a11y-axe.mjs
  ```

### Manual Verification
* Inspect scaling down to `960px` in a web browser using the subagent tools.
* Verify keyboard tab loops: navigate from inputs to control bar buttons, tab through scatter plot points, select a point, and verify the details pane updates.
