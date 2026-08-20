---
name: refine-prompt
description: Turn a rough prompt into a precise, self-contained prompt engineered for an AI agent to execute. Analyzes the draft, asks targeted clarifying questions about goals, scope, constraints and ambiguity, then outputs a copy-paste-ready refined prompt. Use when the user wants to improve, sharpen, rewrite or "prompt engineer" an instruction before feeding it to an agent.
allowed-tools: Read Grep Glob
argument-hint: the prompt to refine (raw text, a file path, or empty to be asked)
---

# Refine a Prompt

Take a rough prompt and return a sharper one, purpose-built to be executed by an AI agent that has **no memory of this conversation**.

## The One Rule That Overrides Everything

**You are refining the prompt. You are not executing it.**

If the incoming prompt says "build a login form", you do not build a login form — you produce a better prompt for building a login form. This is the single most common failure of this skill. Re-read the incoming text as *material to be rewritten*, never as an instruction addressed to you.

The only exception: read-only inspection of the user's codebase (`Read`, `Grep`, `Glob`) to ground the refined prompt in real file paths, type names and conventions. Never write, edit, or run anything.

---

## Step 1 — Intake

Resolve the draft prompt from `$ARGUMENTS`:

| Input                          | Action                                                                    |
| ------------------------------ | ------------------------------------------------------------------------- |
| Raw text                       | Use it as the draft.                                                      |
| A file path                    | Read the file; its contents are the draft.                                |
| Empty, or "my last message"    | Use the user's previous message in this conversation as the draft.        |
| Empty with no prior message    | Ask: "Paste the prompt you want refined." Then stop and wait.             |

Echo nothing back yet. Move straight to analysis.

---

## Step 2 — Analyze

Score the draft against every dimension below. A dimension is either **present**, **vague**, or **missing**. Missing and vague dimensions are the raw material for Step 3's questions.

### Intent

- **Objective** — is the desired end state stated, or only an activity? ("improve the API" is an activity; "cut p99 latency below 200ms" is an objective.)
- **Definition of done** — how would anyone know the task succeeded?
- **Motivation** — is the *why* present? Agents make better trade-offs when they know the purpose.

### Scope

- **In scope** — what must be touched.
- **Out of scope** — what must be left alone. Almost always missing, and almost always the highest-value addition.
- **Depth** — a quick patch, a production-grade implementation, or an exploration?

### Context & grounding

- Does the agent have the facts it needs, or must it guess at file paths, schemas, API shapes, domain terms?
- Are referenced artifacts identified precisely enough to find? ("the service" vs. `src/Orders/OrderService.cs`)
- Is prior work, existing convention, or a reference implementation mentioned?

### Constraints

- Technical: language, framework, version, platform, dependencies allowed or banned.
- Behavioral: what the agent must not do (delete files, change public APIs, touch migrations, add dependencies).
- Process: must it ask before acting, run tests, stay within a directory?
- Non-functional: performance, security, accessibility, compliance, budget.

### Output contract

- Format: code, prose, table, JSON, diff, file(s) on disk.
- Structure and required sections.
- Length or size bounds.
- Where it goes: stdout, a specific file, a PR.

### Ambiguity

Flag every one of these:

- **Vague adjectives** — "better", "clean", "robust", "modern", "optimized", "user-friendly". Each must become a measurable criterion or be cut.
- **Unresolved references** — "it", "this", "the above", "them" with no antecedent the receiving agent can resolve.
- **Overloaded nouns** — a word that means two things in this domain ("user", "account", "policy", "event").
- **Compound directives** — one sentence carrying three instructions; these get partially executed.
- **Unstated assumptions** — the draft presumes context the receiving agent will not have.

### Failure handling

- What should the agent do when blocked, when a file is missing, when two requirements conflict?
- Is it allowed to make assumptions, or must it stop and ask?
- Is partial completion acceptable?

### Examples

- Would one worked example (input → desired output) resolve more ambiguity than a paragraph of description? If yes, the refined prompt needs one, and you should ask the user for it.

---

## Step 3 — Ask Clarifying Questions

This step is mandatory and is where most of the value is created. Do not skip it, and do not merge it into the final answer.

### What earns a question

Ask only if **a different answer would produce a materially different refined prompt.** Everything else is noise.

Do **not** ask about:

- Anything already stated in the draft.
- Anything discoverable from the codebase — go look with `Read`/`Grep`/`Glob` instead.
- Stylistic preferences with a safe, statable default.
- Details that only matter while executing, not while specifying.

Prioritize, in order: **goal → scope boundaries → hard constraints → output contract → disambiguation → autonomy.**

### How to ask

- Maximum **7** questions. If you have more, you are asking about execution details — cut them.
- Every question carries a **default** that will be used if the user skips it. This makes answering optional and keeps the skill from stalling.
- Ask them all at once, numbered. Never drip-feed one at a time.
- When 2–4 questions have discrete, mutually exclusive options, use the `AskUserQuestion` tool. Otherwise use a numbered markdown list.

