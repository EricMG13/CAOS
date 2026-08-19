---
name: F5Prompt
description: Turn a user's raw prompt into two paired artifacts for a Claude Fable 5 session — a thin copy-paste invocation prompt and a self-contained context brief (the context pack the prompt points at). Follows Anthropic's official Fable 5 prompting guidance: objectives over task-lists, right-sized effort, stated intent and boundaries, grounded progress claims, and no reasoning-extraction triggers. Prompts the user for missing detail when the request is too thin. Use when the user says "/F5Prompt", "F5 prompt", "make this a Fable 5 prompt", "optimize this for Fable 5", "rewrite for Fable 5", or hands you a prompt to tune for claude-fable-5 / claude-mythos-5.
user-invokable: true
---

# F5Prompt

Turn a user's initial prompt into a Fable 5 session package that follows
Anthropic's **Prompting Claude Fable 5** guidance. Fable 5 (and Mythos 5) behaves
differently from Opus 4.8: stronger instruction following, much longer autonomous
turns, effort as the primary control, and new failure modes (fabricated progress,
over-engineering, `reasoning_extraction` refusals). A prompt written for older
models often *under*performs here — it over-constrains a model that no longer needs
the rails.

## Two outputs, always

This skill produces **two paired artifacts**:

1. **The Fable 5 prompt** — a thin, copy-paste invocation. It does *not* carry the
   context itself; it names the role, points Fable 5 at the context brief, states
   the deliverable, the boundaries, and the autonomy, and stops. Because the brief
   holds the context, the prompt stays short.
2. **The context brief** — a self-contained **context pack** that grounds the whole
   session: the mission and the *why*, an operating guide tuned to how Fable 5
   works, the system/background context, the success bar, any measured baseline of
   what already exists, the file/scope map, the output specification, a self-check
   protocol, and the definition of done. This is the artifact that does the heavy
   lifting; the prompt is just its front door.

The canonical worked example lives in the repo at
[`caos/docs/PATH_TO_PRODUCTION_BRIEF.md`](../../../caos/docs/PATH_TO_PRODUCTION_BRIEF.md)
— read it before writing a brief, and see `references/context-brief-structure.md`
for the distilled section-by-section template. The pairing is the whole idea: the
brief *is* the context pack, so the prompt "only points Fable 5 at it and states the
deliverable, the boundaries, and the autonomy."

## The core shift

Older-model prompting = enumerate every behavior, list every rule, ask the model to
show its work. Fable 5 prompting = **give objectives, not task lists**; steer with
one brief instruction instead of a rulebook; state the *intent* and the
*boundaries*; let the model reason internally. Prescriptive rule-stacks written to
keep weaker models on rails read as constraints that *degrade* Fable 5's output.
When composing, your instinct in the *prompt* should be to **cut**; the *brief* is
where genuine context belongs — richness there is grounding, not rails.

## Workflow

Work through these in order. Read `references/fable5-guidance.md` for the full
guidance and the verbatim instruction snippets you'll graft in, and
`references/context-brief-structure.md` for the brief's shape.

### 1. Classify the prompt

Determine two axes — they decide how heavy the brief needs to be and which prompt
blocks apply:

- **Task type:** one-shot task · coding/debugging · analysis/research · content
  generation · long-running or autonomous agent · multi-agent/orchestration.
- **Delivery mode:** synchronous (user is watching) vs. autonomous/async (user is
  away, agent runs for minutes–hours).

A quick synchronous one-shot gets a **light brief** (a few short sections — intent,
deliverable, boundaries). A long autonomous or multi-agent task gets the **full
pack** like the exemplar (mission, operating guide, baseline, output spec,
self-check, done-criteria). Right-size the brief; don't force a five-minute task
into a seven-section document.

### 2. Check sufficiency — ask before you write

A good brief needs enough to give the model **objectives + intent + boundaries**. If
the raw prompt is missing the pieces below, use `AskUserQuestion` to gather them
*before* writing — do not invent them. Ask only for what's actually missing (skip
anything the prompt already makes clear):

- **Intent / why** — what larger goal this serves and who the output is for. Fable 5
  performs better when it understands intent (see "Give the reason").
- **Deliverable & done-criteria** — what "finished" looks like; how the user will
  judge success. This becomes the brief's definition of done.
- **Boundaries** — is this a *do it* or an *assess it and report* task? Anything
  off-limits, irreversible, or out of scope? These become the brief's fixed
  boundaries.
- **Effort / scope** — how hard/thorough vs. quick-and-interactive.
- **Mode** — will this run autonomously (user away) or interactively?
- **Where the brief should live** — if the prompt will reference the brief by path
  (the usual pattern), confirm or propose a file location (e.g.
  `caos/docs/<TASK>_BRIEF.md`). If the user would rather paste the brief inline,
  note that instead.

Keep it to one `AskUserQuestion` round with 2–4 focused questions. If the prompt is
already rich enough, skip straight to composing and note what you inferred.

### 3. Strip the anti-patterns (from the prompt)

Remove, don't keep — these actively hurt on Fable 5:

