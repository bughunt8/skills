---
name: idea-to-shipped-code
problem: "I have a vague idea and need shippable code."
summary: "Route a one-line idea through spec → tickets → build → review."
composed_by: Ronald Ng
input: a one-line idea
output: reviewed, shippable code
steps:
  - skill: ask-matt
    invocation: user
    handoff: the routed flow
    why: route the idea to the right flow before any work starts
  - skill: to-spec
    invocation: user
    handoff: a decision-complete spec
    why: turn the idea into a spec with no unanswered forks
  - skill: wayfinder
    invocation: user
    handoff: decision tickets
    why: map the spec into a shared map of decision tickets
  - skill: to-tickets
    invocation: user
    handoff: tracer-bullet slices
    why: break the plan into independently grabbable vertical slices
  - skill: implement
    invocation: user
    handoff: the built work
    why: build exactly what the tickets describe
  - skill: code-review
    invocation: model
    handoff: the diff
    why: verify the diff against the spec before it ships
prompt: |
  You are executing the Solution Skill "idea-to-shipped-code".
  Problem: I have a vague idea and need shippable code.
  Coordinate these stages in order, passing each output to the next.
  Do not invoke a user-only skill from this Solution. At each of the first five
  boundaries, name the needed command and stop until the user independently
  invokes it. Approval of this Solution is not an invocation of all its stages.
  1. Human /ask-matt routes the idea.
  2. Human /to-spec captures the agreed specification.
  3. Human /wayfinder maps unresolved decisions when needed.
  4. Human /to-tickets produces tracer-bullet slices.
  5. Human /implement builds within the approved ticket scope.
  6. Call the Skill tool with "code-review" for independent diff review.
  Resolve each provider through .agents/skill-dependencies.json before dispatch.
  Retain phase approval, tests, review and separate release authority.
  The skills are by their own authors (bughunt8/skills, MIT); this solution only
  composes them. Reading a user-only body does not bypass its invocation rule.
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

Six existing skills define the stage map. The first five require independent
human commands; this Solution coordinates handoffs rather than auto-loading
them. Its metadata records each invocation mode, and the repository checker
rejects an automatic step aimed at a user-only provider.
