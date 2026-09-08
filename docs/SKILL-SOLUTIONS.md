# Skill Solutions — a problem-first paradigm

> **The library is not a catalog. It is a toolbox for problems you actually have.**
> You scroll through *problems*, not categories. Each problem suggests *ways to solve it*,
> and each way is a **Solution Skill** — a small, authored playbook that chains a number of
> existing skills into one repeatable workflow.

---

## 1. Why this replaces the category browser

The current page answers one question — *"what skills exist?"* — by walking a reader through
22 categories of 435 skills. That is a dictionary, not a tool. Nobody arrives at a dictionary
with a job to do.

The new paradigm answers the question people actually arrive with: *"I have a problem — what
do I do?"*

- **Problem-first.** The landing experience is a list of concrete, named problems
  ("I have a vague idea and need shippable code", "My landing page reads as AI-slop",
  "We need a compliance audit before launch").
- **Ways to solve it.** Each problem presents two or three suggested routes, so the reader
  sees the *trade-off* (fast-and-dirty vs. rigorous, do-it-yourself vs. bring-in-specialists),
  not just one prescriptive answer.
- **A Solution Skill.** Each route resolves into one composed Skill — an ordered chain of the
  skills that already exist in the library, with the reason each one is there.
- **Scroll is the reading model.** You travel *through* a problem the way you travel through an
  argument: problem → options → the solution unfolds as a sequence of steps.

---

## 2. The attribution model (why this matters)

The 435 skills are **not** authored here. They are assembled from public repositories
(`bughunt8/skills`, `haowjy/creative-writing-skills`, `eternityspring/shuohao-skills`, and the
vendored `pstack` / `job-hunt` trees), each under its own licence.

Attribution therefore lives at **two levels, and they must never blur**:

| Layer | Who made it | Attribution shown |
|---|---|---|
| **Skill** (the 435) | its original author | repo link + licence on every card, always |
| **Solution** (the composition) | the curator (Ronald Ng) | "composed by" + the constituent skills credited inline |

A Solution Skill is a *reference to* skills, not a copy of them. It credits the skills it
composes — "Step 2 uses `to-spec`, © its author, MIT" — and claims only the thing it actually
made: the ordering, the glue, and the judgement of *which* skills and *why*.

**Rule:** "Built by Ronald Ng" is banned. The right verb is **"composed by"** or
**"assembled by"** for solutions, and the skills themselves always carry their own author.

**Rule — solutions link, never copy.** A Solution Skill references a skill by its frontmatter
`name` only. It never reproduces a skill's description or body. The `prompt` field is written
fresh, in the composer's own words. If a solution ever needed a skill's actual text, it would
link to it, not quote it. `scripts/check_solutions.py` enforces the reference side (every step
must resolve to exactly one skill, not several); the "never copy" side is a review rule rather
than a mechanical check.

---

## 3. The Solution Skill format

A Solution Skill is itself a Markdown document — a real artifact, not prose. One file per
solution, so a solution can be versioned, linked, reviewed, and even *executed* by an agent
later. Schema:

```markdown
---
# frontmatter
name: idea-to-shipped-code            # lowercase kebab-case, unique
problem: I have a vague idea and need shippable code.
summary: Route an idea through spec → tickets → build → review.
composed_by: Ronald Ng
---

# Idea → Shipped Code

## The problem
...one paragraph: who has it, what it costs to get wrong...

## Ways to solve it
- **Route A — disciplined.** (label the trade-off)
- **Route B — prototype-first.**
- **Route C — do the smallest honest thing.**

## Solution Skill: `idea-to-shipped-code`  (Route A)
A pipeline of existing skills, in order.

### Steps
1. **`ask-matt`** — route the idea to the right flow. *[author, repo, licence]*
2. **`to-spec`** — turn the idea into a decision-complete spec.
3. **`wayfinder`** — map the spec into decision tickets.
4. **`to-tickets`** — break it into tracer-bullet vertical slices.
5. **`implement`** — build the work the tickets describe.
6. **`code-review`** — verify the diff before it ships.

### Inputs / outputs
- In: a one-line idea.
- Out: reviewed, shippable code.

### Attribution
Composed by Ronald Ng. Every step is a skill by its own author, used under its own licence.
```

