# Independent adversarial review

**Scope:** branch `chore/professionalize-and-vendor-pstack` at `a995213`, compared with base `e3778af`.

## Verdict

**NO — not mergeable as-is. Changes are required.** The branch adds useful governance and reproducible imports, but the new import engine follows upstream symlinks and can copy runner-local files into a generated pull request. It also accepts destination traversal, destroys sibling mappings when mappings overlap, and leaves stale trees when mappings are removed. The linter is not a YAML parser and can false-pass malformed or overlong frontmatter; its baseline can suppress a completely new violation placed at an old path. Public-release licensing is also incomplete: verbatim Matt Pocock-derived material lacks the required MIT notice locally/consolidated, and the job-hunt import is described as MIT while redistributing OFL fonts. The architecture report contains several demonstrably wrong counts. These are release blockers, not polish.

## Findings

### 1. BLOCKER — the vendor sync follows upstream symlinks and can publish runner-local files

**Location:** `scripts/sync_vendor.py:416-418`, `scripts/sync_vendor.py:431-433`; scheduled use at `.github/workflows/sync-vendored-skills.yml:86-90`.

`shutil.copytree()` uses its default `symlinks=False`, so an untrusted moving upstream can add a symlink to a predictable runner path. The sync dereferences it and commits the bytes as a regular file. The checkout step also leaves credentials persisted by default in this workflow, making a predictable `.git/config` a particularly dangerous target.

**Evidence:** a scratch upstream contained `runner-secret.txt -> /etc/hostname`; the real `process_source(..., apply=True)` produced:

```text
source is symlink True
vendored is symlink False
vendored bytes equal /etc/hostname True
vendored content repr 'space-sandbox\n'
```

**Recommended fix:** reject every symlink using `lstat()` before digest or copy; do not dereference. Set `persist-credentials: false` in the sync checkout, and pass credentials only to the PR step. Add a regression test using both file and directory symlinks.

### 2. BLOCKER — redistributed Matt Pocock material lacks the required MIT notice

**Location:** `skills/engineering/caveman/skills/caveman/SKILL.md:19`, `skills/engineering/write-a-skill/skills/write-a-skill/SKILL.md:15`, `LICENSE:28-29`, `THIRD_PARTY_NOTICES.md`.

Both trees say Matt Pocock content/workflows are “preserved verbatim” under MIT. The upstream licence is MIT, copyright 2026 Matt Pocock. Neither tree contains a full upstream licence/notice, and `THIRD_PARTY_NOTICES.md` does not list Matt Pocock. A name/link in prose is not the MIT copyright-and-permission notice required in copies. This directly contradicts the root assertion that every redistributed work is listed with its licence and author.

**Evidence:**

```text
$ gh api repos/mattpocock/skills/contents/LICENSE ... | head -3
MIT License

Copyright (c) 2026 Matt Pocock
$ grep -n 'Matt Pocock' THIRD_PARTY_NOTICES.md
# no output
```

**Recommended fix:** add the complete upstream MIT notice beside each derived bundle and a commit-pinned consolidated-notice entry; audit whether other copied files share that provenance.

### 3. BLOCKER — manifest destinations can escape the repository root

**Location:** `scripts/sync_vendor.py:375-376`, `386-395`, `490-500`.

`dest`, `from`, and `to` are only stripped of `/`; `..` is not rejected and resolved paths are never checked to remain under the repository/checkout. A crafted `dest: ../escaped` writes and deletes outside `REPO_ROOT`. Validation notices the missing generated metadata but does not reject the traversal itself.

**Evidence:** real `process_source()` against a scratch repository:

```text
validation errors = ['[evil] `../escaped/ATTRIBUTION.md` is missing; run --sync', ...]
escaped path exists = True
escaped outside repo = True
```

**Recommended fix:** reject absolute paths, `..`, empty/`.` segments, and platform-specific drive/UNC forms. Resolve every source and target and require `is_relative_to()` its designated root before reading, deleting, or writing.

### 4. MAJOR — overlapping mappings destructively clobber sibling support trees

**Location:** `scripts/sync_vendor.py:391-433`; schema validator at `471-535`.

