# OpenHeart adversarial closure review (final candidate), 2026-10-25

Reviewer: Claude Opus 5.5 on Computer. This is a fresh, independent review; I did not write the code. The author was GPT6.1, so this is a separate-model review. A cross-harness review was not possible because the Claude Code CLI was not authenticated.
Scope: `repos/skills` working tree (uncommitted candidate), `skills/engineering/openheart-analysis/**`, `scripts/sync_vendor.py`, `scripts/test_openheart_pin.py`, manifest source `openheart-reference`, `docs/openheart-integration.md`. Source pin is `repos/OpenHeart` @ `0bf962fc06e975e9ea7610242b8997b1391fec05`.
Method: all runs were on copies (`/tmp/ohc/skill`, `/tmp/ohrepo`) with `PYTHONDONTWRITEBYTECODE=1`. I made no repo edits, commits, pushes or installs. Probe scripts are in `/tmp/ohprobe2/probe.py` and `/tmp/ohprobe2/probe2.py`.

## Verdict

**Approved with bounds. I found no remaining blocking P1/P2 and no new P1/P2.** Each initial finding is either closed mechanically or bounded honestly in the docs. The residual limits below are P3 issues or documented boundaries. None of them blocks this release, provided the release claim stays limited to schema, cross-reference and source-consistency checks. Semantic accuracy is not validated, and no LLM extraction accuracy is claimed.

## Frozen state that was reviewed (sha256)

| File | sha256 |
| --- | --- |
| skill `scripts/openheart.py` (final; adds `portable_json`) | 87e17fce2b60f50bea5cf91ff14b2bb8b372d23ccdc9cf395374949870cf3834 |
| skill `tests/test_openheart.py` (final; 54 tests) | 203bb894d3bf786a473168ba158a90432773e30d0b9b16cc063e88906d0a97e0 |
| skill `scripts/contract.py` | 38a7298d77f1201720c2685050e47108252c8e2fb0e2b74a9912b1bb40717b73 |
| skill `scripts/build_fixture.py` | 5527cd371b8092a5fc9ac8a9dfbab4551092ee23662c3a54cbc98c9901cd5605 |
| `scripts/sync_vendor.py` (includes the final notices text: "checked at least every two weeks … immutable commit references require a reviewed manual pin update") | 552bbe22d764608154b7288ca750616d36e4f4d9bc36351c5fb8b5f8b32b2225 |
| `scripts/test_openheart_pin.py` | f6f41dd8a9fdf9b0d287a755f0d66319fe11fecf9f74bed47f8f9f70d7d3fa94 |
| `skills/vendor.manifest.json` | c8cea025ce5af2a0f2a3af8ede3b4c8b1984d123c44feaf45827369e8a2043e4 |
| `THIRD_PARTY_NOTICES.md` (regenerated; `notices_text(manifest)` matches it exactly) | acb7c74b176b123d216bc1330994ce5ba874e153a71010b99452a0879e38c551 |

Two changes landed after the freeze, and I read and re-verified both:

1. A notices-text-only edit to the importer. I re-ran the importer tests, `--validate-manifest` and `--check` afterwards.
2. A core hardening fix: a recursive `portable_json()` runs at the start of `validate()` and rejects non-finite floats and unpaired surrogates. A new test, `test_overflow_numbers_and_surrogates_rejected`, comes with it.

The diff against my first review copy contains only those additions. `contract.py` and `build_fixture.py` are unchanged.

Post-fix checks on a fresh copy (`/tmp/ohc2`):

- inf, -inf nested in a list, and `1e999` placed consistently in both copies of a reused ID are rejected ("Non-finite JSON number").
- A lone surrogate in a label or in a dict key is rejected ("Unpaired Unicode surrogate").
- A valid astral character and `1e308` are accepted.
- Through the CLI, NaN text and `1e999` text both exit 1.
- Atomic export, TOCTOU, Java XMI and the 45k-node parent chain (2.45s) still behave as before.

## Regression results (my own runs)

