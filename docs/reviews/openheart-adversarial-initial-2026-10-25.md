# Adversarial review: standalone `openheart-analysis` skill

- Reviewer identity: Claude Opus 5.5 on the Computer harness, acting only as reviewer. This is a same-harness review. Claude Code was unavailable (unauthenticated CLI), so no cross-harness review happened.
- Date: 2026-10-25 (UTC 13:00–13:25)
- Target: `/home/user/workspace/repos/skills`, HEAD `82222123accc73f7bbdc929aa081e035ac1bad52` plus the uncommitted working tree
  - `skills/engineering/openheart-analysis/**`, all files read
  - `skills/vendor.manifest.json`, entry `openheart-reference`
- Source: `/home/user/workspace/repos/OpenHeart` at `0bf962fc06e975e9ea7610242b8997b1391fec05`. `git ls-remote` confirms this is the current upstream `main`.
- Hashes of the reviewed state:
  - `scripts/openheart.py` `19c5664f…`
  - `scripts/contract.py` `96a740a2…`
  - `SKILL.md` `d3e22e10…`
  - `vendor.manifest.json` `c164889d…`
  - authored tree digest `6e6929d4…`
  - vendored tree digest `b9b2058a…`
- Concurrency note: the main agent edited `SKILL.md`, `references/source-map.md`, `references/upstream/ATTRIBUTION.md` and `templates/REPORT.md.tmpl` while this review was running (ACT-badge wording, copyright wording, `pinned on` date). Both versions were reviewed. Scripts, schema, tests and the fixture stayed byte-identical to the copy that was tested.
- Method: read the skill tree, its scripts and tests, and the upstream sources it cites. Tests and probes ran only on copies in `/tmp` with `PYTHONDONTWRITEBYTECODE=1`. Nothing was installed and no repository file was edited. Probe script: `/tmp/ohprobe/probe.py`.

## What was verified as correct

- **Byte fidelity.** All 42 vendored files under `references/upstream/source` (excluding the generated `PROVENANCE.md`) are byte-identical to `git show 0bf962f:<path>`. `LICENSE.upstream` equals upstream `LICENSE` apart from the generated header. `Copyright (c) 2026 OpenHeart Contributors` is preserved. Maintainer credit "Ahmad Hassan (B-Ted)" matches upstream `README.md:12,44,216`.
- **Upstream claims in `references/source-map.md` check out:**
  - Synthetic Mermaid output in `mermaid.rs`: CDG amount/saveOrder, call-graph self-cycle, one-second timing, deployment fallback.
  - Constant JSON projections and fabricated `{name}.java` paths in `json.rs`. For example, `export_cfg_diagram` ignores `_uma/_sta/_tca`, uses hardcoded `bb_0..bb_4`, and sets `verified: true` unconditionally.
  - Upstream uses ACT only as the `action` node badge (`web/diagrams/manifest.json:416`, `web/js/themes/theme-manager.js:79`).
  - All 21 pinned upstream URLs cited in the docs resolve to files that are vendored.
- **Tool runs:**
  - `python3 -m unittest discover -s tests`: 31/31 pass on Python 3.14.8 and 3.12.
  - The grammar parses with `feature_version=(3,10)`, and no API newer than 3.9 is used.
  - `lint_skills.py`, `generate_index.py --check`, `check_links.py`, `audit_third_party.py` and `check_skill_dependencies.py` all pass.
  - `sync_vendor.py --check --source openheart-reference` reports no drift and leaves the tree unchanged.
- **Independence.** The skill's scripts use only the standard library. They make no network calls, start no subprocess and never invoke upstream code. Export writes 20 views × `json/mmd/puml`, byte-identical `ACT.*` aliases of `activity.*`, `traceability.json`, `report.json` and `class.xmi`.
- **File safety:**
  - Path traversal, absolute and non-canonical paths, symlinked path components, a missing root, oversize files and oversize models are all refused.
  - An invalid model creates no output.
  - An existing destination is refused.
- **Safe defaults:**
  - `report.json` records `semantic_accuracy: not_validated` and `renderer_syntax: not_run`, and contains no `verified` field.
  - Label sanitising in `literal()` removes newlines, quotes, `%%{`, `!`, `<`, `>`, `;` and `#`.
  - Node IDs are synthetic (`n0…`), so Mermaid reserved words cannot collide with IDs.

## Findings

### P1-1. Cross-view provenance laundering: a projection can upgrade an inferred stage record to a complete source fact under the same ID