A support mapping such as `guides -> guides` followed by a skill collection `skills -> ""` is legal. The second mapping treats every child directory under the destination root as an owned skill and deletes `guides`. Order changes the result. This is exactly the generalized mapping shape the branch introduced, and no validator rejects nested/overlapping `to` paths.

**Evidence:**

```text
=== overlap/order clobber probe ===
support-first then root-sweep: guides exists = False
alpha exists = True attribution exists = True
```

**Recommended fix:** reject overlapping destination ownership, or construct the complete expected destination in a temporary directory and atomically replace it. Never let one mapping infer ownership from all existing sibling directories.

### 5. MAJOR — removing a `paths` entry leaves stale redistributed content forever

**Location:** `scripts/sync_vendor.py:391-440`.

The synchronizer only reconciles mappings that remain in the current manifest. If `guides -> guides` is removed, the old `guides/` tree is never visited or deleted. `--validate-manifest` also cannot detect it. This defeats “manifest-driven” ownership and can leave withdrawn or newly unlicensed content published.

**Evidence:**

```text
=== stale removed mapping probe ===
removed mapping guides still exists = True
```

**Recommended fix:** stage and replace the whole source destination from the current manifest, or persist a generated ownership inventory and delete previously owned paths absent from the new plan.

### 6. MAJOR — malformed and multi-line YAML can false-pass the linter

**Location:** `scripts/lint_skills.py:66-87`.

The parser explicitly is “not a YAML parser.” It reads `description: |` as the one-character string `|`, `description: >` as `>`, and accepts syntactically invalid YAML such as an unterminated flow sequence. Consequently SK006 can be bypassed by any block scalar and invalid skills can pass all checks. Nested `metadata:` is reduced to an empty scalar rather than parsed.

**Evidence:** the actual parser and linter on isolated scratch skills:

```text
valid folded => {'name': 'foo', 'description': '>', 'metadata': ''}
malformed YAML => {'name': 'foo', 'description': '[unterminated', 'metadata': ''}
overlong block scalar => {'name': 'foo', 'description': '|'}
malformed YAML findings = []
1100-char block description findings = []
```

**Recommended fix:** use a safe YAML parser with a pinned dependency, or implement a strict supported subset that rejects unsupported YAML constructs and malformed documents. Test block/folded scalars, quoted colons, comments, sequences, and nested maps.

### 7. MAJOR — the baseline can launder a new violation at an old path

**Location:** `scripts/lint_skills.py:190-197`, `214-238`; `scripts/skill_lint_baseline.json`.

Suppression identity is only `RULE::path`. Replacing a baselined skill with unrelated content that violates the same rule is treated as accepted debt. CI therefore does not reliably “block new debt.”

**Evidence:** a baselined name mismatch was replaced by a different wrong name at the same file path:

```text
old finding key = ['SK004::skills/foo/SKILL.md']
replacement at same path normal exit = 0
1 skill(s) checked. 0 error(s), 0 warning(s) in vendored trees, 1 accepted by baseline.
replacement strict exit = 1
error  SK004  skills/foo/SKILL.md: `name: entirely-new-wrong-name` does not match directory `foo`
```

**Recommended fix:** baseline a stable fingerprint of rule, path, normalized message, and/or relevant content; fail when a baselined file changes without explicitly refreshing the baseline.

### 8. MAJOR — consolidated licence claims are materially incomplete

**Location:** `LICENSE:25-30`, `README.md:159-160`, `THIRD_PARTY_NOTICES.md:1-28`.

The root licence says every redistributed work is in `THIRD_PARTY_NOTICES.md`, but many explicit local attribution records are absent. Confirmed omissions include VoltAgent/awesome-design-md, nextlevelbuilder/ui-ux-pro-max-skill, domelic/github-repository-setup, pbakaus/impeccable, deeparchi-ai/togaf-skill, bhubanmm/togaf-advisor, and Matt Pocock/skills. Some have a nearby licence, but the branch’s categorical consolidated-notice claim is false and the CI validator does not inventory them.

**Evidence:**

