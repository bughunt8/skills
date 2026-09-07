# Independent adversarial review

Before this skill was proposed for merge it was reviewed by a different model
(`gpt_5_6_sol`), instructed to be hostile and to run the code rather than read it.
Its verdict on the first version was **reject**, and it was right to be: a valid
document could produce a file containing executable attacker-controlled
JavaScript.

The review is recorded here because the findings are the reason several decisions
in this directory look the way they do, and because "it passed its tests" was
exactly the claim the review demolished. The full first-version suite was green
while all of the below was true.

## Findings and disposition

| # | Severity | Finding | Status |
| --- | --- | --- | --- |
| 1 | **BLOCKER** | Template-token collision enabled stored XSS in a valid document | **Fixed** |
| 2 | MAJOR | `TB` layout used box height as horizontal spacing; nodes overlapped by 122px | **Fixed** |
| 3 | MAJOR | Optional fields were not type-checked; valid CLI input could crash the renderer | **Fixed** |
| 4 | MAJOR | Edges are not routed around unrelated nodes, while the docs claimed otherwise | **Documented**, not fixed |
| 5 | MAJOR | Documented `footer` field was accepted then silently discarded | **Fixed** |
| 6 | MAJOR | Sequence participant `note` was accepted then silently discarded | **Fixed** |
| 7 | MAJOR | Long tokens and CJK text overflowed nodes by thousands of pixels | **Fixed** |
| 8 | MAJOR | The "schema and validator cannot drift" guarantee was false | **Fixed** |
| 9 | MAJOR | Geometry tests only ran one LR example and missed the `TB` breakage entirely | **Fixed** |
| 10 | MAJOR | `test_escaping` was one payload in one field and missed the exploitable bug | **Fixed** |
| 11 | MINOR | `<meta>` description was text-escaped into an attribute context | **Fixed** |
| 12 | MINOR | The "no network" test missed `fetch`/`XHR`/etc., and its sanity check was tautological | **Fixed** |
| 13 | MINOR | Accessibility, reduced-motion and print behaviour had no regression tests | **Fixed** |
| 14 | MINOR | "All problems are reported at once" was not true | **Fixed** |
| 15 | MINOR | Duplicate edges were accepted and drawn on top of one another | **Fixed** |

Fourteen fixed, one accepted and documented.

## 1. The XSS, in detail

Worth reading even if you skip the rest, because the bug was in composition rather
than in a missing `escape()` call, and that class is easy to reintroduce.

`render_html` applied one global `str.replace()` per template token. Text inserted
by an earlier replacement was therefore rescanned by later ones. A node id of
`__A11Y_DESC__` passed through `quoteattr` correctly, landed in `data-id`, was then
matched by the later `__A11Y_DESC__` replacement, and received the accessibility
description, which is escaped for element text and so leaves `"` intact. The quotes
closed the attribute and the rest of the title became an `onfocus` handler.

Reproduced in Chromium: focusing the node set `globalThis.PWN = 1`.

The fix is not a better blocklist. Substitution is now a **single pass** with
`re.sub`, so a placeholder appearing in user data is emitted literally and never
expanded, and attribute sinks use an escaper that also escapes quotes. Reverting
to multi-pass substitution now fails `tests/test_security.py`, which was verified
by doing exactly that.

## 4. Why edge routing was documented rather than fixed

Edges are single cubics between their endpoints. Between neighbouring ranks
nothing can be in the way, and that is now asserted. Longer edges, and the legs of
a back edge heading to its reserved strip, can cross an unrelated node; on a
25-node fully-connected graph the reviewer measured 276 of 600 paths crossing
something.

Obstacle-aware routing is a substantial piece of work and the wrong trade for a
diagram tool whose own guidance is that more than about a dozen nodes means the
diagram should be split. So the claim was corrected instead: SKILL.md and the
authoring contract now state the limitation plainly under "Known limitations". An
overclaiming document is a defect; a stated limitation is a design decision.

## What this changed about the tests

The reviewer's most useful work was not the bug list. It was demonstrating that
several tests passed while their own subject was broken:

- a mutation that completely broke `TB` placement left the whole suite green
- three separate schema-only mutations left the whole suite green
- removing escaping from edge labels left `test_escaping` green
- planting `fetch("https://…")` in the viewer left the "no network" test green
- setting `tabindex="-1"`, inverting the reduced-motion query, and changing
  `@media print` to `@media screen` each left the whole suite green

Every one of those mutations now fails the suite, and that was checked by applying
them rather than by assuming. The suite went from 27 tests to 57, and the schema is
now generated from the validator so that a whole category of drift cannot occur.

## Reproducing the review

```bash
python3 scripts/render_diagram.py --self-test
python3 scripts/generate_schema.py --check
python3 -m unittest discover -s tests -v
```