- **Where:** `scripts/openheart.py:160-174`. The reuse identity is `("node", label, kind, evidence)` and `("edge", source, target, kind, evidence)`. It leaves out `basis`, `attributes` and `parent`. The inferred-requires-partial rule (lines 164-165 and 173-174) only looks at the record's own `basis`.
- **Contract this breaks:**
  - `references/data-contract.md:39-44`: "inferred records remain partial"; "Diagram records reuse stage IDs only for identical source entities".
  - `SKILL.md` example: "Dynamic dispatch stays unresolved unless supported by evidence".
  - `datasets/scenarios.json` case `dynamic-call`: "no confirmed Payment edge".
- **Reproduction:** run on the bundled fixture, copied to `/tmp`.
  1. Set `diagrams.callgraph.status="complete"` and `reason=""`.
  2. Set `basis="source"` on `call:caller`, `call:unresolved` and `call:site`.
  3. Leave `stages.calls.call:unresolved` as `basis: inferred`, `attributes.resolution: unresolved`.
  4. Run `validate(model, "datasets")`. It returns `pass`.
- **Variant:** setting `attributes.resolution` to `"resolved"` in the diagram also passes, because attributes are not part of the identity.
- **Effect:** `export` then emits a complete call graph whose edge carries `source` basis. `traceability.json:by_entity` merges both records into one entity with no basis field. The only mechanical safeguard against hallucinated certainty is bypassed by copying a record into a view.
- **Remediation:**
  - Include `basis`, `parent` and `attributes` (or at least `attributes.resolution`) in the reuse identity. Alternatively, require a projected record's basis rank to be no stronger than its stage record's (`inferred` < `derived` < `source`; `observed` only with a trace).
  - Propagate a minimum status: a view containing a reused inferred record cannot be `complete`.
  - Add negative tests for both variants.

### P2-1. Several contract rules are documented but never enforced

- **Where:** `references/data-contract.md:39-41`; `references/workflow.md:87-91`; `scripts/openheart.py:124-131,142-174`.
- **Probes that passed `validate()` and exported cleanly:**
  - **(a) Observed runtime facts without a trace.** A `timing` view with `status: complete`, `method: "not run"`, a node with `basis: observed` labelled "charge took 1200ms", and evidence whose excerpt is the single character `"c"` from `checkout.py`. The contract says observed facts "require provided trace/snapshot files in the input inventory".
  - **(b) Trivial excerpt.** A `deployment` view, `complete`, with node "Kubernetes prod cluster", `basis: source` and excerpt `" "` (one space). The test `ev["excerpt"] in "\n".join(lines)` accepts any substring, including whitespace.
  - **(c) Missing derivation.** A `derived` edge with no `attributes.derivation`. The bundled fixture itself does this (`stages.syntax` edges `ast:contains:if` and `ast:contains:call`).
  - **(d) Placeholder method.** `status: complete` with `method: "not run"`.
- **Remediation:**
  - Require excerpts to contain at least one non-whitespace token. Consider requiring an excerpt to match a whole line or a token boundary, or a minimum length.
  - Require `observed` evidence to point to files whose inventory record is marked as a trace or snapshot. Add a `role` field to `files`.
  - Require `attributes.derivation` for `derived` records.
  - Forbid `complete` when `method` is a placeholder.
  - Add `missing-runtime` and `no-padding` regression tests that mirror `datasets/scenarios.json`.

### P2-2. `class.xmi` uses wrong namespaces and is not valid UML/XMI; control characters make it malformed

- **Where:** `scripts/openheart.py:292` builds `f"{{uml}}Model"` and `f"{{xmi}}version"`, and line 297 builds `f"{{xmi}}type"`. In an f-string, `{{uml}}` produces the literal text `{uml}`, not the URI held in the variable `uml`. The `register_namespace` calls (lines 290-291) never take effect.
- **Reproduction:** export the fixture and read `diagrams/class.xmi`:
  ```xml
  <ns0:Model xmlns:ns0="uml" xmlns:ns1="xmi" ns1:version="2.5" ...>
    <packagedElement ns1:type="uml:Class" ...>
  ```
  The namespace URIs are the bare strings `uml` and `xmi`. The QName `uml:Class` uses a prefix that is never declared.
- **Second defect:** a label containing `\u0001` (legal in JSON) produces XML that `ElementTree.fromstring` rejects ("not well-formed (invalid token)").
- **Why tests miss it:** `tests/test_openheart.py:119` only calls `ET.parse`, so a namespace-broken file still passes.
- **Remediation:**
  - Use `f"{{{uml}}}Model"` and `f"{{{xmi}}}type"`, or plain string concatenation.
  - Emit the `xmi:XMI` root (or `uml:Model` with `xmi:id`).
  - Strip or reject XML-illegal control characters.
  - Assert namespace URIs in the test.

