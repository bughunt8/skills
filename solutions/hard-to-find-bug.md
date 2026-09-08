---
name: hard-to-find-bug
problem: "Something is broken and I can't find where."
summary: "Reproduce it, lock it with a failing test, fix it minimally, verify."
composed_by: Ronald Ng
input: a bug report or symptom
output: a fixed, regression-locked change
steps:
  - skill: diagnosing-bugs
    handoff: a confirmed root cause
    why: run a hypothesis-driven loop until the real cause is pinned
  - skill: tdd
    handoff: a failing test that reproduces the bug
    why: lock the bug with a red test before touching the fix
  - skill: code-review
    handoff: the reviewed fix
    why: verify the minimal fix against the spec and the diff
prompt: |
  You are executing the Solution Skill "hard-to-find-bug".
  Problem: Something is broken and I can't find where.
  Run these skills in order, passing each output to the next:
  1. diagnosing-bugs — form hypotheses and run a disciplined loop to the root cause
  2. tdd — lock the bug with a failing test before touching the fix
  3. code-review — verify the minimal fix against the spec and the diff
  The skills are by their own authors (bughunt8/skills, MIT); this solution only
  composes them. Load each skill's SKILL.md when its step begins.
---

# Hard-to-find bug

## The problem

The symptom is obvious; the cause is not. Random edits make it worse. The way out
is a disciplined loop, not intuition.

## Ways to solve it

- **Route A — hypothesis-driven.** Form hypotheses, investigate in parallel, lock the
  root cause with a failing test. The route below.
- **Route B — bisect.** `git bisect` to the offending commit, then read the diff.
- **Route C — observe.** Add tracing and watch it fail in production.

## Solution Skill (Route A)

Three skills: diagnose to a confirmed root cause, lock it with a red test, then
review the minimal fix.
