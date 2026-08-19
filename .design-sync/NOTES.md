# design-sync notes — CAOS

CAOS is a **Next.js app, not a component-library design system**, so this is an
**off-script `package`-shape synth-entry** sync. Everything below is required for
a reproducible re-sync.

## Build invariants (off-script)
- **No `dist`/`module`/`main`** → converter runs in synth-entry mode (builds an
  entry from `src/components`).
- **Scratch node_modules `.ds-sync/nm/`** (gitignored) holds symlinks the build
  needs: `caos-frontend → caos/frontend`, `react`, `react-dom`. Run with
  `--node-modules .ds-sync/nm`. **Never** put the `caos-frontend` self-symlink
  *inside* `caos/frontend/node_modules` — ts-morph follows it into an infinite
  `node_modules/caos-frontend/node_modules/...` loop (ENAMETOOLONG).
- **Tailwind must be pre-compiled** to `caos/frontend/.ds-tailwind.css`
  (`cfg.cssEntry`) before each build — `globals.css` uses `@tailwind` directives
  that aren't real CSS until compiled. Regenerate:
  `cd caos/frontend && node_modules/.bin/tailwindcss -c tailwind.config.js -i src/app/globals.css -o .ds-tailwind.css --minify`
- **`tsconfig.sync.json`** (`cfg.tsconfig`, committed) aliases `next/link` +
  `next/navigation` to browser-safe shims in `caos/frontend/.ds-shims/` — Claude
  Design has no Next runtime. Without it the bundle pulls Next's client code,
  which references `process.env.__NEXT_*` → `process is not defined` crashes the
  whole IIFE (all components blank). If new components import other `next/*`
  submodules, add a shim + a `paths` alias.
- **`source-kit.mjs` fork** (`.design-sync/overrides/`, `cfg.libOverrides`):
  re-emits the synth entry with explicit per-component re-exports so default
  exports and ESM-ambiguous duplicate names bind to `window.CAOS`. Needs
  `.design-sync/node_modules → ../.ds-sync/node_modules` symlink (gitignored,
  recreate per clone) so the fork resolves `ts-morph`.
- **`componentSrcMap` nulls**: `LineagePanel` (defined in 2 files — ambiguous),
  `G2Chart` (dynamic `import('@antv/g2')` + ResizeObserver — not statically
  renderable), `EvChip` (out of scope). Adding a *non-null* componentSrcMap entry
  in synth mode suppresses src-derivation (drops to just the pinned names) — only
  use null exclusions here.
- **`overrides.cardMode: "column"`** on Panel/SectionHeader/PageSubHeader (wide
  cards that else crop in the product grid). `skip` expects an array of story
  names, NOT a boolean.

## Authored previews
- 10 previews authored (the `shared/` primitives + pipeline atoms Dot/Tag/Bar),
  all graded `good`. Previews import from `'caos-frontend'` and use inline styles
  + `--caos-*` vars / verified `caos-*` utility classes for glue.
- 51 components ship the **floor card** (unauthored) — authorable on any re-sync.

## Re-sync risks (watch-list)
- `.ds-tailwind.css` is **generated** — stale if `globals.css`/Tailwind config
  changed; regenerate before building or utilities go missing.
- The two symlink sets (`.ds-sync/nm/*`, `.design-sync/node_modules`) are
  gitignored — **recreate on a fresh clone** before building.
- `next/*` shims are **inert** (nav/router do nothing in previews — by design).
  Any component depending on real routing renders statically only.
- Preview `caos-*` class glue is validated against the compiled CSS at author
  time; if the type scale / token classes are renamed in the app, re-validate
  `conventions.md` (its class/token list) against the fresh build.