- **Reasoning-extraction triggers** — delete "show your reasoning step by step",
  "explain your thought process before answering", "echo/transcribe/print your chain
  of thought". These can trip the `reasoning_extraction` refusal and cause
  fallbacks. If the user needs reasoning *visibility*, tell them to read structured
  `thinking` blocks or use a send-to-user tool — don't put it in the prompt.
- **Enumerated rule-stacks** — collapse long "always/never" lists into one brief
  objective. Brief instruction-following is strong; the list degrades output.
- **Redundant guardrails** — drop hand-holding the model no longer needs.
- **Micromanaged step-by-step task lists** — replace with the goal + success
  criteria and let it determine steps.

### 4. Compose the context brief

Build the brief as a self-contained context pack, right-sized per step 1. Pull the
section template from `references/context-brief-structure.md`; the exemplar's
sections, in order, are:

- **What this file is** — one paragraph: the role/authority Fable 5 holds, what to
  read, and the deliverable. Sets the frame.
- **The mission / outcome owned** — the single outcome, stated so an operator would
  recognize it; the gap classes or workstreams it decomposes into.
- **How to work (operating guide)** — calibrated to how Fable 5 performs best:
  decide-then-decompose, start at the hard foundation, lead with the outcome, ground
  every claim in evidence, state boundaries and stay inside them, delegate
  verification to fresh-context subagents, keep a working-memory file. Graft the
  relevant verbatim snippets from `references/fable5-guidance.md`.
- **System / background context** — what the thing is and what "done well" means
  here.
- **The success bar (objective proxy)** — the rubric/scorecard the work must hit;
  the measurable floor.
- **Measured baseline (when applicable)** — what already exists vs. what's missing,
  grounded in real inspection. For a codebase task, run or cite this so Fable 5
  doesn't re-spec strong existing posture. Ground it; don't fabricate.
- **Scope / file map & execution order** — the real paths and the dependency-correct
  sequence.
- **Output specification** — the exact shape of the deliverable Fable 5 writes.
- **Self-check protocol** — how Fable 5 verifies its own work at intervals
  (fresh-context verifier subagents beat self-critique).
- **Definition of done** — the checklist that closes the task.

The brief carries the intent, the boundaries, and the grounding. Weave the Fable 5
guidance *into* the operating guide and output spec rather than pasting it raw.

### 5. Compose the thin prompt

Keep the prompt short — it points at the brief and states only what the brief
doesn't. Compose from these blocks; include a block only when the classification
calls for it:

- **Point at the brief (always):** `Read <path-to-brief> in full and own the mission
  it defines.` If the brief is pasted inline instead of filed, reference it as "the
  context brief above."
- **Lead with a one-line frame (always):** one sentence of intent —
  `I'm working on [larger task] for [who]; they need [what the output enables].`
- **Deliverable (always):** what to produce and where it goes.
- **Boundaries (when there's a do/assess ambiguity or scope risk):** e.g. *"the
  deliverable is the spec; do not write or apply the code, and do not change
  behavior."* Or the anti-over-engineering block.
- **Autonomy reminder (async, user away):** the "you are operating autonomously…
  proceed without asking; do the work now with tool calls" block.
- **Grounded progress (long/autonomous runs):** *"Before reporting progress, audit
  each claim against a tool result from this session."*
- **Checkpoint / pause rule (agentic):** *"Pause only for a genuine scope change or
  a decision only I can make."*

Pull exact wording for each block from `references/fable5-guidance.md`. The exemplar
prompt (its Appendix) is the target length — a handful of sentences, no more.

### 6. Recommend an effort level

Effort is the primary intelligence/latency/cost control on Fable 5. State a
recommendation with one line of why:

- **`high`** — default for most real tasks.
- **`xhigh`** — the most capability-sensitive / hardest work.
- **`medium` / `low`** — routine work; still strong, often beats older models' top
  effort. Suggest lowering if the task finishes but runs longer than needed or the
  user wants a snappier, interactive feel.

### 7. Deliver

Present, in this order:

1. **The context brief** — either written to the agreed file path (say where), or in
   a fenced block ready to save.
2. **The Fable 5 prompt** — in a fenced block, ready to copy, with the brief's path
   filled in.
3. **Recommended effort** — one line.
4. **What changed** — a terse bullet list (what you cut from the raw prompt, what
   went into the brief), so the user learns the pattern. Lead with the outcome.

If you asked clarifying questions, weave the answers into the brief and prompt
rather than appending them.

## Guardrails for this skill

- **Both artifacts, every time.** The prompt without the brief loses the context;
  the brief without the prompt has no front door. Deliver the pair.
- **Keep the prompt thin, put context in the brief.** Resist stuffing background
  into the prompt — that's the brief's job, and a fat prompt re-introduces the
  over-constraint the skill exists to remove.
- **Right-size the brief.** A one-shot question does not need a seven-section pack, a
  measured baseline, or a subagent self-check protocol. Match brief weight to the
  classification.
- **Ground the baseline.** If the brief asserts what already exists in a codebase,
  base it on actual inspection — a fabricated baseline is worse than none.
- **Preserve the user's actual intent and constraints** — change *how* it's asked,
  never silently change *what* is asked.
- This skill produces the pair; it does not execute the task. Hand back the prompt
  and brief and stop unless the user asks you to also run it.
