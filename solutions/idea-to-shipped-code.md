---
name: idea-to-shipped-code
problem: "I have a vague idea and need shippable code."
summary: "Route a one-line idea through spec → tickets → build → review."
composed_by: Ronald Ng
input: a one-line idea
output: reviewed, shippable code
steps:
  - skill: ask-matt
    handoff: the routed flow
    why: route the idea to the right flow before any work starts
  - skill: to-spec
    handoff: a decision-complete spec
    why: turn the idea into a spec with no unanswered forks
  - skill: wayfinder
    handoff: decision tickets
    why: map the spec into a shared map of decision tickets
  - skill: to-tickets
    handoff: tracer-bullet slices
    why: break the plan into independently grabbable vertical slices
  - skill: implement
    handoff: the built work
    why: build exactly what the tickets describe
  - skill: code-review
    handoff: the diff
    why: verify the diff against the spec before it ships
prompt: |
  You are executing the Solution Skill "idea-to-shipped-code".
  Problem: I have a vague idea and need shippable code.
  Run these skills in order, passing each output to the next:
  1. ask-matt — route the idea to the right flow
  2. to-spec — turn it into a decision-complete spec
  3. wayfinder — map the spec into decision tickets
  4. to-tickets — break it into tracer-bullet vertical slices
  5. implement — build the work the tickets describe
  6. code-review — verify the diff before it ships
  The skills are by their own authors (bughunt8/skills, MIT); this solution only
  composes them. Load each skill's SKILL.md when its step begins.
---

# Idea → Shipped Code

## The problem

A founder or lead has a one-line idea and no spec, no tickets, no build. Starting wrong
costs weeks of work on the wrong thing; not starting at all costs the opportunity.

## Ways to solve it

- **Route A — disciplined.** Spec first, then tickets, then build, then review. Slow,
  repeatable, and safe. This is the route below.
- **Route B — prototype-first.** Throw away a prototype to find the shape, then spec from
  what worked.
- **Route C — smallest honest thing.** Build one slice only, ship it, and decide from there.

## Solution Skill (Route A)

Six existing skills, in order. Each step is attributed to its own author; the composition
is what this solution claims.