- Core suite (final): `python3 -m unittest discover -s tests` **54/54 OK** on Python 3.14.8 and 3.12.15. 3.12 is the CI version. Before the portable_json fix it was 53/53.
- Importer pin suite: `scripts/test_openheart_pin.py` **4/4 OK** on 3.14 and 3.12.
- All repository script tests: `unittest discover -s scripts` **180 OK**. I re-ran them after the notices edit.
- `lint_skills.py` 0 errors; `generate_index.py --check` up to date; `check_links.py` 0 unresolved; `audit_third_party.py` 0 unaccounted; `check_skill_dependencies.py` OK; `sync_vendor.py --validate-manifest` 35 sources, 0 problems.
- Live `sync_vendor.py --check --source openheart-reference`: fetched the exact SHA and reported no drift.
- Source fidelity: the 46 vendored files under `references/upstream/source` are byte-identical to `git show 0bf962f:<path>`. `LICENSE.upstream` is identical.
- **No new drift from the importer change.** I ran each of the 35 sources one at a time with `--check`, once with the new importer and once with the `HEAD` importer:
  - 34/34 non-OpenHeart sources gave identical results.
  - The `HEAD` importer cannot fetch the SHA ref ("Remote branch … not found"), as expected.
  - Five sources (pstack, i-have-adhd, addyosmani-sdd-reference, job-hunt, humanlayer-pr-credit-license) already drift or abort under `HEAD` because their upstreams changed. That is pre-existing and not caused by OpenHeart. One source's error still aborts a combined multi-source `--check`; this is also pre-existing.
- Not run by me: pytest (not installed, and no installs were allowed), jsonschema, Mermaid/PlantUML renderers, and the catalogue browser suites. The parent reports pytest 53/53, pytest collecting only the skill's own tests, jsonschema 4.25.1 and Mermaid 11.12 parses. I did not reproduce these. They are author-reported.

## Closure of the initial findings

| ID | Initial issue | Status | Evidence |
| --- | --- | --- | --- |
| P1-1 | Certainty laundering under a reused ID | **Closed (same ID); bounded (new ID)** | The identity check now compares the full canonical JSON record. Changing basis, resolution, evidence or kind under a reused ID is rejected ("Inconsistent reused ID"). An identical inferred copy in a view marked `complete` is rejected ("inferred node requires partial status"). Pointing a reused edge at a missing endpoint is rejected. See the bounds section for the new-ID residual. |
| P2-1a | `observed` basis without trace evidence | Closed (role-bounded) | Rejected: "observed fact needs trace/snapshot evidence". File roles are still self-declared: a `.py` file marked `role: trace` passes. `data-contract.md` documents that roles need review. |
| P2-1b | Trivial excerpts | Partially closed, bounded | Whitespace-only excerpts are rejected. A one-character excerpt still passes; for example, `"a"` "supports" a Kubernetes deployment node. The docs state that source consistency is not proof. P3. |
| P2-1c | `derived` with no derivation | Closed (presence only) | A missing derivation is rejected. `derivation:"x"` passes. P3. |
| P2-1d | Placeholder method on a populated graph | Closed for "not run" variants | `not run` and `  Not Run ` are rejected. `n/a` passes. P3. |
| P2-2 | XMI namespaces | Closed | The Java export root is `{http://www.eclipse.org/uml2/5.0.0/UML}Model` with `xmi:version=2.5` and `xmi:id` in the `http://www.omg.org/spec/XMI/20131001` namespace. Children are unqualified `packagedElement`, as UML2 XMI expects. `uml:` QName values use a declared prefix. Control and surrogate characters are filtered. It parses with ElementTree. Not validated against a UML tool; the docs state this. |
| P2-3 | Ordinal typing | Closed | On fresh records, `"a"`, `True`, `1.5`, `0` and `-1` are rejected ("invalid ordinal"). `3` is accepted. Sorting is now integer-safe. |
| P2-4 | Atomic export | Closed | A temp sibling directory is renamed into place. On `TypeError` and `KeyboardInterrupt` during the write, nothing is left behind. An export that fails partway (lone-surrogate label) leaves no destination, and a retry succeeds. If the destination appears during export, this is detected and the attacker-created directory is left alone. SIGKILL can leave a hidden `.openheart-*` temp directory (P3, inherent). |
| P2-5 | Line-count semantics | Closed (documented choice) | CRLF and lone CR become LF, and lines are split on LF only. `\x0c` and U+2028 no longer create lines, so the count matches git/wc-style LF counting plus a final unterminated line. A BOM file passes. Non-UTF-8 input fails cleanly with an error that does not name the file (P3). |
| P2-6 | Pin/provenance (index 0, branch drift, metadata) | Closed | `ref` = `expected_commit` = full SHA, fetched detached. `--validate-manifest` rejects a SHA ref that does not match `expected_commit`, and rejects uppercase SHAs. Live `--check` shows no drift. Tampering with `ATTRIBUTION.md`, tampering with `source/PROVENANCE.md`, or changing manifest `pinned_at` each yields "changed: … (generated metadata)" and "drift detected". Notices match the generator. |
| P2-7 | Kind / attribute validation | Closed (stage level); bounded (views) | Invented kinds fail the enum. Stage-specific kind sets are enforced (a `calls` edge in `symbols` is rejected). Callsites need a valid resolution. Unreduced BDDs (`low == high`) are rejected. `1.0` is rejected as a line number. Diagram views do not restrict kinds per view: a `token` node is accepted in `class` (P3). |
| P2-8 | Java fixture ground truth | Closed (scoped) | I checked it by hand against the vendored Java at the pin: NewsAgency implements Subject, NewsChannel implements Observer, NewsAgency's `List<Observer>` field gives a type_use edge, visibilities are correct, and every method returns void. The status is `partial`, and the limitations say only these relations are qualified. Not modelled: parameter-type uses (`Subject.attach(Observer)` and others) and the `observer.update` call. The class-view `reason` could name these (P3). |
| P2-9 | Datasets / scenarios honesty | Closed | `datasets.md` and `scenarios.json` describe mechanical checks only. The dynamic-call scenario is scoped "under the same ID". The report sets `semantic_accuracy: not_validated` and `renderer_syntax: not_run`. |
| P2-10 | Vendored pytest file collected | Closed by inspection; execution author-reported | The skill `conftest.py` sets `collect_ignore_glob` to `references/upstream/**`. I checked upstream pytest `pytest_ignore_collect`: it reads `collect_ignore_glob` through `_getconftest_pathlist(path=collection_path.parent)` and applies `fnmatch` to the full path. A nested conftest therefore excludes `references/upstream/source/...` even when pytest runs from the repo root. CI uses `unittest`, which does not recurse into non-package directories. |

