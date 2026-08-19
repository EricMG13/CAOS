# CAOS Design System — build conventions

CAOS is a dense, dark **institutional credit-analysis terminal** (a designed
Bloomberg, not a consumer dashboard). Components are React, imported from
`window.CAOS.*`. Styling is Tailwind utility classes layered over `--caos-*` CSS
design tokens.

## Setup
- **No theme provider.** Load `styles.css` and components are styled; without it
  they render unstyled. There is no `<ThemeProvider>` to wrap.
- **Single dark mode only** — there is no light theme. Surfaces ramp dark:
  `--caos-bg` → `--caos-panel` → `--caos-elevated`, hairline `--caos-border`.

## Styling idiom — Tailwind utilities over CAOS tokens
Compose layout with these **verified** utility families (don't invent class
names — use these or inline `style` with the `--caos-*` vars):

- Surfaces: `bg-caos-bg` `bg-caos-panel` `bg-caos-elevated`
- Borders: `border border-caos-border` (hairline) · `border-caos-accent` ·
  `rounded` / `rounded-md`
- Text color: `text-caos-text` (primary) · `text-caos-muted` (secondary) ·
  `text-caos-accent`
- Type scale (custom sizes): `text-caos-3xs` `text-caos-2xs` `text-caos-xs`
  `text-caos-sm` `text-caos-md` `text-caos-lg` `text-caos-xl` `text-caos-2xl`
  and the figure sizes `text-caos-metric` / `text-caos-hero`
- Numerics: **always** `tabular` (tabular-nums, aligned decimals) on any figure
- Caption/label idiom: `tabular text-caos-2xs uppercase tracking-wider text-caos-muted`
- Motion: `transition-caos` (160ms ease-out) · live/running pulse `caos-running` ·
  selection `caos-selected` · change-flash `caos-flash`
- Keyboard focus: `focus-ring`

**Color is signal, never decoration.** Reserve hue for status / seniority /
selection. Status colors are **not** text utilities — apply them inline from the
CSS vars: `--caos-success` `--caos-warning` `--caos-critical` (and `*-bright`
variants), neutral `--caos-idle`, e.g.
`style={{ color: 'var(--caos-critical)' }}`. Several components also take a
`sev` prop (`"critical" | "warning" | "success"`) that tints them for you —
prefer it (see `StatCard`, `Dot`, `Tag`).

## Where the truth lives
- `styles.css` and its `@import` closure (it pulls `_ds_bundle.css`, which holds
  the token `:root`, the compiled utilities, and component CSS) — read before
  styling.
- Per component: `<Name>.d.ts` (props) and `<Name>.prompt.md` (usage).

## Idiomatic example
```tsx
import { Panel, StatCard, Tag } from 'caos-frontend';

<Panel title="Capital Structure" right={<Tag sev="success">PASS</Tag>}>
  <div className="grid grid-cols-3 gap-2 p-3">
    <StatCard value="4.1x" label="Net Leverage" sub="vs 3.8x prior Q" />
    <StatCard value="6.2x" label="Gross Leverage" sev="critical" sub="above 6.0x covenant" />
    <StatCard value="32%" label="Headroom" sev="success" />
  </div>
</Panel>
```