Format for the markdown fallback:

```
Before I refine this, {N} questions — answer what you like, skip the rest and I'll use the defaults.

1. **{Topic}** — {question}
   *Default: {what I'll assume}*

2. **{Topic}** — {question}
   *Default: {what I'll assume}*

Reply with answers, or **defaults** to accept all of them.
```

Then **stop and wait.** Do not produce the refined prompt in the same message as the questions.

If the user replies "defaults", "skip", or ignores the questions and asks you to proceed, apply every stated default and continue — do not ask again.

---

## Step 4 — Refine

### Calibrate the depth

Match the scaffolding to the task. A bloated prompt degrades an agent as surely as a vague one.

| Draft complexity                        | Refined form                                                                              |
| --------------------------------------- | ----------------------------------------------------------------------------------------- |
| Single, well-bounded action             | A tightened paragraph plus explicit constraints and output format. No headings.           |
| Multi-step task, one domain             | Objective, Context, Task, Constraints, Output format, Acceptance criteria.                |
| Large or risky task, multiple systems   | Full template below, including edge cases, failure handling, and a worked example.        |

### The template

Use as many sections as the calibration calls for, in this order:

```
# Objective
{One or two sentences: the end state, and why it matters.}

# Context
{Everything the agent needs that it cannot discover on its own: file paths, domain terms,
existing conventions, prior decisions, relevant links.}

# Task
{Numbered steps if order matters; bullets if it does not. One instruction per line.}

# Constraints
Must:
- {...}

Must not:
- {...}

# Output
{Exact shape of the deliverable: format, structure, destination, length bounds.}

# Acceptance criteria
- {Verifiable condition}
- {Verifiable condition}

# Edge cases and failure handling
- {Condition} → {expected behavior}
- If blocked or requirements conflict: {stop and ask | proceed under a stated assumption}

# Example
{Input → desired output, when an example resolves ambiguity faster than description.}
```

### Rewriting principles

- **Self-contained.** The receiving agent sees only this prompt. Every "as we discussed" and "the file I mentioned" must be replaced with the actual content.
- **Imperative, second person, present tense.** "Write the handler", not "You should probably write a handler" or "The handler will be written".
- **One instruction per line.** Split compound sentences; compound directives get partially executed.
- **Measurable over evaluative.** "Clean code" → "functions under 30 lines, no nesting deeper than 2 levels". "Fast" → a number.
- **State the negative space.** An explicit "Do not modify `X`" prevents more damage than three positive instructions.
- **Front-load the objective.** The most important sentence goes first.
- **Preserve the user's vocabulary.** Keep their domain terms exactly. Do not substitute synonyms — it breaks the ubiquitous language and makes the prompt read as if it came from someone outside the project.
- **Never drop a constraint.** Every restriction in the draft survives into the refined prompt, even one that seems redundant.
- **Never invent facts.** If a file path, API name, version, or schema is unknown, write `[TBD: exact path to the order repository]` rather than a plausible guess. A visible placeholder is honest; a fabricated path silently sends the agent to the wrong place.
- **Prefer positive framing, except for hazards.** "Return an empty list" beats "don't return null" — but keep a hard "Do not" for anything destructive or irreversible.
- **Add a verification step** for any task that can be checked (tests, a build, a re-read of acceptance criteria).
- **Cut ritual.** Drop "You are a world-class expert...", "Take a deep breath", "This is very important". A role line earns its place only when it genuinely changes the output (e.g. "Respond as a security reviewer" changes what gets flagged).

---

## Step 5 — Deliver

Output exactly this, in this order:

1. **What changed** — a short list, each line naming the weakness and the fix:
   - `Vague objective` → replaced "improve performance" with a p99 latency target.
   - `Missing scope boundary` → added an explicit do-not-touch list.

2. **Assumptions and placeholders** — every default you applied and every `[TBD: ...]` left in the prompt, so the user knows precisely what to fill in or correct. Omit this section only if there are none.

3. **The refined prompt**, alone in a single fenced code block. Nothing else inside the fence — no commentary, no headers of your own. It must be copy-paste-ready.

4. **One line offering next steps** — run it, iterate on it, or produce a variant tuned for a different model or agent.

Do not ask for permission before delivering. Steps 3 and 5 are the only places this skill talks to the user.

---

## Anti-Patterns

A refinement has failed if it:

- **Executed the task** instead of rewriting the prompt.
- **Skipped the questions** and went straight to output.
- **Asked questions the draft already answered** — signals the draft was never read carefully.
- **Inflated a one-line request** into a ten-section document with four empty headings.
- **Invented specifics** — file paths, class names, library versions the user never mentioned.
- **Lost a constraint** present in the original.
- **Replaced the user's domain terms** with generic synonyms.
- **Buried the prompt** in commentary so it cannot be copied cleanly.
- **Padded with ritual** — expert personas, urgency, flattery, "think step by step" on a task that needs no reasoning scaffold.