```text
$ grep -nE 'VoltAgent|nextlevelbuilder|domelic|pbakaus|deeparchi|bhuban|Matt Pocock' THIRD_PARTY_NOTICES.md
# no output
$ find skills -type f \( -iname 'LICENSE*' -o -iname 'NOTICE*' -o -iname 'ATTRIBUTION.md' \) | wc -l
87
```

**Recommended fix:** generate notices from a complete machine-readable inventory of all third-party trees, not two manifest sources plus a hand-maintained legacy table. Make CI reconcile every attribution/licence marker against that inventory.

### 9. MAJOR — the job-hunt collection is not solely MIT, despite generated claims

**Location:** `skills/job-hunt/templates/fonts/OFL.txt:1-19`, `skills/job-hunt/ATTRIBUTION.md:10`, `THIRD_PARTY_NOTICES.md:12`.

The import redistributes four Gelasio TTFs under SIL Open Font License 1.1. The local OFL text is present, but the collection attribution and consolidated notice describe the whole import only as MIT and do not name Gelasio, its authors, or OFL. Generated per-tree provenance repeats “Upstream licence | MIT.”

**Evidence:**

```text
skills/job-hunt/templates/fonts/OFL.txt:1:Copyright 2022 The Gelasio Project Authors
skills/job-hunt/templates/fonts/OFL.txt:13:The goals of the Open Font License (OFL)...
THIRD_PARTY_NOTICES.md:12:... job-hunt-skills ... MIT ...
```

**Recommended fix:** support multiple/per-path licences in the manifest, list Gelasio/OFL explicitly, and stop rendering one licence as if it covers every imported file.

### 10. MAJOR — the “fortnightly” ISO parity gate has 21-day gaps

**Location:** `.github/workflows/sync-vendored-skills.yml:6-8`, `46-62`; `AGENTS.md:80-81`; `docs/ARCHITECTURE_REVIEW.md:263-264`.

Even ISO-week parity is not a fixed 14-day cadence across years with week 53. Iterating every Monday from 2026 through 2036 finds two three-week gaps. There are no 7-day double-runs, but “once every two weeks” is still false.

**Evidence:**

```text
runs 286 min_gap_days 14 max_gap_days 21
gap_counts {14: 283, 21: 2}
ANOMALY 2026-12-21 ... week=52 -> 2027-01-11 ... week=2 gap_days 21
ANOMALY 2032-12-20 ... week=52 -> 2033-01-10 ... week=2 gap_days 21
```

**Recommended fix:** persist a last-success timestamp and run when at least 14 days elapsed, use a true every-14-days external trigger, or document the schedule as “approximately fortnightly with occasional 21-day gaps.”

### 11. MAJOR — the scheduled PR step names labels that do not exist

**Location:** `.github/workflows/sync-vendored-skills.yml:142-159`.

The action asks GitHub to apply `automation` and `vendored-skills`, but neither repository label exists. This creates an avoidable failure point in the first scheduled PR path, which has not been exercised on the branch.

**Evidence:**

```text
$ gh api repos/bughunt8/skills/labels --paginate --jq '.[].name' | sort
bug
documentation
duplicate
enhancement
good first issue
help wanted
invalid
question
wontfix
```

**Recommended fix:** create both labels before enabling the workflow, or remove `labels:` and add a preflight that verifies all repository settings required by the job.

### 12. MAJOR — job-hunt’s preferred runtime commands point to files that were not vendored

**Location:** `skills/job-hunt/skills/get-started/SKILL.md:113,149`; `_shared/state-layer.md:39,46,276,306`; multiple skill files; limitation at `skills/job-hunt/ATTRIBUTION.md:46`.

The import omits `scripts/scaffold-state.mjs`, `profile-strength.mjs`, and `export-documents.mjs`, yet `get-started` calls the missing scaffolder the “Preferred” path and the shared contract says skills run it. Native fallbacks reduce harm, and the attribution discloses the omission, but a user following the primary instruction gets a guaranteed file-not-found. This gap is broader than DOCX/PDF export: scaffolding and profile strength are ordinary Markdown-state operations.

**Evidence:** 28 references were found to the three absent scripts; representative lines are:

