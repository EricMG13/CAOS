# The context brief — structure and template

A **context brief** is a self-contained *context pack* handed to a Claude Fable 5
session. It holds everything the session needs to own a task, so the invocation
prompt that points at it can stay thin. The prompt is the front door; the brief is
the house.

**Canonical worked example:** [`caos/docs/PATH_TO_PRODUCTION_BRIEF.md`](../../../../caos/docs/PATH_TO_PRODUCTION_BRIEF.md).
Read it in full before writing a brief — it is the reference implementation of every
section below. Other examples in the repo: `caos/docs/FRONTEND_ARCHITECT_BRIEF.md`.

## Why a brief instead of a fat prompt

Fable 5 follows brief instructions strongly and reasons well over rich context, but
a long list of rules *in the prompt* over-constrains it. The split fixes both:

- **Context → the brief.** Mission, background, baseline, boundaries, output shape,
  done-criteria. Richness here is grounding, and the model reads it as fact to act
  on, not rails to obey.
- **Invocation → the prompt.** A handful of sentences: point at the brief, state the
  deliverable, the boundaries, the autonomy. Nothing the brief already carries.

The exemplar states it directly: the prompt "is deliberately thin: this file is the
context pack, so the prompt only points Fable 5 at it and states the deliverable, the
boundaries, and the autonomy."

## Section template (order matters)

Right-size this. A quick synchronous task may collapse to the first three sections;
a long autonomous or multi-agent task uses them all. Number the sections (§0, §1, …)
so the prompt and the self-check can cite them.

### What this file is (the frame)
One short paragraph, usually a blockquote at the top. State: (1) the **role and
authority** Fable 5 holds ("You are the Principal … you hold full authority over
…"), (2) that it should **read the whole file, then own the mission**, (3) the
**deliverable in one line** and, critically, what the deliverable is *not* ("your
deliverable is a Markdown spec that Opus executes; do **not** write the code").
Follow with a compact header of the load-bearing paths (repo root, the roots it
works in, and where to write output).

### The mission (§0)
The single **outcome owned**, stated so the target persona would recognize it
("when a pipeline is failing at 3am, an operator must be able to see which layer is
at fault from the telemetry alone"). Then decompose it into the **gap classes or
workstreams** the work splits into. Close with the **fixed boundaries** — the posts
that cannot move, each phrased as a constraint every decision must survive.

### How to work — operating guide (§0.1)
Calibrated to how Fable 5 performs best. Draw these from
`references/fable5-guidance.md` and phrase them for the task:
- **Decide the architecture, then decompose** — don't wait for permission; give a
  recommendation, not a survey.
- **Start at the hard foundation**, not the easiest item.
- **Lead every writeup with the outcome**; readability beats brevity.
- **Ground every claim in evidence** — inspect the file before asserting a fact.
- **State boundaries, then stay inside them.**
- **Delegate verification to fresh-context subagents** and keep working while they
  run.
- **Keep a working-memory file** for decisions and rationale.
- Note that **de-prescription is deliberate**: the brief gives goal + constraints +
  map, not a step list; judgment fills the gaps.

### System / background context (§1)
What the thing is, how it's built, and what "done well" means *here* specifically.
Enough for a cold reader to orient without opening the codebase.

### The success bar — objective proxy (§2)
The **rubric or scorecard** the work must hit — the measurable floor that stands in
for the real objective. A table of criteria with an explicit "pass bar" per row
works well. State that the proxy is the floor, not the objective: hitting it must
mean the system is genuinely better, not that a checkbox was satisfied.

### Measured baseline (§3) — when applicable
For a codebase or system task, an inventory of **what already exists (strong — do
not touch) vs. what is missing (the targets)**, grounded in real inspection (cite
file + block, not line numbers). This is what stops Fable 5 from re-specifying strong
existing posture. If you assert it, you must have inspected it — a fabricated
baseline is worse than none. Producing it with fresh-context subagents before
writing the brief is the exemplar's approach.

### Scope / file map & execution order (§4)
The real paths in play and the **dependency-correct sequence** to work them, with a
one-line "why here" per step. Name existing knobs/seams to extend rather than
duplicate.

### Output specification (§5)
The **exact shape** of the deliverable Fable 5 produces: the file to write, its
top-level structure, and a per-item template (treated as a completeness floor, not a
rigid form). Add the rules that keep the output honest — extend before you add, no
line numbers, don't re-spec strong posture, tie each item to a success criterion.

### Self-check protocol (§6)
How Fable 5 verifies its own work **at intervals** (e.g. one fresh-context verifier
subagent per completed layer), with the verifier's charge written out and told to be
adversarial. State the cadence and that every REVISE is reconciled before done.
Fresh-context verifiers beat self-critique.

### Definition of done (§7)
The closing checklist: every condition that must hold for the task to be complete —
grounded, in-scope, boundaries held, verifications reconciled, executable without
further clarification.

### Appendix — invocation (operator note)
Include the **thin prompt** that hands the brief to a Fable 5 session, plus the
**recommended effort** and one line of why. This is the F5Prompt skill's first
output; keeping it in the brief's appendix makes the pair travel together.

## Rules for a good brief

- **Ground everything.** Any fact about existing code/state comes from inspection,
  cited by file + named block.
- **Boundaries are load-bearing.** State them once, sharply, and let the self-check
  enforce them.
- **De-prescribe.** Give the goal, the constraints, the map — not a step list. The
  brief informs judgment; it doesn't replace it.
- **Number the sections** so the prompt and the self-check can reference them.
- **Right-size.** Match section count and depth to the task; don't inflate a short
  task into the full pack.