### P2-3. Export is not atomic, and an uncaught `TypeError` leaves a partial, unretryable output directory

- **Where:**
  - `scripts/openheart.py:195-197`: `ordered()` sorts every view's edges by `attributes.get("ordinal", 0)`.
  - Ordinal type is checked only for `sequence` (lines 175-179).
  - `export()` at lines 316-330 writes files directly into the destination.
  - The CLI `except` at line 381 does not catch `TypeError`.
- **Reproduction:**
  1. In `diagrams.cfg`, set edge 0 to `attributes.ordinal = "a"` and edge 1 to `ordinal = 1`.
  2. `validate`: passes.
  3. `export`: exits 1 with a raw `TypeError: '<' not supported between instances of 'int' and 'str'` traceback. The destination stays behind with `analysis.json`, `ACT.*` and `activity.*`. Retrying the same `--out` is refused because the destination exists.
- **Remediation:**
  - Validate `ordinal` as a positive integer wherever it appears, or sort with a key that does not depend on type.
  - Export into `tempfile.mkdtemp(dir=parent)` and `os.rename` on success. Clean up on any exception.
  - Catch `Exception` at the CLI boundary with a clear message.

### P2-4. Line counting diverges from editor and git line numbers, and empty or non-UTF-8 files cannot be inventoried