```text
get-started/SKILL.md:113: Preferred: run node "{job_hunt_skills_root}/scripts/scaffold-state.mjs"
_shared/state-layer.md:46: ... the skill runs .../scripts/scaffold-state.mjs
get-started/SKILL.md:149: ... /scripts/profile-strength.mjs
$ test -d skills/job-hunt/scripts; echo $?
1
```

**Recommended fix:** vendor and test the non-export helpers, or patch the vendored integration so native operations are primary and missing scripts are never attempted. If content must remain verbatim, mark the collection as capability-degraded at the point of use, not only in attribution.

### 13. MAJOR — the architecture review mixes base, intermediate, and final snapshots

**Location:** `docs/ARCHITECTURE_REVIEW.md:3,16,68-77,128,201-211`; `AGENTS.md:8,33`; `README.md:166`.

The report says it reviewed base `e3778af`, then calls the repository 459 skills. Base has 419. The intermediate pstack-only commit has 459. Final branch has 470 physical `SKILL.md` files; the linter reports 469 because it ignores one fixture. The report’s before/after table says 459→469, AGENTS says 469, and generated README says 470. Its “67 metadata violations measured with `--strict`” table includes an ignored SK001 that strict mode does not report; the actual command reports 66 errors and two vendored warnings.

**Evidence:**

```text
base SKILL 419 markdown 1912 workflow_yml 0 top_dirs 20
branch SKILL 470 markdown 2092 workflow_yml 2 top_dirs 22
python3 scripts/lint_skills.py --strict:
469 skill(s) checked. 66 error(s), 2 warning(s) ... EXIT=1
```

**Recommended fix:** define each metric precisely (physical files, linted skills, parsed names), bind every table to a commit, and regenerate all prose after the final import. Do not count ignored fixtures as strict findings.

### 14. MAJOR — the documented “386 links, all resolve” result is false

**Location:** `docs/ARCHITECTURE_REVIEW.md:210-211,231-232,303-304`; reproducer at `314+`.

Running the report’s own regex finds 358 relative-link matches, not 386, with one unresolved upstream placeholder. A more careful checker reaches the same substantive result: pstack 226 checked/225 resolved and job-hunt 132/132. The known placeholder may be acceptable as vendored content, but the numeric and zero-unresolved claims are not.

**Evidence:**

```text
checked 358 resolved 357 unresolved 1
('skills/pstack/why/references/synthesizer-prompt.md', 'url')
```

**Recommended fix:** replace prose counts with output from a checked-in link checker, explicitly exempt the known placeholder with path/reason, and run the checker in CI and sync jobs.

### 15. MAJOR — manifest validation verifies declarations, not licence truth or completeness

**Location:** `scripts/sync_vendor.py:471-535`; claims at `AGENTS.md:22-25`, `CONTRIBUTING.md:40-71`, `.github/workflows/ci.yml:46-51`.

The validator checks non-empty author/licence strings, generated file presence, and some selection invariants. It does not require `license_path` (`483` omits it), parse a copyright notice, compare `LICENSE.upstream` with an upstream file, inventory legacy third parties, reject overlapping paths, reject traversal, or identify secondary licences. A fabricated `author: x`, `license: MIT` is structurally sufficient. Documentation says CI rejects imports without correct licence/author/pin attribution, which is stronger than the code.

**Evidence:** current validation says:

```text
2 vendored source(s) checked, 0 problem(s)
```

while findings 2, 3, 8, and 9 remain true.

**Recommended fix:** narrow the documentation claim, require and validate licence-path metadata, reconcile a complete third-party inventory, and add online verification in the scheduled trusted context.

### 16. MINOR — `tree_digest` misses security- and behavior-relevant changes

**Location:** `scripts/sync_vendor.py:108-128`.

The digest hashes only regular file path/content. It ignores modes, empty directories, symlink identity, and symlinked directories. An executable-bit change, empty-directory change, or added directory symlink can be invisible to `--check`; a symlink and regular file with the same bytes/path can digest identically.

**Evidence:**

```text
mode + empty-dir digests equal = True
extra symlink-directory invisible = True
symlink-file vs regular same path/content digests equal = True
```

**Recommended fix:** reject symlinks, and hash entry type, relative path, normalized mode/executable bit, empty directories, and content.

### 17. MINOR — `generate_index.splice()` silently corrupts mismatched markers

