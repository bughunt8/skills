# GitHub Platform Mechanics

Answers one decision: **which files go where, in what syntax, and which platform settings must be
applied outside version control.**

Evidence note: frequencies below come from a file-by-file survey of 14 production repositories
(`cloudflare/workers-sdk`, `honojs/hono`, `vercel/next.js`, `sveltejs/svelte`, `denoland/deno`,
`microsoft/TypeScript`, `openai/openai-node`, `anthropics/claude-code`, `openai/agents.md`,
`kubernetes/kubernetes`, `nodejs/node`, `supabase/supabase`, `tailwindlabs/tailwindcss`,
`github/docs`).

---

## 1. Community health file placement

GitHub searches three locations in order: **`.github/` → repository root → `docs/`**, then falls back
to the organization's **public** `.github` repository.

Two traps to encode in the scaffolder:

- **`LICENSE` cannot be inherited** from an org default community health file.
- **Any file in a repo's own `.github/ISSUE_TEMPLATE` disables all inherited templates.**

Source: [creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)

---

## 2. Issue templates — YAML forms, not markdown

**Default to forms.** Survey: YAML forms beat markdown 9 to 2.

Top-level keys: `name`, `description` and `body` are required; `title`, `labels`, `assignees`,
`projects` and `type` are optional. Body element types are `markdown`, `input`, `textarea`,
`dropdown`, `checkboxes` and `upload` (with per-type size limits).

**Critical caveat:** the `required` validation on form fields **only works in public repositories**.
For a private repo, put the requirement in the field label and validate in triage instead.

Template ordering in the chooser is alphanumeric by filename, with YAML forms listed first.

**`config.yml` is non-negotiable.** It appeared in 12 of the 12 surveyed repos that have an
`ISSUE_TEMPLATE` directory — the most consistent artifact after README and LICENSE. Keys:
`blank_issues_enabled` (boolean) and `contact_links` (a list of `name`/`url`/`about`). Use it to route
questions to Discussions and vulnerabilities to the security advisory flow.

Sources: [form schema syntax](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema) ·
[configuring the template chooser](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository)

---

## 3. Pull request templates — one file

**Zero of 14 surveyed repos use a `PULL_REQUEST_TEMPLATE/` directory.** All 12 that have a template
use a single file. Default to `.github/pull_request_template.md`.

The multi-template directory exists (`.github/PULL_REQUEST_TEMPLATE/<name>.md`) but selection
requires a hand-built URL — `?quick_pull=1&template=name.md` — and nothing in the UI surfaces it.
Offer it only as an explicit opt-in, and if enabled, document the URLs in CONTRIBUTING.

The PR checklist must mirror CONTRIBUTING's checklist rather than restating it, and should name the
single local command that reproduces CI.

Source: [using query parameters to create a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/using-query-parameters-to-create-a-pull-request)

---

## 4. CODEOWNERS

Valid in repository root, `.github/` or `docs/`. Rules to encode:

- **Last matching pattern wins** — order matters, most general first.
- Owners **must have write access**, or the rule silently does nothing.
- Gitignore-style negation is **not** supported.
- 3 MB file size cap.
- Draft PRs do not request review from owners until marked ready.

Two notable production variants: per-directory `OWNERS` files (Kubernetes) and an external
multi-team engine driven from `.codeowners`/`codeowners.toml` with a deliberate root stub
(`cloudflare/workers-sdk`). Both are heavier than a new repo needs — start with a single file.

