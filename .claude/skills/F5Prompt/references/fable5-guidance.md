# Claude Fable 5 — prompting guidance (distilled)

Source: Anthropic, *Prompting Claude Fable 5*
(`platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5`)
and *Prompting best practices*. Applies to `claude-fable-5` and `claude-mythos-5`.
This file holds the reference plus the **verbatim instruction snippets** to graft
into rewritten prompts. Quote them as-is; they were tuned by Anthropic.

## What changed from Opus 4.8 (why prompts need rewriting)

- **Stronger instruction following.** One brief instruction steers a behavior;
  enumerating each rule by name is unnecessary and *degrades* output. Give
  objectives, not task lists.
- **Much longer turns by default.** Hard tasks can run many minutes at higher
  effort; autonomous runs can go hours. Expect and design for it (timeouts,
  streaming, async harnesses).
- **Effort is the primary control** for the intelligence / latency / cost
  trade-off — not prompt verbosity.
- **New failure modes to prompt against:** fabricated progress reports,
  over-engineering/unrequested refactoring at high effort, unrequested actions,
  rare early-stopping, and context-budget anxiety.
- **`reasoning_extraction` refusal category.** Instructions to echo/show/transcribe
  the model's chain of thought can trigger refusals and elevated fallbacks.
- Also runs safety classifiers for offensive cybersecurity and biology/life
  sciences; those domains can return `stop_reason: "refusal"`. Configure fallback
  to Opus 4.8 if needed. (Not a prompt-rewrite concern, but worth flagging.)

## Effort levels

- `high` — default for most tasks.
- `xhigh` — most capability-sensitive workloads.
- `medium` / `low` — routine work; lower effort still performs well and often
  exceeds prior models' top effort. Reduce effort if a task completes but takes
  longer than necessary, or for a quicker, more interactive style.

## Verbatim snippets to graft

### Don't overplan an ambiguous task
```
When you have enough information to act, act. Do not re-derive facts already established in the conversation, re-litigate a decision the user has already made, or narrate options you will not pursue in user-facing messages. If you are weighing a choice, give a recommendation, not an exhaustive survey. This does not apply to thinking blocks.
```

### Don't over-engineer at higher effort
```
Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug fix doesn't need surrounding cleanup and a one-shot operation usually doesn't need a helper. Don't design for hypothetical future requirements: do the simplest thing that works well. Avoid premature abstraction and half-finished implementations. Don't add error handling, fallbacks, or validation for scenarios that cannot happen. Trust internal code and framework guarantees. Only validate at system boundaries (user input, external APIs). Don't use feature flags or backwards-compatibility shims when you can just change the code.
```

### Brevity / lead with the outcome
```
Lead with the outcome. Your first sentence after finishing should answer "what happened" or "what did you find": the thing the user would ask for if they said "just give me the TLDR." Supporting detail and reasoning come after. Being readable and being concise are different things, and readability matters more.

The way to keep output short is to be selective about what you include (drop details that don't change what the reader would do next), not to compress the writing into fragments, abbreviations, arrow chains like A → B → fails, or jargon.
```

### Checkpoint / pause only when genuinely needed
```
Pause for the user only when the work genuinely requires them: a destructive or irreversible action, a real scope change, or input that only they can provide. If you hit one of these, ask and end the turn, rather than ending on a promise.
```

### Ground progress claims during long runs
```
Before reporting progress, audit each claim against a tool result from this session. Only report work you can point to evidence for; if something is not yet verified, say so explicitly. Report outcomes faithfully: if tests fail, say so with the output; if a step was skipped, say that; when something is done and verified, state it plainly without hedging.
```

### State the boundaries (assess vs. act)
```
When the user is describing a problem, asking a question, or thinking out loud rather than requesting a change, the deliverable is your assessment. Report your findings and stop. Don't apply a fix until they ask for one. Before running a command that changes system state (restarts, deletes, config edits), check that the evidence actually supports that specific action. A signal that pattern-matches to a known failure may have a different cause.
```