The `steps` block is the load-bearing part: an **ordered** list of **existing** skills, each
with a one-line *why* and its author/licence. The order is the product.

The model is a **linear chain** today. A future extension adds an optional `when:` condition per
step (branching) — out of scope for v1, but the schema must not assume a step is unconditional.

**The `prompt` contract.** `prompt` is a drop-in **user message** for another agent. The
consuming agent is assumed to already have the referenced skills installed; the prompt names each
skill and its order, and tells the agent to load each skill's `SKILL.md` when its step begins.
It is not a system prompt, not a full tool spec, and it never copies the skills' own text.

**Rename / removal.** When a referenced skill is renamed or removed, `check_solutions.py` fails
with the dangling reference; the fix is to edit the solution's `steps` (or drop the step) — never
to silence the check.

---

## 4. The scroll experience

```
HERO          The Skill Library — "you have a problem. Here's how to solve it."
              (no counting, no category index)

PROBLEM 1     "I have a vague idea and need shippable code."
   └ ways     3 routes, each one line + trade-off
   └ solution Route A unfolds as a horizontal chain of step-cards (the composed skills)

PROBLEM 2     "My landing page reads as AI-slop."
   └ ways     2 routes
   └ solution taste-skill → redesign-skill → ui-ux-pro-max  (a different chain)

...            one pinned "problem" per viewport, the chain scrolls in left-to-right

CLOSE         "435 skills, composed into solutions. Skills © their authors."
```

- One problem = one pinned chapter (reusing the existing `chapter` + filmstrip mechanics, so the
  motion layer, the "fly-through" feel, and the a11y guarantees all carry over).
- The **chain of step-cards** replaces the flat card strip: each step is a card naming a skill,
  its role in the solution, and its author — so attribution stays visible *in the flow*, not in a
  footer.
- No "000 / 435" counter and no count-up. Progress is a **circular ring** (how far through the
  problems you are) plus the current problem's title.

---

## 5. Concrete examples (drawn from the actual library)

1. **"I have a vague idea and need shippable code."**
   → `ask-matt` → `to-spec` → `wayfinder` → `to-tickets` → `implement` → `code-review`.

2. **"My landing page reads as AI-slop."**
   → `taste-skill` → `redesign-skill` → `image-to-code-skill` → `ui-ux-pro-max`.

3. **"We need a compliance / security audit before launch."**
   → `performing-security-audits` → `checking-owasp-compliance` → `generating-security-audit-reports`
   → `assisting-with-soc2-audit-preparation`.

4. **"I need to size a market before building anything."**
   → `market-research-pro` → `competitor-alternatives` → `pricing-strategy`.

(These are illustrative; the authoritative set is authored solution-by-solution.)

---

## 6. What changes vs. what stays

**Stays:** build.py generation-from-tree, per-skill licence/attribution on every card,
pinned-chapter scroll mechanics, the a11y/content/motion test gates, the always-visible rail
(now a rail of *problems*), vendored trees, the "never hand-edit generated output" rule.

**Changes:**
1. The index of content becomes a curated `solutions/` collection (one Markdown per Solution
   Skill), not a flat walk of 435 skills.
2. `build.py` renders *problems and their solution chains* as the pinned chapters; the raw
   category browse becomes a secondary "browse all 435" escape hatch, not the hero.
3. The rail lists **problems**, and each card in a solution chain shows the skill's **author +
   licence** inline.
4. Attribution copy changes from "Built by Ronald Ng" to "Skills © their authors · Solutions
   composed by Ronald Ng".

---

## 7. Open questions for review

- Is "problem → ways → composed Skill" the right *grain*? (Too many problems to curate? Too few
  to be useful?)
- Should a Solution Skill also be an *executable* SKILL.md that an agent can run, or is it
  documentation-only?
- Does surfacing only curated problems hide the long tail (435 skills) from people who want the
  raw catalog? Is the "browse all" escape hatch enough?
