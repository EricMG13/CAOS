# Command Center Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve responsiveness, visual consistency, vector chart rendering, and keyboard accessibility for the Command Center Portfolio and Sector RV views.

**Architecture:** Use a custom `useResizeObserver` React hook to calculate parent sizes in pixels, passing them into the SVG chart to scale points dynamically. Refactor panel grids to use CSS `@container` rules so panels fold gracefully. Add window listeners for dialog keyboard states (Escape key closing) and keyboard interactivity (`tabIndex={0}`, `Enter`/`Space` handlers) inside the SVG scatter points.

**Tech Stack:** React 18, Next.js 16, Tailwind CSS, TypeScript, Vitest, Testing Library.

## Global Constraints
* Guard CP-1 figures with `is_finite_number` before dividing/multiplying.
* All layout modifications must adhere strictly to the CAOS theme guidelines:
  * Colors: `--caos-bg #0a0a0f`, `--caos-panel #11131d`, `--caos-elevated #1d2030`, `--caos-border #34384a`, `--caos-accent #63a1ff`.
  * Typography: Inter + JetBrains Mono, decimal aligned `.tabular`.
* Do not use generic AI-slop graphics, decorative gradients, or unstyled card structures.

---

### Task 1: Create `useResizeObserver` Custom Hook

**Files:**
* Create: `caos/frontend/src/lib/use-resize-observer.ts`
* Create: `caos/frontend/src/lib/use-resize-observer.test.ts`

**Interfaces:**
* Consumes: None
* Produces: `useResizeObserver<T extends HTMLElement>() => [React.RefObject<T>, { width: number, height: number }]`