### Give the reason, not only the request
```
I'm working on [the larger task] for [who it's for]. They need [what the output enables]. With that in mind: [request].
```

### Parallel subagents (agentic / orchestration)
```
Delegate independent subtasks to subagents and keep working while they run. Intervene if a subagent goes off track or is missing relevant context.
```

### Memory system (repeated / very long work)
```
Store one lesson per file with a one-line summary at the top. Record corrections and confirmed approaches alike, including why they mattered. Don't save what the repo or chat history already records; update an existing note rather than creating a duplicate; delete notes that turn out to be wrong.
```
Bootstrap it from history:
```
Reflect on the previous sessions we've had together. Use subagents to identify core themes and lessons, and store them in [X]. Make sure you know to reference [X] for future use.
```

### Autonomy reminder (async pipelines, user not watching)
```
You are operating autonomously. The user is not watching in real time and cannot answer questions mid-task, so asking "Want me to…?" or "Shall I…?" will block the work. For reversible actions that follow from the original request, proceed without asking. Offering follow-ups after the task is done is fine; asking permission after already discussing with the user before doing the work is not. Before ending your turn, check your last paragraph. If it is a plan, an analysis, a question, a list of next steps, or a promise about work you have not done ("I'll…", "let me know when…"), do that work now with tool calls. End your turn only when the task is complete or you are blocked on input only the user can provide.
```

### Context-budget reassurance (only if harness shows token countdown)
```
You have ample context remaining. Do not stop, summarize, or suggest a new session on account of context limits. Continue the work.
```

### Readability of the final user-facing summary (long/agentic runs)
```
When you write the summary at the end, drop the working shorthand. Write complete sentences. Spell out terms. Don't use arrow chains, hyphen-stacked compounds, or labels you made up earlier. When you mention files, commits, flags, or other identifiers, give each one its own plain-language clause. Open with the outcome: one sentence on what happened or what you found. Then the supporting detail. If you have to choose between short and clear, choose clear.
```

### Interval self-verification (long-running build tasks)
```
Establish a method for checking your own work at an interval of [X] as you build. Run this every [X interval], verifying your work with subagents against the specification.
```
Fresh-context verifier subagents tend to outperform self-critique.

### send-to-user tool elicitation (async agents delivering verbatim content)
```
Between tool calls, when you have content the user must read verbatim (a partial deliverable, a direct answer to their question), call the send_to_user tool with that content. Use send_to_user only for user-facing content, not for narration or reasoning.
```

## Anti-patterns to strip when rewriting older prompts

| Remove | Because | Replace with |
|---|---|---|
| "Show your reasoning step by step" / "explain your thought process first" / "print your chain of thought" | Can trip the `reasoning_extraction` refusal → fallbacks | Nothing in-prompt. Read `thinking` blocks or use a send-to-user tool for visibility. |
| Long "always do / never do" rule stacks | Over-constrains; degrades output | One brief objective + done-criteria |
| Step-by-step choreography for every task | Micromanages a model that navigates ambiguity well | The goal + success criteria; let it plan |
| Redundant guardrails / hand-holding | Rails weaker models needed; now noise | Trust default behavior; keep only real constraints |
| "Be exhaustive / list all options" (when not wanted) | Fable 5 already elaborates at high effort | The don't-overplan or brevity snippet |
| Defensive backups, unrequested refactors baked into instructions | Fable 5 can over-act at high effort | The boundaries / anti-over-engineering snippet |

## Scaffolding reminders

- **Start at the top of your difficulty range** — Fable 5 undersells on easy
  tests. Let it scope, ask clarifying questions, and execute a hard task.
- **Make self-verification explicit** on long runs; prefer fresh-context verifier
  subagents over self-critique.
- **Refactor existing prompts/skills** — older ones are often too prescriptive and
  degrade output. Cut before you add.
- **Don't instruct Claude to reproduce its reasoning in the response.**
