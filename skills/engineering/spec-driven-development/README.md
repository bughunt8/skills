# Spec-driven development

Portable skill with nine Markdown artifacts, phased human review, EARS behavior, invariant tests, safe observation design, drift evidence, and bounded one-task builds. Read [SKILL.md](SKILL.md) for routing, [artifact contract](references/artifact-contract.md) for templates/mappings, [commands](references/commands.md) for phase rules, [EARS](references/ears.md) for syntax, [review](references/review.md) for authorization, and [source analysis](references/source-analysis.md) for all three sources and adaptations.

## Install

Copy the entire directory, not only SKILL.md, into the host's skill directory. For example, install as `.claude/skills/spec-driven-development/` or `skills/engineering/spec-driven-development/` in bughunt8/skills. Use the same canonical skill name. No pip/npm install is needed. Python 3.10+ and its standard library are enough for the bundled checker and tests.

Standalone installations have no repository-absolute runtime dependencies. In bughunt8/skills, the adapter can use the unchanged existing `skills/engineering/skills/spec-driven-workflow/scripts/test_extractor.py`; this optional code must be from the trusted installed repository. It only parses AC-N/GWT, not EARS. If absent, standalone GWT extraction is used. Neither the combined RFC2119 spec_generator nor spec_validator is bundled or required, and neither validates this split contract.

## Syntax and exits

Run from any cwd with an explicit existing project root. Flags before the subcommand are global.

```text
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project scaffold
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project --feature preview scaffold
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project lint --stage spec
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project lint --stage plan
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project lint --stage tasks
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project lint --stage ready
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project snapshot
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project extract
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project analyze --review /project/review.json
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project gate --approval /project/.specs/reviews/human-approval.json --task TASK-1
python3 /path/to/spec-driven-development/scripts/sdd.py --root /project gate --approval /project/.specs/reviews/human-approval.json --purpose verify --task TASK-1
```

These path placeholders describe syntax; substitute actual installed paths. Exit 0 means the requested structural operation succeeded. Exit 2 means usage, malformed/missing content, blocked review, or stale/missing approval. There is no completeness score and no "warning implies approved" fallback.

`scaffold` creates the nine draft files plus INDEX/CROSS_ANALYSIS, and CAPABILITY_MAP only in multi-feature mode. It preflights targets, rejects unsafe feature IDs and symlink components, and refuses to overwrite files. It reuses existing multi-feature globals. Scaffold output is deliberately invalid for lint until filled.

`spec`, `plan`, and `tasks` stages check progressively more selected artifact content. All authoritative mapped files must exist. `tasks` permits future test paths; `ready` checks existing owned files and test declarations. `extract` returns AC intent plus `standalone-GWT` or `legacy-SpecParser` mode. `analyze` uses all task paths for pre-build and the selected task plus completed tasks for post-build, binds reviewed code/tests and evidence, and appends analysis. `gate` checks final record structure and hashes, not human identity, prior phase approvals, or code correctness.

## Runnable examples

From this directory, these are complete shell commands with stated cwd and expected exit:

```bash
# Cwd: installed spec-driven-development directory. Expected exit: 0.
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Same cwd. Expected exit: 0, structural pass for the filled example.
python3 scripts/sdd.py --root "$PWD/examples/minimal" lint --stage ready

# Same cwd. Expected exit: 0, three AC intent records plus parser mode.
python3 scripts/sdd.py --root "$PWD/examples/minimal" extract

# Same cwd initially; subshell cwd becomes examples/minimal. Expected exit: 0.
(cd examples/minimal && python3 -m unittest discover -s tests -v)

# Same cwd. Make a new disposable project, never point this at existing docs.
# Scaffold expected exit: 0; draft lint expected exit: 2.
DEMO="$(mktemp -d)"
DEMO="$(cd "$DEMO" && pwd -P)"  # physical path if /var or /tmp is symlinked
python3 scripts/sdd.py --root "$DEMO" scaffold
python3 scripts/sdd.py --root "$DEMO" lint --stage tasks
```

No real approval is supplied or implied by the green example. The suite includes a clearly labelled simulated approved fixture that passes the structural gate, as well as an unapproved fixture that fails. Synthetic records exist only in temporary test projects and do not authorize live builds. Tests also show draft rejection, malformed EARS, stale specs/code/tests/evidence/approvals, missing refs/paths/markers, cycles, duplicates, symlinks, sparse docs, best-effort how leakage, planned test paths, and no command execution by the checker.

To try analysis without modifying the bundled example, copy it to another project using a reviewed copy command. Fill a real review record following [review protocol](references/review.md), run analyze, then have the authorized human create an immutable authorization record. Compute the review, CROSS_ANALYSIS, and verification hashes with `sha256sum` or another trusted local hashing utility. Do not generate a real approval from the test helper.

## Optional older workflow

From a bughunt8/skills checkout root, the existing combined-format scripts may still be run for that format:

```bash
# Cwd: repository root. Expected exit: 0, stdout only, no file overwrite.
python3 skills/engineering/skills/spec-driven-workflow/scripts/spec_generator.py --name "Preview" --description "Local preview"

# Cwd: repository root. Supply an actual reviewed combined RFC2119 file.
# Expected exit: 0 only for a completed strict-valid combined doc; draft often exits 2.
python3 skills/engineering/skills/spec-driven-workflow/scripts/spec_validator.py --file docs/combined-spec.md --strict --json

# Cwd: repository root. Expected exit: 0 only if its AC/edge cases parse without warnings.
python3 skills/engineering/skills/spec-driven-workflow/scripts/test_extractor.py --file docs/combined-spec.md --json
```

Do not concatenate the nine files and claim the legacy score validates them. The existing extractor may generate stubs for pytest/jest/go-test, but generated NotImplemented exceptions are not the real behavior red required here. Its optional use is documented, not a standalone dependency.

## Repository checks after deliberate integration

From the bughunt8/skills checkout root, with this candidate placed at `skills/engineering/spec-driven-development`, expected exit is 0 for each command when the candidate and repository satisfy their contracts:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/engineering/spec-driven-development/tests -p 'test_*.py' -v
agentskills validate skills/engineering/spec-driven-development
python3 scripts/lint_skills.py --self-test
python3 scripts/lint_skills.py
python3 scripts/check_links.py --path skills/engineering/spec-driven-development
python3 scripts/check_solutions.py
python3 scripts/audit_third_party.py
```

These are manual repository validation instructions, not actions performed by runtime tooling. Respect repository-authoring/import policy and existing baselines; do not suppress findings, alter vendor trees, install dependencies, commit, post, or deploy automatically.

## Review limits

The implementation-detail filter is heuristic. Empty-content and placeholder checks are bounded. A named test declaration is not assertion coverage or discovery. Hash freshness covers declared authoritative/reviewed files, not undeclared changes. Local authorizer text cannot authenticate consent, and append-only behavior does not stop a hostile filesystem editor. Binary evidence must be nonempty and at most 20 MB per file; larger video evidence needs a separately reviewed external record. Human semantic, code, security, actual-test, and UI review remains necessary. No claim of deterministic code generation or formal safety is made.

Checked files must be regular independent files without symlink components or multiple hardlinks; linked checkouts and package-store files may therefore need independent copies. Completed receipts bind task definition rows separately from execution-log progress. A shared-owned-file change requires a new predecessor post-build review and renewed human verification before downstream authorization; see the review protocol for recovery.