## Residual bounds (non-blocking; must stay in the release notes)

1. **New-ID laundering is not detected (P3, semantic).** A diagram view or `stages.unified` can add a contradictory claim under a fresh ID. For example, an edge `cg:e` of kind `calls` with `basis: source` and `status: complete` passes even though `stages.calls` records the call as unresolved. Upgrading the stage and the view together also passes. `data-contract.md` allows new-ID abstractions and limits the guarantee to reused IDs. Recommended: add one explicit sentence ("contradictions under a new ID are not detected"). Optionally add a lint that requires analysis views (callgraph, cfg, dfg, cdg, robdd, ast) to reuse stage IDs.
2. **Evidence and derivation checks are lexical and presence-only.** Excerpts can be a single character, derivations a single word, and `n/a` is accepted as a method.
3. **View kinds are not restricted per view.**
4. **Roles (`trace`, `snapshot`) are self-declared.**
5. **Rendering loss.** In the Mermaid class export, generics become `List Observer` and method parameters are dropped (`+attach() void`). The full signatures stay in JSON. `FORMAT_LOSSES` documents this in general terms.
6. **Error messages and test strength.** The lone-surrogate case is now closed in `validate()`. A UTF-8 decode error still does not name the file. In the new test, the first two cases (inf, surrogate) change only one copy of the reused ID `class:Payment`. Those cases would therefore still raise `Invalid` through the reused-ID check if `portable_json` were removed. I confirmed the real behaviour separately with consistent mutations. Recommended: assert on the error message, or mutate both copies (P3).
7. **Importer: `pinned_at` updates on every `--sync`, including immutable pins.** As a result, `ATTRIBUTION.md` says "pinned on" with the last sync date rather than the date the pin was chosen. The bump was already there before this change and is now internally consistent (metadata no longer goes stale by one cycle).
8. **Pre-existing importer behaviour.** One failing source aborts a combined run. Five unrelated sources currently drift or abort upstream.
9. **`docs/openheart-integration.md` still says "Syntax checks parse diagrams."** The skill and CI contain no renderer syntax check, and `report.json` says `renderer_syntax: not_run`. Reword it to something like "Mermaid parsing was checked externally by the author (author-reported)". P3, documentation only.
10. **Release boundary.** Known mobile catalogue browser failures (mobile performance and hover-card) are pre-existing, and the parent says they reproduce on the unchanged baseline. I did not re-run them. They are outside the skill's semantics but must be disclosed as unqualified gates. Pytest, jsonschema and Mermaid results are author-reported, not reproduced by me.
11. **Hygiene.** Ignored `__pycache__/*.pyc` (including `pytest-8.4.2` bytecode) is still in the working tree. Git ignores it, but exclude it if the skill is packaged from the filesystem rather than from git.

## Bottom line

No blocking P1/P2 remain, and I found no new ones. The P1 same-ID laundering is mechanically closed. The new-ID variant is a documented semantic boundary, not a regression. The candidate is approved for release within those bounds, together with the residuals and unqualified gates listed above.