- **Where:** `scripts/openheart.py:119-121` uses `str.splitlines()`. That method also splits on `\x0b`, `\x0c`, `\x1c-\x1e`, `\x85`, `\u2028` and `\u2029`. Separately, `scripts/contract.py:90` sets `line_count` `minimum: 1`.
- **Reproduction:**
  - **(a) Mismatched line numbers.** File `a = 1\n# page\x0c break\nb = '\u2028'\nc = 3\n` has 4 lines by `wc -l` and in editors. The validator counts 6.
    - With `line_count: 4`, it rejects "Wrong line count".
    - With `line_count: 6`, evidence for `c = 3` at the real line 4 is rejected.
    - Correct, editor-visible evidence therefore cannot validate. Form feeds are common in GNU-style C and Python code (CPython's stdlib, for example).
  - **(b) Empty files.** An empty `__init__.py` cannot be listed ("below minimum"). That prevents a complete ingestion inventory for most Python packages.
  - **(c) Non-UTF-8 source.** Latin-1 source raises `UnicodeDecodeError`. The contract does not document a UTF-8 requirement.
- **Remediation:**
  - Split on `\n` only, after normalising `\r\n` and `\r`, and document that rule.
  - Allow `line_count: 0` for empty files (evidence ranges are impossible for them anyway).
  - Document UTF-8 as required, or record `encoding` per file.

### P2-5. The Mermaid/PlantUML class renderer invents types and can show a field as a method

- **Where:** `scripts/openheart.py:187-192` (`literal()` returns `"unnamed"` for an empty string); lines 216 and 256 (the type is always appended); lines 214 and 256 (`member in node["methods"]` is a value-equality test).
- **Reproduction:**
  - A member with `type_name: ""` renders as `+amount unnamed` in Mermaid and `+amount : unnamed` in PlantUML. For untyped languages, which includes the skill's only fixture language, Python, every member gets the made-up type "unnamed".
  - If a field dict equals a method dict, the field renders as `+x() int`.
- **Remediation:**
  - Omit the type suffix when `type_name` is empty.
  - Iterate over fields and methods separately (`for m in fields`, then `for m in methods`) instead of testing list membership.

### P2-6. Pinning OpenHeart while following `main`, placed first in the manifest, will break the scheduled sync for all 35 sources once upstream moves

- **Where:**
  - `skills/vendor.manifest.json`: `openheart-reference` is source index 0 of 35, with `ref: "main"` and `expected_commit: 0bf962f…`.
  - `scripts/sync_vendor.py:768-775` (`check_expected_commit` calls `_fail`, which raises `SystemExit(2)`), called from `preflight_upstream` at line 854 inside the source loop.
  - `.github/workflows/sync-vendored-skills.yml:107` (the "Apply upstream" step runs `--sync`).
- **Reproduction:** in a `/tmp` copy, set `expected_commit` and `pinned_commit` to `1111…` and run `sync_vendor.py --check --source openheart-reference --source pstack`. Output: `error: [openheart-reference] expected_commit … differs …`. The run aborts before `pstack` is examined.
- **Context:** upstream `main` is active, so the abort-all is only a matter of time. The pattern already exists for other sources in this repository; this entry adds another tripwire and puts it first.
- **Contradictory notices:** `references/upstream/ATTRIBUTION.md:12` and `source/PROVENANCE.md:18` advertise "refreshed at least every two weeks". The manifest limitation says updates need a manual pin change.
- **Remediation (pick one):**
  - Pin `ref` to the commit SHA, as the tag-pinned sources do, so `main` drift is ignored.
  - Make an `expected_commit` mismatch a per-source skip or warning that is reported in `drift.txt`, rather than a global abort.
  - Correct the cadence wording for pinned sources.

### P2-7. The "typed" contract types only the envelope; kinds and stage attributes are free-form, and the fixture contradicts its own dictionary

- **Where:**
  - `SKILL.md:28` ("create a typed `analysis.json`").
  - `scripts/contract.py`: `kind` is any non-empty string and `attributes` is `{"type": "object"}`.
  - `references/data-contract.md:57-68`: the stage dictionary is prose only.
- **Evidence:**
  - Any node kind or edge kind is accepted, and nothing ties edge kinds to stages.
  - The bundled fixture's `stages.symbols` uses kind `class`, while the dictionary specifies `symbol` / `scope`.
  - The fixture's syntax `ast` nodes have none of the dictionary attributes (`node_type`, `preorder`, …).
  - Unknown edge kinds silently fall back to `-->` / `->` in class views.
  - Consumers that use the JSON Schema alone also miss every cross-field invariant (dangling endpoints, inferred-requires-partial, ordinals). `data-contract.md` should state this plainly.
  - The JSON Schema allows `integer` values such as `1.0`, which the bundled validator rejects. That is a minor divergence for external validators.
- **Remediation:**
  - Add per-stage `kind` enums, or a `stage_kinds` table enforced by `validate()`, plus minimal required attributes (`resolution` for `callsite`, `ordinal` for messages, `low`/`high` for BDD).
  - Fix the fixture to follow the dictionary.
  - Either qualify "typed" as "typed envelope" or implement the above.

### P2-8. Dataset translation is thin: no upstream example inputs, and the scenarios are not executable

- **Where:** `references/datasets.md:7-11,18-40`; `datasets/`.
- **Evidence:**
  - Upstream pins Java example corpora with known expectations: `examples/big_project_src`, `examples/huge_enterprise_src`, `examples/test_patterns_codebase` and `sample_codebase`. That is 63 files under the same MIT licence. Upstream's CLI collects only Java and Kotlin.
  - The skill ships one 10-line Python fixture, a language the upstream CLI never processed, so no regression compares against upstream inputs.
  - The vendored `web/diagrams/*.json|mmd|puml` sample outputs have no corresponding vendored or modelled inputs.
  - `datasets/scenarios.json` holds ten prose expectations. The only test that references it (`tests/test_openheart.py:131-141`) uses it as an invalid model. None of its cases is scored, and P1-1 and P2-1 show the validator accepts the very outputs that `dynamic-call`, `missing-runtime` and `no-padding` forbid.
- **Remediation:**
  - Add at least one small Java fixture translated from `examples/test_patterns_codebase` (for example the observer pattern), with an independently authored model. Vendor or pin those inputs.
  - Turn each scenario into a validator-level negative test where it can be checked mechanically. Mark the rest as manual evaluation prompts.

### P3 findings

1. **Communication ordinals are not rendered.** `references/diagram-rules.md:21` promises "ordinal labels" for `communication`. `scripts/openheart.py:269` prints an ordinal prefix only when `key == "sequence"`, and the Mermaid flowchart path drops ordinals too. Ordinals affect only sort order. Reproduced: edges with ordinals 2 and 1 render as `-->|"false"|` with no number.
2. **Renderer syntax is unverified and has no render check in CI.** Two outputs are risky in Mermaid and could not be rendered without installing tooling:
   - empty class bodies (`class n0["Checkout"] {` followed by `}`), which is what the fixture produces;
   - `participant n1 as end`, where `literal()` keeps the reserved word.

   `report.json` correctly says `not_run`. Recommend a pinned mermaid-cli/PlantUML check over the exported fixture in CI, and quoting or escaping reserved words in sequence participant aliases.
3. **Parent-cycle detection is O(n²)** (`scripts/openheart.py:155-158`). A 4,000-node chain (907 KiB model) took 1.81 s; the 10 MiB model limit allows about 45k nodes, which would take minutes. Memoise depth per node.
4. **Silent acceptance of unchecked input:**
   - Duplicate JSON keys are accepted with last-key-wins semantics (`load_model`); use `object_pairs_hook` to reject them.
   - `source.revision` is free text and is never compared with the source root's VCS state (`"deadbeef"` passes).
   - A file listed in both `files` and `source.exclusions`, or outside `source.scope`, passes.
5. **Exported `VALIDATION.md` says NOT RUN for checks that ran.** Export copies the template as-is, so the receipt reports schema, cross-references and spans as NOT RUN while `report.json` in the same directory says `pass`. `report.json` also lacks the model SHA-256 and the exporter version, both of which the template asks for. Pre-fill the machine-checked rows and add `model_sha256` and `tool` to `report.json`.
6. **Generated attribution drift is not detected.** When this review started, `references/upstream/ATTRIBUTION.md` read "pinned on n/a" while the manifest said `pinned_at: 2026-10-25`. `sync_vendor.py --check` reported "no drift". The main agent later changed it to the date. Because the file is marked "do not edit by hand" and `--check` does not compare regenerated attribution, this channel is unguarded either way. Have `--check` re-render generated files (ATTRIBUTION, PROVENANCE) and compare them.
7. **Standalone portability claim.** `README.md:4` says the directory is "a complete standalone package". Two generated files link outside it:
   - `references/upstream/ATTRIBUTION.md:11-12` → `../../../../vendor.manifest.json`, `../../../../../scripts/sync_vendor.py` and `.github/...`;
   - `source/PROVENANCE.md:18,23`, similarly.

   Those links break once the skill is copied on its own. The skill itself runs fine from any working directory. Qualify the claim, or add a note that these links refer to the source repository.
8. **A vendored test file matches pytest discovery.** `references/upstream/source/scripts/test_ruthless_popular_datasets.py` matches `test_*.py`. A repo-root `pytest` run (no `pytest.ini` restricts discovery) would collect and execute it: `shell=True` calls to the OpenHeart binary, and `shutil.rmtree("/tmp/openheart_*_out")`. That contradicts the manifest limitation "Do not execute bundled … Python". Add a `conftest.py`/`pytest.ini` `norecursedirs` entry for `references/upstream`, or have the importer rename the file.
9. **Weak tests:**
   - `test_literal_blocks_directives` (`tests/test_openheart.py:165-172`) uses `'\\n'`, a literal backslash followed by n, so it never injects a real newline.
   - `test_all_nonempty_presentations_are_deterministic` (lines 174-178) calls the same pure function twice in one process, so it cannot detect ordering nondeterminism. Shuffle the input instead.
   - No test covers basis laundering, XMI namespaces, communication ordinals, control characters, Unicode line separators or empty files.
10. **Integration doc misclaims** (main-agent document, flagged per task scope):
    - `docs/openheart-integration.md:66` says "Syntax checks parse diagrams." No such check exists, and `renderer_syntax` is `not_run`.
    - Line 45 says "Separate-model source audit". This review ran on the same harness, so it is not a cross-harness review.
11. **Windows path edge cases.** On Windows, `safe_relative` accepts `checkout.py:stream` (an NTFS alternate data stream) and reserved device names. Reject `:` and reserved names when `os.name == "nt"`.
12. **Misleading fixture stage reasons.** The fixture's `stages.ingestion`, `traceability`, `uml` and `unified` keep the template reason "Analysis has not started." The file inventory clearly exists and `traceability.json` is exported, so a model held up as an example teaches the wrong status semantics. Give concrete reasons.
13. **Display names.** The `name` field "OpenHeart source reference for the independent analysis skill" is used as the upstream project's link text in `THIRD_PARTY_NOTICES.md:19` and `ATTRIBUTION.md`. The project is named "OpenHeart". Use a short project name; the qualifier belongs in `notes`.

## Verdict, with bounds

**Not ready to merge as a provenance-checked analysis tool until P1-1 is fixed.** P2-2 (XMI namespaces), P2-3 (export crash/atomicity) and P2-4 (line semantics) are small, local fixes that should go in the same change. P2-6 needs a decision before the next scheduled sync after upstream moves.

On the user's request:
- **Independence:** the skill reproduces the workflow, templates, reports, data schema, the 19 projections plus AST, the ACT alias and Mermaid/PlantUML output as an independent package. It does not install, wrap or execute upstream code.
- **Source fidelity:** byte-exact vendoring and accurate source-map claims.
- **Notices:** the licence notice is correct.

Bounds of this verdict:
- Mermaid/PlantUML/XMI were not rendered (nothing was installed).
- The schema was not checked with a third-party JSON Schema validator (`jsonschema` is not installed).
- Python 3.10 itself was not run (only 3.12 and 3.14).
- No semantic-accuracy evaluation of an LLM-produced model was done.
- Files the main agent may change after 13:23 UTC are outside this review. Re-check against the hashes above.