**Location:** `scripts/generate_index.py:109-114`.

If BEGIN exists but END is missing, the function appends a second complete block rather than failing. That leaves two BEGIN markers and one END marker; later runs replace from the first BEGIN through the single END, potentially swallowing unrelated content.

**Evidence:**

```text
orphan BEGIN + real rendered block => BEGIN count 2 END count 1
'before\n<!-- BEGIN ... -->\norphan\n\n<!-- BEGIN ... -->\nnew\n<!-- END ... -->\n'
```

**Recommended fix:** require exactly one matched marker pair in the correct order; exit 2 on missing, duplicate, or reversed markers.

### 18. MINOR — explicit empty `include` means “include everything”

**Location:** `scripts/sync_vendor.py:131-139`.

`include or ["*"]` conflates absent/default with an explicitly empty list. A maintainer trying to disable all imports with `include: []` gets all children instead, a dangerous fail-open.

**Evidence:**

```text
explicit include=[] yields ['alpha', 'beta'] (expected [] for explicit empty selection)
```

**Recommended fix:** default only when the key is absent; either treat `[]` as none or reject it explicitly.

### 19. MINOR — “tracked skills: 12” is wrong for the 11-skill job-hunt import

**Location:** `scripts/sync_vendor.py:397-403,441-463,631-637`.

The `skills` mapping counts every child directory, including `_shared`, although `_shared` has no `SKILL.md`. `--check` therefore reports 12 tracked skills while README and the actual tree correctly report 11.

**Evidence:**

```text
[job-hunt] -> skills/job-hunt
  tracked skills  : 12
$ find skills/job-hunt -name SKILL.md | wc -l
11
```

**Recommended fix:** call these “selected child directories,” or count only `_has_skill()` children and model `_shared` as support.

### 20. MINOR — branch automation is intentionally nonfunctional, and CODEOWNERS is unenforced

**Location:** `.github/workflows/sync-vendored-skills.yml:161-176`; `.github/CODEOWNERS`; `docs/ARCHITECTURE_REVIEW.md:273-284`.

Current repository settings have auto-merge disabled, no branch protection, and no rulesets. The workflow will warn rather than merge, which is a safe failure and is acknowledged in the report. However, CODEOWNERS currently enforces nothing, and the claimed automated “PR then merge” objective is not delivered. A human can also merge without CI/review.

**Evidence:**

```json
{"allow_auto_merge":false,"default_branch":"main","private":false,"visibility":"public"}
{"message":"Branch not protected", "status":"404"}
[]
```

**Recommended fix:** before advertising automation as operational, protect `main`, require CI and code-owner review for sensitive paths, enable auto-merge, and test one end-to-end sync PR.

### 21. MINOR — unquoted workflow argument expansion permits option injection

**Location:** `.github/workflows/sync-vendored-skills.yml:80,83,89-90`.

A manual `source` input is formatted into `SOURCE_ARG` and expanded unquoted. Shell metacharacters in the value are not reparsed as operators, so this is not arbitrary command execution, but whitespace can create extra CLI arguments/options. The input should be one source ID, not an argument vector. On scheduled events, absent `inputs.source` evaluates to the intended empty string; that part is clean.

**Evidence:** the workflow literally executes:

```yaml
SOURCE_ARG: ${{ inputs.source && format('--source {0}', inputs.source) || '' }}
run: python3 scripts/sync_vendor.py --sync ${SOURCE_ARG}
```

**Recommended fix:** store only `SOURCE`, validate it against manifest IDs, and use a Bash array: `args=(); [[ -n $SOURCE ]] && args+=(--source "$SOURCE"); python3 ... "${args[@]}"`.

### 22. MINOR — the CONTRIBUTING link-check snippet silently checks zero files

**Location:** `CONTRIBUTING.md:50-63`.

The snippet contains literal `skills/<dest>/**/*.md`. Copied exactly, it exits 0 and prints “0 unresolved” because the glob matches no files. That looks like success and is unacceptable for a verification recipe. The architecture version does match files but exposes finding 14.

**Evidence:**

```text
$ [run CONTRIBUTING snippet literally]
0 unresolved
```