Source: [about code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

---

## 5. Rulesets, not legacy branch protection

Use **repository rulesets**. Multiple rulesets aggregate with the **most restrictive** rule winning.
Typical baseline for a new repo: require a pull request before merging, require status checks to
pass, require linear history, block force pushes, and restrict deletions.

**`gh ruleset` is view-only** — creation must go through `gh api`:

```bash
gh api --method POST repos/{owner}/{repo}/rulesets --input ruleset.json
```

Do not apply rulesets in the same step as file generation. It is a remote mutation and needs its own
confirmation.

---

## 6. Actions hardening — the non-negotiables

1. **Least-privilege `permissions:`** at workflow level, narrowed further per job. Start from
   `permissions: contents: read` and add only what a job needs.
2. **Pin third-party actions to a full-length commit SHA.** A SHA is the only immutable reference; a
   tag can be moved. Add the human-readable version as a trailing comment.
3. **`pull_request_target` runs privileged against untrusted code.** Never combine it with checking
   out the PR head. Prefer `pull_request` plus a separate privileged workflow triggered on
   `workflow_run`.
4. **Use OIDC for cloud auth** rather than long-lived secrets.
5. **`concurrency` with cancel-in-progress** on PR workflows, to stop queue pileups.
6. **Environment protection rules** for anything that deploys.

`zizmor` audits workflows for these exact classes of problem and appeared in 2 of 14 surveyed repos —
rare but high leverage. Include it in the security workflow.

**Reusable workflows vs composite actions:** reusable workflows (`workflow_call`) accept `inputs`,
`secrets` and `outputs` and run as their own jobs, with a nesting cap; composite actions run as steps
inside a job. For a single new repo, neither is needed — inline the workflow and factor later.

---

## 7. Dependabot

`.github/dependabot.yml`. Ship two ecosystems for a Node repo: `npm` and `github-actions` — the
second is what keeps SHA pins current.

Useful keys: `version` (always `2`), `updates`, `package-ecosystem`, `directory`/`directories`,
`schedule`, `groups` (grouped updates are supported and strongly recommended to cut PR noise),
`open-pull-requests-limit`, `cooldown`, `exclude-paths`.

Survey: `dependabot.yml` in 6 of 14; `renovate.json` in **0 of 14**. Dependabot is the default.

---

## 8. Scanning

**CodeQL default setup** covers most repos without a committed workflow; use the advanced workflow
only when a custom build is required.

**Secret scanning and push protection have an asymmetry worth knowing:** repository-level push
protection is **off by default**, while **user** push protection is **on by default** for public
repos. Bypass reasons determine alert state — "It's used in tests" and "It's a false positive" close
the alert, "I'll fix it later" leaves it open.

Source: [about push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection)

---

## 9. OpenSSF Scorecard and provenance

Scorecard runs 22 checks. A repo scaffolded from this template already satisfies most of the
document-and-process checks; the ones that need deliberate work are pinned dependencies, branch
protection, code review, token permissions, and signed releases.

For releases, use artifact attestations to generate SLSA provenance. Grant `id-token: write` and
`attestations: write` only on the release job.

---

## 10. `gh` CLI bootstrap surface

| Task | Command |
|---|---|
| Create repo | `gh repo create <name> --private --description … --source . --push` |
| Description, homepage, topics | `gh repo edit --description … --homepage … --add-topic …` |
| Labels | `gh label create` / `gh label clone <source-repo>` |
| Secrets and variables | `gh secret set NAME` · `gh variable set NAME` |
| Rulesets | `gh api --method POST repos/{owner}/{repo}/rulesets --input ruleset.json` |
| Private vulnerability reporting | `gh api --method PUT repos/{owner}/{repo}/private-vulnerability-reporting` |

Default to `--private` unless a public repo is explicitly requested.

---

## 11. Security advisories and SECURITY.md

Private vulnerability reporting is **public-repo-only** and is a repository setting — there is **no
mechanical link between SECURITY.md and PVR**. Enable both, and have SECURITY.md point at the
advisory flow rather than an email address where possible.

The advisory workflow is draft → private fork → CVE request (72-hour review) → publish.

SECURITY.md should state supported versions, the reporting channel, and an acknowledgement SLA.
Nothing else.

---

## 12. Template repositories

If publishing the scaffold as a GitHub template repository: history is squashed to a single commit,
Git LFS objects are not copied, and branches created from a template have unrelated histories. That
makes a template repo a poor fit for a skill-driven scaffolder — generate files instead.

---

## 13. Frequencies to respect

| Artifact | Present in |
|---|---|
| README, license file | 14 / 14 |
| `.github/` | 13 / 14 |
| PR template (always a single file) | 12 / 14 |
| `ISSUE_TEMPLATE/` directory | 12 / 14 |
| `ISSUE_TEMPLATE/config.yml`, given the directory | 12 / 12 |
| CONTRIBUTING | 12 / 14 |
| Code of conduct — usually a 2–4 line pointer | 9 / 14 |
| Some agent-instruction file | 11 / 14 |
| AGENTS.md specifically | 6 / 14 |
| dependabot.yml | 6 / 14 |
| SUPPORT.md | 3 / 14 |
| `.env.example` | 1 / 14 |
| renovate.json, CITATION.cff, Taskfile, justfile | 0 / 14 |

Two consequences: **inline a full code of conduct only on request** — the pointer form plus a filled
reporting contact is the norm — and **keep SUPPORT.md to a routing table**, since only very large
projects carry one at all.
