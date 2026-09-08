---
name: landing-page-that-sells
problem: "My landing page reads as AI-slop and doesn't convert."
summary: "Audit, redesign, and re-implement a page until it looks and reads like a brand."
composed_by: Ronald Ng
input: an existing (or blank) landing page
output: a redesigned, on-brand landing page
steps:
  - skill: taste-skill
    handoff: an art direction for the page
    why: establish the anti-slop design language before touching layout
  - skill: redesign-skill
    handoff: an audited, improved page
    why: audit what is there and apply the direction without breaking function
  - skill: image-to-code-skill
    handoff: implemented, image-faithful sections
    why: generate and implement the visual sections the direction demands
  - skill: ui-ux-pro-max
    handoff: an accessible, usable page
    why: verify contrast, hierarchy, and usability so it does not just look right
prompt: |
  You are executing the Solution Skill "landing-page-that-sells".
  Problem: My landing page reads as AI-slop and doesn't convert.
  Run these skills in order, passing each output to the next:
  1. taste-skill — establish the anti-slop design language
  2. redesign-skill — audit and improve the existing page without breaking function
  3. image-to-code-skill — generate and implement the visual sections to match
  4. ui-ux-pro-max — verify contrast, hierarchy, and usability
  The skills are by their own authors (bughunt8/skills, MIT); this solution only
  composes them. Load each skill's SKILL.md when its step begins.
---

# Landing page that sells

## The problem

A page that reads as generic AI output repels the exact visitor it was built to
convert. It looks right to nobody and sells to nobody.

## Ways to solve it

- **Route A — redesign in place.** Keep the content, fix the craft. The route below.
- **Route B — rebuild from an image.** Generate a fresh reference, then implement it 1:1.
- **Route C — copy-first.** Rewrite the messaging before touching pixels.

## Solution Skill (Route A)

Four skills in order: set the design language, audit and improve, implement the
sections, then verify they are actually usable.