**Recommended fix:** make destination a required CLI argument, count matched files and links, and fail if either count is zero. Prefer a checked-in script used by CI.

### 23. MINOR — README says its commands are the same checks as CI, but substitutes a network drift check

**Location:** `README.md:146-155`; actual CI at `.github/workflows/ci.yml:38-51`; `AGENTS.md:30-39`.

README’s three commands include `sync_vendor.py --check`; CI uses offline `--validate-manifest`. AGENTS and CONTRIBUTING list the actual CI set. The README command currently passes, but it performs network clones and has different semantics/exit behavior.

**Evidence:**

```text
README:      lint; generate_index --check; sync_vendor --check
ci.yml:      lint; generate_index --check; sync_vendor --validate-manifest
```

**Recommended fix:** label the offline CI set accurately and list network drift as an additional optional check.

### 24. MINOR — the integration review overstates the pre-existing career gap

**Location:** `README.md:99-104`.

“No name collisions” is correct: job-hunt adds no duplicate frontmatter names, and the repository remains at 16 duplicate names/32 files before and after. But “nothing that helps a person get hired” is too absolute. The base already had `andreessen` for career bets, `dossier` with LinkedIn/person research, social-content/social-media-manager for LinkedIn presence, CHRO/VPE hiring workflows, and interview-oriented tools. These are adjacent, not substitutes for resume/cover-letter skills, so the import still fills a real gap; the overlap analysis was simply too shallow.

**Evidence:** base-tree search returned, among others:

```text
skills/productivity/andreessen/... : career
skills/research/dossier/... : linkedin
skills/marketing-skill/skills/social-content/... : linkedin
skills/c-level-advisor/skills/chro-advisor/... : career,hiring
skills/engineering/skills/interview-system-designer/... : hiring,interview
```

**Recommended fix:** say the repo lacked a coherent job-seeker application workflow, then document routing boundaries with adjacent research, social, career-decision, and employer-side interview skills.

### 25. NIT — generated Python bytecode is committed

**Location:** `scripts/__pycache__/generate_index.cpython-314.pyc`, `lint_skills.cpython-314.pyc`, `sync_vendor.cpython-314.pyc`; `.gitignore`.

Three interpreter-specific binary cache files are in the 244-file branch diff. They are not source, are non-reviewable, and will churn across Python versions.

**Evidence:**

```text
scripts/__pycache__/generate_index.cpython-314.pyc | Bin 0 -> 8572 bytes
scripts/__pycache__/lint_skills.cpython-314.pyc    | Bin 0 -> 17088 bytes
scripts/__pycache__/sync_vendor.cpython-314.pyc   | Bin 0 -> 40234 bytes
```

**Recommended fix:** remove them from version control and ignore `__pycache__/` and `*.py[cod]`.

## Independently measured numeric claims

| Author’s claim | Independent measurement | Verdict |
|---|---:|---|
| Base/review-time skills: 459 | Base `e3778af`: **419** physical `SKILL.md`; pstack-only intermediate: 459 | Wrong snapshot attribution |
| Final skills: 469 | **470** physical files; **469** linted because one fixture is ignored | Ambiguous/wrong unless defined |
| pstack imported skills: 40 | **40** | Correct |
| job-hunt imported skills: 11 | **11** `SKILL.md`; sync misleadingly prints 12 selected children | Skill count correct |
| Duplicate names: 16 names used twice / 32 findings | **16 distinct names, 32 files**, unchanged base→branch | Correct |
| Strict metadata violations: 67 | Actual strict: **66 errors + 2 vendored warnings**; ignored SK001 is absent | Wrong |
| Self-audit on base: 8 errors, 2 warnings | **8 errors, 2 warnings**, exit 1 | Correct |
| Self-audit on branch: clean | **0 errors, 0 warnings**, exit 0 | Correct |
| Vendored links: 386, all resolve | Exact documented regex: **358 checked, 357 resolve, 1 known placeholder** | Wrong |
| Markdown files at review time: 1,912 | Base: **1,912**; branch: 2,092 | Correct for base |
| Workflows after branch: 3 (table implication) | **2** workflow YAML files | Wrong |
| Top-level skill directories after branch: 22 | **22** | Correct |
| Regular lint | **469 checked; 0 errors; 2 vendored warnings; 66 suppressed; exit 0** | Matches behavior |
| Strict lint | **469 checked; 66 errors; 2 warnings; exit 1** | Docs miscount |
| Index check | Up to date, exit 0 | Correct |
| Manifest validation | 2 sources, 0 reported problems, exit 0 | Correct output; inadequate guarantees |
| Upstream drift check | No drift, exit 0; reports pstack 40/job-hunt 12 | Correct drift status, wrong label/count |
| Fortnight cadence | 2026–2036 gaps: 283×14 days, **2×21 days** | Wrong as fixed cadence |