- [ ] **Step 1: Write the failing test**

  Write test cases verifying the hook returns a ref, initial zero dimensions, and updates on resize callback events:
  ```typescript
  import { renderHook, act } from "@testing-library/react";
  import { useResizeObserver } from "./use-resize-observer";

  describe("useResizeObserver", () => {
    it("should initialize with 0 dimensions", () => {
      const { result } = renderHook(() => useResizeObserver<HTMLDivElement>());
      expect(result.current[1]).toEqual({ width: 0, height: 0 });
    });
  });
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `npx vitest run src/lib/use-resize-observer.test.ts`
  Expected: FAIL (module not found / hook not defined)

- [ ] **Step 3: Implement hook**

  Create `caos/frontend/src/lib/use-resize-observer.ts`:
  ```typescript
  import { useState, useLayoutEffect, useRef } from "react";

  export function useResizeObserver<T extends HTMLElement>() {
    const ref = useRef<T | null>(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

    useLayoutEffect(() => {
      if (!ref.current) return;
      const observer = new ResizeObserver((entries) => {
        if (!entries || entries.length === 0) return;
        const { width, height } = entries[0].contentRect;
        window.requestAnimationFrame(() => {
          setDimensions({ width, height });
        });
      });
      observer.observe(ref.current);
      return () => observer.disconnect();
    }, []);

    return [ref, dimensions] as const;
  }
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `npx vitest run src/lib/use-resize-observer.test.ts`
  Expected: PASS

- [ ] **Step 5: Commit**

  Run:
  ```bash
  git add caos/frontend/src/lib/use-resize-observer.ts caos/frontend/src/lib/use-resize-observer.test.ts
  git commit -m "feat: add useResizeObserver hook"
  ```

---

### Task 2: Refactor SVG Scatter Plot to Dynamic Sizing and Keyboard Navigation

**Files:**
* Modify: `caos/frontend/src/components/command/SectorRV.tsx`
* Create: `caos/frontend/src/components/command/SectorRV.test.tsx`

**Interfaces:**
* Consumes: `useResizeObserver` from `caos/frontend/src/lib/use-resize-observer`
* Produces: Responsive and keyboard-navigable `<SectorRV />` and `<RVScatter />` components.

- [ ] **Step 1: Write accessibility and sizing tests**

  Create `caos/frontend/src/components/command/SectorRV.test.tsx` asserting focus and keypress behaviors on SVG scatter points:
  ```tsx
  import React from "react";
  import { render, screen, fireEvent } from "@testing-library/react";
  import { SectorRV } from "./SectorRV";

  describe("SectorRV Scatter Interaction", () => {
    it("renders scatter points as accessible buttons", () => {
      render(<SectorRV />);
      // Assert point tags are focusable and navigable
    });
  });
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `npx vitest run src/components/command/SectorRV.test.tsx`
  Expected: FAIL (points not interactive / test file crashes)

- [ ] **Step 3: Refactor RVScatter coordinates and element controls**

  Update `SectorRV.tsx` to:
  1. Measure container size using `useResizeObserver`.
  2. Modify `RVScatter` component parameters to accept measured `width` and `height`.
  3. Swap static `W=820, H=340` constants for dynamic dimensions in axis rendering, SVG viewport scales, and point mapping.
  4. Modify render output for scatter points:
     - Wrap scatter point tags inside `<g tabIndex={0} role="button">` with custom keyboard listeners (`onKeyDown` handling Space and Enter keys).
     - Add `focus-visible` styles to show a border outline rings on points.
     - Implement the double-ring layout (glowing circle, padding, and center dot) for the selected position.
  5. Mute axes lines to dashed strokes: `strokeDasharray="3 3"` and `strokeOpacity={0.3}`.

- [ ] **Step 4: Run tests to verify they pass**

  Run: `npx vitest run src/components/command/SectorRV.test.tsx`
  Expected: PASS

- [ ] **Step 5: Commit**

  Run:
  ```bash
  git add caos/frontend/src/components/command/SectorRV.tsx caos/frontend/src/components/command/SectorRV.test.tsx
  git commit -m "feat: make sector RV scatter plot responsive and keyboard-navigable"
  ```

---

### Task 3: Spacing Polish and Responsive Grid Layouts

**Files:**
* Modify: `caos/frontend/src/components/command/SectorRV.tsx`
* Modify: `caos/frontend/src/app/command/page.tsx`

**Interfaces:**
* Consumes: Standard layout properties
* Produces: A `@container`-queried layout wrapper and polished control interfaces.

- [ ] **Step 1: Write responsive wrapper test assertions**

  Add container structure checks to `SectorRV.test.tsx` to verify responsive classes are applied.

- [ ] **Step 2: Run tests to verify they pass/fail**

  Run: `npx vitest run src/components/command/SectorRV.test.tsx`
  Expected: PASS/FAIL

- [ ] **Step 3: Modify layout templates**

  1. Wrap `SectorRV` inside a `@container` div class wrapper.
  2. Change the top-half grid from viewport breakpoints `xl:grid-cols-[1.6fr_1fr]` to container classes: `@[60rem]:grid-cols-[1.6fr_1fr]`.
  3. Standardize button heights, border styles, and text letter-spacings in selectors to match the mockups.

- [ ] **Step 4: Verify UI compiles and runs successfully**

  Run: `npx vitest run src/components/command/SectorRV.test.tsx`
  Expected: PASS

- [ ] **Step 5: Commit changes**

  Run:
  ```bash
  git add caos/frontend/src/components/command/SectorRV.tsx caos/frontend/src/app/command/page.tsx
  git commit -m "style: refine Sector RV grid layout and standardize button controls"
  ```

---

### Task 4: Accessible Column Customizer Dialog

**Files:**
* Modify: `caos/frontend/src/components/command/views.tsx`
* Create: `caos/frontend/src/components/command/views.test.tsx`

**Interfaces:**
* Consumes: Close dialog window actions and keyboard escape states.
* Produces: Key-closable, focus-managed Column Customizer Dialog inside the `PortfolioTable` header.

- [ ] **Step 1: Write keyboard dialog tests**

  Create `caos/frontend/src/components/command/views.test.tsx` verifying Escape key closes the customizer popover.

- [ ] **Step 2: Run test to verify it fails**

  Run: `npx vitest run src/components/command/views.test.tsx`
  Expected: FAIL

- [ ] **Step 3: Implement keyboard listeners and focus indicators**

  1. Register a keyboard event listener for the Escape key in the Column customizer popover within `views.tsx`.
  2. When Escape is caught, set `customizerOpen` to false and return focus to the trigger button (`buttonRef.current?.focus()`).
  3. Style the custom checkbox outline states inside the popup.

- [ ] **Step 4: Run tests to verify they pass**

  Run: `npx vitest run src/components/command/views.test.tsx`
  Expected: PASS

- [ ] **Step 5: Commit changes**

  Run:
  ```bash
  git add caos/frontend/src/components/command/views.tsx caos/frontend/src/components/command/views.test.tsx
  git commit -m "feat: secure keyboard accessibility for column customizer dialog"
  ```
