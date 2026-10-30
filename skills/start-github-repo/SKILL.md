---
name: start-github-repo
description: "Render a GitHub repository skeleton for a TypeScript/Node or Cloudflare Workers project: README, AGENTS.md, LICENSE, CODE_OF_CONDUCT, CHANGELOG, issue forms and a PR template, hardened workflows, SECURITY.md, SUPPORT.md, CODEOWNERS, env examples and automation scripts. It also renders a PRD/TRD/TOGAF-ADM/WIREFRAME/DESIGN document spine with a traceability matrix and TDD gates. The agent-service profile adds the agent runtime contracts: a persona, human-in-the-loop triggers, safety filters and an eval dataset. Use when starting a new repository, scaffolding a project skeleton, adding the document spine to an existing repo, or auditing a repo against this template. Triggers on 'start a new repo', 'scaffold a repository', 'new project skeleton', 'set up repo structure', 'add PRD and TRD', 'repo template'. For standardizing an existing repo against an external preset catalog, use github-repository-setup instead."
license: MIT
compatibility: "Requires Python 3.9+ (stdlib only) for the bundled scripts. Optional: gh CLI for remote settings, Node 20+ for design.md linting."
metadata:
  version: 1.0.0
  entrypoint: "/start-github-repo"
  argument-hint: "[plan | docs | audit | <profile>]"
  disable-model-invocation: false
  profiles: "worker-service, ts-library, monorepo, docs-site, internal-tool, agent-service"
---

# Start GitHub repo

Scaffold a repository from templates bundled in `assets/templates/`.
No network fetch or external catalog is needed. Pinned versions live in `assets/versions.json`; never hardcode a
version number in prose.

## Modes

| Invocation | Behaviour |
|---|---|
| `/start-github-repo` | Interview → plan → confirm → scaffold → validate → summarize |
| `/start-github-repo plan` | Print the resolved file list and answers. Write nothing. |
| `/start-github-repo docs` | Emit only the document spine into an existing repo |
| `/start-github-repo audit` | Report missing or stale template artifacts. Never writes. |
| `/start-github-repo <profile>` | Skip the profile question |

## Workflow

1. **Classify.** If the target directory is non-empty, inspect it first and switch to merge
   behaviour: diff every file, never overwrite without showing the diff and getting approval.
2. **Interview.** Ask eight core questions, each with a default so `--defaults` can skip them:
    project name · description · profile · license · visibility · package manager · CoC reporting
    contact · release tooling. The `agent-service` profile always includes the agent runtime.
    Every other profile includes it only when the operator explicitly sets `emit_agentic_stack` to
    `true`; that answer defaults to `false`. Ask `database`, either `postgres` or `sqlite`, only
    when the agentic stack is on. Default it to `postgres`. Derive everything else.
3. **Plan.** Run `scripts/scaffold.py --dry-run` and show the tree plus every required secret by
   name and purpose. Get confirmation before writing.
4. **Scaffold.** `scripts/scaffold.py` renders `assets/manifest.json`. Use `--only docs` for docs
   mode, `--force` only after an approved diff. The `agentic-stack` group, labelled
    "Agent runtime and human-in-the-loop", applies to `agent-service` and to other profiles only
    when `emit_agentic_stack` is explicitly set to `true`. It emits the fifteen destinations listed
    in the agent runtime row of `README.md`. `database` selects the migration dialect. Use
    `--only agentic-stack` to select this group without changing its conditions.
5. **Validate.** Run `python3 scripts/validate_repo.py --root <target>` and
   `python3 scripts/validate_docs.py --root <target>`. When the agentic stack is on, run
   `python3 scripts/validate_repo.py --root <target> --require-agentic` for repository validation.
   Agentic checks otherwise run only when `config/hitl_triggers.json` is present. The flag makes
   a missing agentic stack an error. Both validators must exit 0.
6. **Hand off.** Report unresolved `TODO`/`[NEEDS CLARIFICATION]` markers, required secrets, and
   remote settings still to apply. Remote mutations are a **separate, individually confirmed step**.

## Hard rules

- Never overwrite a file without a diff and explicit approval.
- Never invent commands. Emit only scripts the chosen profile actually supports.
- A blocking trigger parks the session in `PENDING_HUMAN_APPROVAL` until a human resolves it. The
  scaffold must never pre-approve a trigger. A `NOTIFY_ONLY` trigger leaves the session running.
- The router checks the loop budget before evaluating any trigger. An exhausted session aborts
  instead of waiting for human approval.
- Never write a secret value. `.env.example` and `.dev.vars.example` carry empty values only.
- Every placeholder must be resolved or reported. Unresolved markers go in the final summary.
- Pin every third-party action to a full-length commit SHA and set least-privilege `permissions:`.
- File generation is local and safe. `gh api` ruleset creation, label sync and repository-settings
  changes each need their own approval.

## References

Read the one that answers the question in front of you. Do not read all of them.

| File | Answers |
|---|---|
| `references/document_spine.md` | Section-by-section specs for PRD, TRD, WIREFRAME, DESIGN, ADRs and the TOGAF ADM-lite `docs/architecture/` set |
| `references/agentic_stack_and_hitl.md` | How does the agent runtime constrain itself, and when does it stop for a human? |
| `references/github_platform.md` | Community health file placement, issue forms, PR templates, CODEOWNERS, rulesets, Actions hardening, Dependabot, Scorecard |
| `references/release_and_versioning.md` | changesets vs release-please, Keep a Changelog, SemVer, Conventional Commits, licensing and SPDX |
| `references/cloudflare_worker_repo.md` | wrangler config, `.dev.vars`, `wrangler types`, the Vitest plugin rename, secrets |
| `references/repo_hygiene_and_scripts.md` | `.gitignore`/`.gitattributes`/`.editorconfig`, env layering, secret scanning, hooks, `scripts/` conventions |
| `references/traceability_scheme.md` | The five ID families, the matrix, and commit/PR/test wiring |

## Scripts

All stdlib-only, deterministic, `--output {text,json}`.

| Script | Purpose |
|---|---|
| `scripts/scaffold.py` | Render `assets/manifest.json` into a target dir. `--dry-run --only --force` |
| `scripts/validate_repo.py` | Artifact presence plus structural traps (workflow permissions, SHA pins, ignored `.env`) |
| `scripts/validate_docs.py` | Required headings, ID formats, matrix integrity, unresolved clarification markers |
| `scripts/traceability.py` | Rebuild the matrix from PRD IDs, test names and commit scopes; report orphans both ways |

## Adjacent skills

- `github-repository-setup` audits an existing repository against an external preset catalog. Use it to
  standardize a repo that already exists; use this skill for day zero.
- Use `spec-driven-workflow`, `tdd`, `togaf-advisor` or `senior-architect` to deepen individual artifacts
  after scaffolding.
