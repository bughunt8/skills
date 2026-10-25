# OpenHeart source-fidelity audit @ 0bf962fc06e975e9ea7610242b8997b1391fec05

Scope: `/home/user/workspace/repos/OpenHeart` (read-only; `git status` clean). No cargo/rustc in the sandbox, so I did not run anything. Every finding below comes from reading source; line numbers refer to that commit. Neither repo was edited.

## 0. Headline verdict
OpenHeart has three layers. Phases 1–9 are real analysis code for Java (Kotlin and JS support is partial). The 19-diagram export layer reads only `uma`/`sta`/`tca`. In many places it writes hardcoded templates that ignore the input, and the three output formats disagree with each other. The marketing/validation layer (README, web demo, Python "ruthless" tests) claims more than the code does. An honest standalone skill should treat the analysis phases as its reference model, re-derive any diagram that upstream fakes, and label each such diagram "skill-native, not upstream parity".

## 1. Workflows (entry points)
| Workflow | Evidence | Reality |
|---|---|---|
| CLI `analyze` (10 phases → binaries + `diagrams/*.puml|mmd|json`) | src/main.rs:139-148 (artifact paths), 257-308 (19 keys × 3 formats) | Files collected only when ext is `java|kt|kts` (main.rs:80,92). Write errors are swallowed with `.ok()` (main.rs:289,298,307). XMI is never written by the CLI. |
| CLI `inspect` | src/main.rs:346-460 | For TCA/BPA it prints "VERIFIED VALID" without running any check (see inspect branch). |
| Library pipeline | src/core/pipeline.rs:159-168 | Unified file is named `graph.scpg` here but `unified.scpg` in the CLI (main.rs:148 vs pipeline.rs:168). |
| HTTP server `/api/analyze` | src/adapters/server.rs | Collects many extensions (server.rs:805-830). `/api/languages` advertises java, python, typescript, javascript, cpp, rust, go (server.rs:84). When a clone fails it falls back to the first directory under `target_repos`, so it can analyse the wrong repo (server.rs:466-485). The response holds only the 14 PlantUML diagrams and the top-10 traceability links (server.rs:700-770). |
| Web demo (GitHub Pages) | .github/workflows/deploy_pages.yml; web/js/github-engine.js; web/js/graph-canvas.js | Not the Rust engine. It parses class declarations in the browser with regex, capped at 30 files (github-engine.js:110-170). It fabricates `id`/`execute()` members and reports a hardcoded `execution_time_ms`. Every other diagram type is produced client-side from the class IR by `projectCustomDiagram` (graph-canvas.js:108-600, e.g. "Synthesize packages" at ~131). |
| Committed demo outputs | web/diagrams/*.json|puml|mmd + manifest.json | Generated from a different codebase, then hand-edited or stale. `compiler_hash` values (0x6FE2910B, 0x11AB90EF, …) do not match the exporter constant 0x83D2D2B2. `state.json`/`use_case.json` keys don't exist in the current factory. Treat as non-reproducible. |

## 2. AST / "ACT" nomenclature
- Upstream term: **BP AST** (Balanced-Parentheses AST), artifact `ast.bpa` (`BPASTArtifact`). Phase 2 is "CST Reduction & BP AST Encoding" (src/ast/mod.rs:1,38; main.rs:140).
- **"ACT" appears nowhere as an artifact or analysis.** Its only uses are a UI badge for activity *action* nodes: web/js/themes/theme-manager.js:79 and web/diagrams/manifest.json:416 (`action: {badge:"ACT"}`). There is no "Abstract Code Tree".
- AST is **not** one of the 19 diagram keys (main.rs:261-279). Any `ast` projection in the skill is a skill-native extension.
- Requirement: the skill must never present "ACT" as an OpenHeart artifact. If a user says "ACT", map it to activity-action nodes (upstream badge meaning) or BP AST, and state which mapping is used and why. Do not invent a third meaning.

## 3. Supported languages (actual)
| Lang | Phase 1 tokens | Phase 2 AST | Phase 3 symbols | CLI collects? | Verdict |
|---|---|---|---|---|---|
| Java | tree-sitter-java (ingestion/adapter/registry.rs:24,66) | JavaASTReductionAdapter (ast/adapter/registry.rs:19) | JavaSemanticAdapter | yes | **Only genuinely supported language** |
| Kotlin | `KotlinLanguageAdapter` uses the **Java grammar** (ingestion/adapter/kotlin.rs; registry.rs:25,67) | not registered → falls back to **generic JS adapter** (ast/adapter/registry.rs:28,41) | Java semantics | yes | Mis-parsed; not supported |
| JavaScript | tree-sitter-javascript (registry.rs:28,70) | generic JS (ast/adapter/registry.rs:24) | **Java semantics hardcoded** (src/symbol/mod.rs:38) | **no** (CLI); server yes | Partial/experimental |
| TS, Rust, Python, C++, Go, C# | Unknown → JS grammar (registry.rs:35,56,82) | TS/Rust mapped to the JS adapter (ast/adapter/registry.rs:25-28) | Java semantics | no (CLI) | **Unsupported**, despite server.rs:84 and README claims |
- Noise: generic.rs:27 `println!("[TS-KIND] ...")` writes debug output to stdout.
- Cargo.toml has only `tree-sitter-java` and `tree-sitter-javascript` dependencies.
- Requirement: the skill states "Java (full); JavaScript (partial: syntax only, Java-style semantics); Kotlin and all others unsupported/heuristic". Inputs in other languages are refused or labelled heuristic.

## 4. The 19 diagram implementations
Exporter API surface: `export_diagram(format, key, uma, sta, tca)` (factory.rs:53-62). **The CFA, SSA, CGA, PSA and TRA artifacts are never passed to any exporter**, even though they contain real data: `BasicBlock` (core/types/cfg.rs:33), `CallEdge` (core/types/cg.rs:71) and PSA summaries. The only exception is `sat_count`/`cyclomatic`, which flows from PSA into class records (uma/structural/class_diagram.rs:224-236).

Legend: G = grounded in extracted symbols/UMA. H = heuristic. T = template (structure is fixed and only names are substituted). S = fully synthetic/constant (ignores input).

| # | key | UMA source | PlantUML | Mermaid | JSON | Notes |
|---|---|---|---|---|---|---|
| 1 | class | real classes/fields/methods | G (274-512); composition is inferred from `final` | G (590) | G (121), but `file: "{Name}.java"` is fabricated and `lines: []` is always empty | XMI is class-only with names `Class_{sym_id}` (xmi.rs:8-13), and every key returns this same class XMI (factory.rs:147,159) |
| 2 | package | real | G (641) | G (900) | G (424) | |
| 3 | component | components = packages 1:1 (uma/structural/component_diagram.rs:10-48) | H (564) | H (834) | H (1043) | |
| 4 | composite | extractor is a no-op (uma/structural/composite_diagram.rs) | H from class fields/inner classes (772) | H (956) | root hardcoded to "OpenHeartEngine" (json.rs:1439-1440) | |
| 5 | object | none (no instances) | class→`obj_` with field-type links (513) | no links (805) | linear chain (1349) | Formats disagree; not real objects |
| 6 | deployment | none (no build/deploy files read) | fabricated `node "Host Environment"` + `art_X.jar` per component/package (597-632) | H (859) | H (1152) | Fabricated topology |
| 7 | profile | annotations + detected patterns | H (811-885) | H (999) | **S**: constant Class/ArchitecturePattern (json.rs:1511-1555) | |
| 8 | usecase | none | H: actors = classes ending in Controller/Service/App/Main/…; falls back to first class; ≤6 classes × ≤3 methods; every UC linked to the first actor (886-945) | H (1065) | H (1234) | Not requirements-derived |
| 9 | activity | real CFG edges, but **labels discarded** (`_label_text`, label_text_id=block_id; uma/behavioral/activity_diagram.rs:81-95). `label_texts` is never populated (only init at uma/types.rs:282, serializer.rs:677) | `if (eval_branch) then (yes)` with no `endif` (950-987), likely invalid PlantUML | H (1124) | linear chain ignoring edges, ≤6 nodes (871) | Labels are always `Block_N` |
| 10 | statemachine | **T**: 2-state template per class (uma/behavioral/state_machine.rs) | T (988) | T (1170) | T Uninitialized→Active→final (707) | Not real state extraction |
| 11 | sequence | from CG, but lifelines come from `HashMap::into_values` (non-deterministic) | actor declared `act_X`, messages use `part_X` (1037-1064), so a duplicate participant is created | H (1198) | falls back to a fabricated `execute()` chain (json.rs:656-686) | |
| 12 | communication | extractor no-op (uma/behavioral/communication_diagram.rs) | ≤4 classes chained with `invoke_X` (1083-1150) | H (1237) | = sequence with retitle (json.rs:1660-1669) | |
| 13 | interaction | extractor no-op (uma/behavioral/interaction_overview.rs) | T (1151) | T (1304) | **S** (1672) | |
| 14 | timing | extractor no-op | index-based synthetic time steps (1196-1252) | T (1357) | **S** (1584) | No real timing |
| 15 | cfg | ignores CFA | **T**: fixed BB0..BB3 per activity (1253) | T (1389) | **S**: OpenHeart's own pipeline stages (1748) | |
| 16 | dfg | ignores SSA | **S**: hardcoded `retries` variable (1339-1377) | S (1510) | **S**: v0_manifest…v6_scpg pipeline values (json.rs:1841-1849) | `retries`/`amount > 0` are copied from the fixture in tests/research_paper_theorems_tests.rs:108-110 |
| 17 | cdg | ignores CFA/dominators | **S**: hardcoded `amount > 0`, `saveOrder` (1378-1400) | S (1559) | **S** (1896) | |
| 18 | callgraph | ignores CGA edges | `HashSet` iteration order (non-deterministic); every edge labelled "CHA/1-CFA dispatch"; fake recursion self-loop (1401-1456) | same HashSet (mermaid.rs:1583-1606) | **S** (1970) | |
| 19 | robdd | ignores real BDD | **T** labelled with real sat_count/cyclomatic (1300) | T (1449) | **S** (2033) | |

Totals: JSON is constant for 8/19 keys (profile, timing, interaction, cfg, dfg, cdg, callgraph, robdd), and composite's root is hardcoded. The JSON for all 18 GraphIR exports carries the constant `compiler_hash: "0x83D2D2B2"` and `verified: true`, whatever the input (rg `compiler_hash` json.rs). Tests only check that `has_strategy(...)` returns true and that output is non-empty (tests/strategy_diagram_tests.rs:50,144). No test checks semantics.

## 5. Binary vs semantic outputs
- Binaries (main.rs:139-148): `corpus.tca`, `ast.bpa`, `symbols.sta`, `cfg.cfa`, `ssa.ssa`, `callgraph.cga`, `traceability.tra`, `paths.psa`, `metadata.uma`, `unified.scpg`. Magics: UMA `OPENHUMA` (uma/types.rs:10), PSA `OPENHPSA` (psa/types.rs:19), TRA (tra/types.rs:3), SCPG (scpg/types.rs:3).
- `unified.scpg` is not a merged graph. It mostly stores counts (scpg/serializer/mod.rs:53-150) and includes a `SystemTime::now()` timestamp (serializer/mod.rs:136; also ingestion/serializer.rs:80), so its bytes are non-deterministic.
- The hash chain is partly fake (tra/uml_link/hash_chain.rs:36-41). `bpa_hash` is the CRC of the *file count*, `cga_hash` is the CRC of the call-site count, `tca_hash` is the CRC of Debug output, and the BPA/CFA/SSA inputs are ignored (`_bpa`, `_cfa`, `_ssa`).
- "CFL reachability" (scpg/query/cfl.rs) is plain BFS with no call/return matching.
- Requirement: the skill must not claim upstream byte compatibility. Any binary the skill emits gets its own magic and version number, and its manifest states "OpenHeart-inspired, not interoperable". Semantic outputs (JSON, PUML, MMD) carry provenance per element (`grounded|heuristic|template|unavailable`) with real file and line spans.

## 6. Datasets, report schemas, templates
- **GraphIR schema** (json.rs:1-65): `diagram_type, title, compiler_hash, verified, nodes[{id,label,name,kind,stereotype,parent,nest_level,is_package,is_domain_tier,file,lines,fields,methods,instructions}], edges[{source,target,kind,label,arrow}]`. `compiler_hash` and `verified` are constants. `file` is fabricated and `lines` is empty. A faithful port keeps the field names but must compute or omit those values, never hardcode them.
- **ruthless_verify.py**: the "ground truth" is a regex class-name oracle that also counts `.py/.rs/.ts…` files the engine cannot parse. Precision is 1.0 when the engine produces nothing, and recall is 1.0 when the truth set is empty (ruthless_verify.py:252-253). The pass rule is F1 ≥ 0.999 with zero phantoms (ruthless_verify.py:435). It measures class *names only* and never checks diagrams.
- **scripts/test_ruthless_popular_datasets.py**:
  - The PlantUCD "50/50" test never runs OpenHeart. It regex-parses the dataset's own PUML (229-264) and logs every batch as passing (≈259).
  - Class names are rewritten (GHobbits→GenHobbits) to match truth (60-64).
  - The design-patterns test posts `github.com/iluwatar/java-design-patterns/{pdir}` URLs that cannot be cloned, so the server-side fallback analyses whatever directory is first (server.rs:466-485).
  - The Petclinic check passes on the substring "Artifact Type" (113).
- README claims of F1 = 1.0000 across languages, "100% symbol-grounded", "deterministic" and "zero-backend in-browser ingestion" are contradicted by §3, §4 and §1 (see README.md:57-66).
- Templates in the repo: only `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md` and `PULL_REQUEST_TEMPLATE.md`. There is no report template, so any REPORT template in the skill is skill-native.

## 7. Limitations & attribution
- Limitations in the paper's own section (docs/openheart_research_paper.tex:1303-1345) do not mention the synthetic exporters. The skill must document §3 and §4 itself.
- Attribution is inconsistent. LICENSE says "Copyright (c) 2026 OpenHeart Contributors" (MIT), Cargo.toml says `authors = ["OpenHeart Developers"]`, and README.md:44 says "Designed, created, and maintained solely by Ahmad Hassan (B-Ted)". The README.md:10 CI badge is a static "passing" image, not a live status. There is no THIRD_PARTY_NOTICES, even though the project depends on tree-sitter (MIT), sha2, memmap2, serde and others.
- Requirement: reproduce the MIT notice verbatim with the LICENSE holder ("OpenHeart Contributors"). Credit the README author as "per README". Pin the commit `0bf962fc…`. Do not upgrade the attribution to the stronger README wording.

## 8. Concrete requirements for honest standalone parity (no install/wrapper)
1. **Pipeline model**: reimplement the phase concepts (tokens → BP AST → symbols → CFG → SSA → CG → TRA → PSA → UMA) for Java first. Name the artifacts with upstream terms (TCA, BPA, STA, CFA, SSA, CGA, TRA, PSA, UMA, SCPG) but mark them non-interoperable.
2. **Language gate**: Java is full. JS is partial. Kotlin, TS, Py, Rust, Go, C++ and C# are refused or marked heuristic. Never echo the language list from server.rs:84.
3. **19 keys exactly** as in main.rs:261-279, using upstream spellings (`statemachine`, `usecase`, `callgraph`, `robdd`…). Any extras (e.g. `ast`) are flagged `upstream:false`.
4. **Per-diagram honesty**:
   - Derive cfg, dfg, cdg, callgraph and robdd from the skill's own CFG, SSA, CG and BDD data. Do not copy the upstream templates.
   - For statemachine, timing, interaction, communication and deployment, emit `unavailable`/`heuristic` with the reason when there is no evidence, rather than a template.
   - Usecase actors must be labelled "naming-heuristic".
5. **No constants**: no fixed `compiler_hash` and no `verified:true`. Hashes are computed over the real artifact bytes. Do not write wall-clock timestamps into deterministic artifacts.
6. **Determinism**: use sorted iteration everywhere, replacing the upstream HashSet and HashMap iteration (plantuml.rs:1401-1456, mermaid.rs:1583-1606, the sequence lifelines). Same input gives byte-identical semantic outputs.
7. **Cross-format consistency**: PUML, MMD and JSON for one key must come from the same graph. Upstream violates this for object, cfg, dfg and more.
8. **Valid syntax**: close PlantUML `if` blocks with `endif`, and use consistent participant aliases. Validate with a parser or render check where available.
9. **Source spans**: real `file`/`lines` for each node, never `{Name}.java`.
10. **Validation datasets**: do not reuse upstream "ruthless" numbers. If the skill reuses PlantUCD, iluwatar or petclinic, it must actually run its own analyzer against independent ground truth and report precision, recall and F1, counting an empty output as a failure.
11. **Docs**: include a "Divergences from upstream" table (this file's §4) and the attribution block from §7.

## 9. Observations about the in-progress skill (not reviewed in full; candidate review comes later)
- skills/engineering/openheart-analysis/assets/diagram-catalog.json has 20 entries, the 19 upstream keys plus `ast` (upstream:false), which matches requirement 3.
- SKILL.md points to `references/source-map.md` and `references/upstream/...`, which don't exist yet. Only data-contract, datasets, diagram-rules and workflow are present.
- templates/REPORT.md.tmpl:20 and datasets/scenarios.json:7 call ACT "a provisional activity alias". That is broadly consistent with the upstream badge (action node), but the wording should say it is a UI badge for action nodes, not an artifact.
- SKILL.md:58-59 says the MIT notice "belong[s] to Ahmad Hassan and OpenHeart Contributors". The LICENSE copyright line names only "OpenHeart Contributors", so the notice should be credited to that holder, with Ahmad Hassan credited separately as README-stated maintainer (see §7). The cited files `references/upstream/LICENSE.upstream` and `ATTRIBUTION.md` don't exist yet.