## What the author got right

- All five requested verification commands run and have coherent exit behavior: normal lint, index check, manifest validation, and drift check return 0; strict lint returns 1 for the known backlog.
- The base self-audit really was 8 errors and 2 warnings, and the branch self-audit is clean.
- pstack and job-hunt upstream repository licences are MIT. The pstack mirror’s licence is also present at the original `cursor/plugins/pstack` source and matches Lauren Tan’s MIT notice, so the mirror-of-a-mirror concern is substantially addressed.
- The root MIT text is expressly scoped to original repository content, so it does not itself relicense upstream work. Using the maintainer’s legal name “Ronald Ng” rather than the GitHub handle `bughunt8` is not inherently defective; the unresolved question is which files are actually original and owned by that copyright holder.
- The three pinned action SHAs are real and exactly match `actions/checkout v7.0.1`, `actions/setup-python v7.0.0`, and `peter-evans/create-pull-request v8.1.1`.
- `permissions:` are sensibly read-only by default and elevated only for the sync job. The PR `add-paths` list covers the intended writes (`skills/`, `THIRD_PARTY_NOTICES.md`, `README.md`). Scheduled-event `inputs.source` falls back to empty as intended.
- Job-hunt relative Markdown links all resolve; pstack has only the already-known `](url)` placeholder. No additional broken Markdown path was found.
- No direct conflict was found between vendored instructions and AGENTS’ repository editing rules. There are portability assumptions (Cursor paths, Task subagents, MCPs), but SUPPORT/attribution disclose several of them.
- The newly authored non-vendored prose had **0 concrete violations** for the requested unslop patterns after excluding quoted rule examples and standard Code of Conduct labels: no new em dashes, curly quotes, decorative emoji, banned “landscape/testament/crucial/delve” usage, title-case headings, or defensible forced-rule-of-three instance. The bold imperative bullets add new detail rather than merely restating their labels.

## Documentation snippet execution

- README required commands: all passed today, but its drift command is not the same as CI.
- AGENTS and CONTRIBUTING three-check blocks: all passed.
- Architecture strict lint: exited 1 as expected for backlog, but the reported count is wrong.
- Architecture link snippet: exited 0 while printing `1 unresolved`; therefore its prose conclusion is wrong and the snippet itself does not fail on bad links.
- CONTRIBUTING `<dest>` snippet: exited 0 and falsely printed `0 unresolved` because it matched no files.
- SECURITY and SUPPORT contain no executable bash snippets.
- Example commit-message and tree-layout fences are illustrative text, not shell commands; treating them as executable would be unreasonable.

## Could not verify

- I did not execute an actual scheduled GitHub Actions run or create a test PR because that would mutate the public repository. Therefore action behavior after the missing-label step, PAT availability, and end-to-end auto-merge behavior remain unverified.
- I could not prove legal ownership of every line of the pre-existing 419-skill corpus. The local inventory proves the consolidated claim is incomplete; a full provenance audit requires source-by-source historical comparison.
- I could not verify whether every upstream project has the right to license all material it republishes. I did verify that `cursor/plugins/pstack` carries the same MIT licence as the pstack mirror.
- The claims “651 scripts” and “44 MB” are snapshot-sensitive and not tied to a quoted machine command in the report. Current/base filesystem definitions (whether generated, `.git`, binaries, and extensions count) are unspecified, so these are not reproducibly verifiable as written.
- GitHub expression behavior for every unusual manually supplied string was reasoned from the workflow and shell semantics rather than executed on a hosted runner.
