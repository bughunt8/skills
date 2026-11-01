# Workflow pipeline

Answers one question: **how does the pipeline run, and how does the skill fill in a deployment target?**

Two mechanisms carry the answer. The number in front of each workflow filename sets the order work
moves through the pipeline. The `SCAFFOLD-PLACEHOLDER` marker marks the step that depends on the
target repository, and the skill either derives that step or reports it.

---

## 1. The funnel

Ten templates live in `assets/templates/github/workflows/`. Each filename starts with a zero-padded
two-digit number, and GitHub lists workflows in filename order, so the number is the order an
operator reads.

Five bands:

| Band | Range | Meaning |
|---|---|---|
| Checks | `01`-`49` | Runs on a pull request, a schedule or the default branch. Quality, review, tests, security, release and scorecard work. None of these files deploys the application. |
| Staging promotion | `50`-`59` | Moves a verified commit onto the `staging` branch. |
| Staging deployment | `60`-`79` | Ships the `staging` branch to the staging environment. |
| Production promotion | `80`-`89` | Merges `staging` into the default branch. A person starts it. |
| Production deployment | `90`-`99` | Ships the default branch to the production environment. |

The ten files:

| File | Band | `name:` |
|---|---|---|
| `01-quality-gates.yml` | Checks | Quality gates |
| `02-docs-review.yml` | Checks | Documentation review |
| `03-e2e.yml` | Checks | End-to-end tests |
| `04-security.yml` | Checks | Security scan |
| `05-release.yml` | Checks | Release |
| `06-scorecard.yml` | Checks | OpenSSF Scorecard |
| `50-promote-to-staging.yml` | Staging promotion | Promote to Staging |
| `60-deploy-staging.yml` | Staging deployment | Deploy Staging |
| `80-promote-to-production.yml` | Production promotion | Promote Staging to Main |
| `90-deploy-production.yml` | Production deployment | Deploy Production |

Six files fill the checks band. One file fills each of the other four bands. The spare numbers
inside a band are the room the next file takes.

---

## 2. Why a band is a range

The number is a position, so a change of position stays local. A workflow that changes role changes
its own number and never renumbers another band, because no other band's position moved. A check
that starts gating a merge leaves `05` and takes the free slot at `07`. The other nine filenames
stay as they are.

Bands carry spare numbers on purpose. `07` through `49` holds nothing today, and that space is where
the next check goes: coverage reporting, a bundle-size limit, a migration dry run. Staging and
production keep smaller reserves, `61`-`79` and `91`-`99`, because a stage rarely needs more than a
few files.

A gap inside a band is informative. An empty `07`-`49` says no extra check has been added. An empty
`61`-`79` says one deployment workflow covers staging. The gap tells a reader what the pipeline does
not have yet, and it does so without a second document.

A flat list of names orders itself alphabetically, so `deploy-staging` lands beside `dependabot` and
the pipeline order disappears. The numeric prefix is the fix, and it sorts correctly with no
tooling because two digits pad every name and every name shares the same width.

---

## 3. Gate semantics

### Inside one workflow

`needs:` orders jobs in the same file. `50-promote-to-staging.yml` runs `verify`, then `promote`, and
`promote` declares `needs: [verify]`, so a red lint, typecheck or test result stops the promotion
before it starts.

`80-promote-to-production.yml` chains three jobs. `guard` checks the confirmation. `verify` runs the
suite unless the operator set `run_verification` to `"false"`. `promote` runs when `guard` succeeded
and `verify` either succeeded or was skipped:

```yaml
  promote:
    needs: [guard, verify]
    if: ${{ always() && needs.guard.result == 'success' && (needs.verify.result == 'success' || needs.verify.result == 'skipped') }}
```

The `always()` call is load-bearing. A skipped `verify` would otherwise skip `promote` as well, and
the operator who turned verification off could never promote. The condition reads both results and
decides.

### Across workflows

GitHub has no `needs:` between workflow files. The cross-workflow gate is the repository ruleset on
the default branch. That ruleset must require the status check published by `01-quality-gates.yml`,
which is the `check` job of the `Quality gates` workflow, before a pull request merges. Every pull
request then reaches the default branch with one green quality run behind it, and the promotion that
merges `staging` inherits the same gate on the way in.

The skill's manual settings list already carries the instruction. Its first item tells the operator
to create a repository ruleset on the default branch that requires a pull request, required status
checks and linear history, and blocks force pushes. Applying that item includes adding the
`Quality gates` check to the required list. The scaffold does not create rulesets: `gh api` calls are
a separate, individually confirmed step.

The ruleset and the promotion push need reconciling. A ruleset that requires a pull request also
refuses a direct `git push` to the default branch, and the `promote` job in `80` does exactly that.
Add the identity that runs the promotion to the ruleset bypass list, or the push is refused.

### The one human gate

`80-promote-to-production.yml` is the single workflow a person starts. Its `on:` block is
`workflow_dispatch` alone, with no push, pull request or schedule trigger. The `confirm` input must
equal `PROMOTE`, and the `guard` job compares the input and exits 1 otherwise, so a typo stops the
run before `verify` or `promote` can start. The `promote` job then merges `staging` into the default
branch with `--no-edit` and pushes.

Every other workflow is automatic. Six start on a pull request, a push or a schedule. `50` and `60`
start on a push to `staging`. `90` starts on a push to the default branch.

---

## 4. What fires when

| Workflow | Trigger | Starts |
|---|---|---|
| `01-quality-gates.yml` | `pull_request`; push to `{{DEFAULT_BRANCH}}` | GitHub, on the event |
| `02-docs-review.yml` | `pull_request` on documentation paths; push to `{{DEFAULT_BRANCH}}` | GitHub, on the event |
| `03-e2e.yml` | `pull_request` labelled or synchronized; schedule; `workflow_dispatch` | GitHub, on the event |
| `04-security.yml` | `pull_request`; push to `{{DEFAULT_BRANCH}}`; schedule | GitHub, on the event |
| `05-release.yml` | push to `{{DEFAULT_BRANCH}}` | GitHub, on the event |
| `06-scorecard.yml` | `branch_protection_rule`; schedule; push to `{{DEFAULT_BRANCH}}` | GitHub, on the event |
| `50-promote-to-staging.yml` | push to `staging`; `workflow_dispatch` | GitHub, on the event |
| `60-deploy-staging.yml` | push to `staging`; `workflow_dispatch` | GitHub, on the event |
| `80-promote-to-production.yml` | `workflow_dispatch` only, with `confirm` set to `PROMOTE` | A person |
| `90-deploy-production.yml` | push to `{{DEFAULT_BRANCH}}`; `workflow_dispatch` | GitHub, after the promotion lands |

A `workflow_dispatch` entry on an automatic workflow adds a manual run option. The normal path stays
the event.

One GitHub rule applies to the last row. Events caused by the repository's default `GITHUB_TOKEN`
start no new workflow run, apart from `workflow_dispatch` and `repository_dispatch`. The `promote`
job in `80` pushes with that token, so `90-deploy-production.yml` does not start on its own.

The `promote` job therefore dispatches it by hand with `gh workflow run`, which is the exception
GitHub makes for `workflow_dispatch`:

```yaml
      - name: Start the production deployment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if gh workflow view 90-deploy-production.yml >/dev/null 2>&1; then
            gh workflow run 90-deploy-production.yml --ref {{DEFAULT_BRANCH}}
          else
            echo "90-deploy-production.yml is not on {{DEFAULT_BRANCH}}. Start it by hand."
          fi
```

The job needs `actions: write` for that. The guard around the call keeps the promotion green when
the operator has removed or renamed the deployment workflow.

The same rule reaches `05-release.yml`. A release does not happen when a promotion pushes, because
that push carries `GITHUB_TOKEN`. Two ways to close the gap: dispatch the release from `80` the
same way, or give the promotion a token that can start workflows, such as a personal access token
or a GitHub App installation token. A ruleset that requires a pull request also refuses the
promotion's direct push, so the identity that runs the promotion needs a bypass entry either way.

---

## 5. Placeholders

A step that needs a command only the target repository knows carries a comment and a harmless body:

```yaml
      - name: Deploy the application to the production environment
        # SCAFFOLD-PLACEHOLDER: deploy-production
        # Replace this step with the deploy command for this repository. A
        # deployment that needs credentials also needs them declared as secrets.
        run: |
          echo "No deploy command is configured for this repository yet."
```

Three markers ship today, one per deployment-stage workflow: `promote-to-staging`,
`deploy-staging` and `deploy-production`. The step echoes a message and exits 0, so the workflow
stays valid YAML and runs green while the command is still missing.

`validate_repo.py` counts the lines carrying `SCAFFOLD-PLACEHOLDER` and reports one warning per file:

```
{rel}: {n} step(s) still await a real command - replace the SCAFFOLD-PLACEHOLDER step before this workflow deploys anything
```

The marker is a warning, so a fresh scaffold that still carries placeholders exits 0. `SCAFFOLD-PIN-SHA`
sits on the error side of that line, and the validator refuses to pass while one unresolved pin
survives. The split is deliberate. A missing pin is a supply-chain hole. A missing deploy command is
unfinished work that the next step fills.

The Hand off step lists every placeholder the skill could not fill, by marker name, in the final
summary. A summary that names `deploy-production` tells the operator which step will echo instead of
deploy.

---

## 6. The assessment rules

Run these in order for every placeholder. The first rule that matches wins, and the skill stops
looking.

1. If the target repository already defines a `deploy` script in its `package.json`, the placeholder
   becomes that script. A repository whose `package.json` carries `"deploy": "node scripts/deploy.mjs"`
   gets `run: {{PACKAGE_MANAGER}} run deploy` in `60-deploy-staging.yml` and in
   `90-deploy-production.yml`. The script body does not matter; the skill reads the key.
2. Otherwise, if the chosen profile carries `cloudflare` and the repository has a `wrangler.jsonc`,
   the placeholder becomes `npx wrangler deploy --env staging` or `--env production`. A
   `worker-service` scaffold with a `wrangler.jsonc` gets `npx wrangler deploy --env staging` in
   `60-deploy-staging.yml` and `npx wrangler deploy --env production` in `90-deploy-production.yml`.
3. Otherwise the placeholder stays, and the skill reports it. A `docs-site` scaffold with no `deploy`
   script and no `wrangler.jsonc` keeps the `echo` step, and the summary reports `deploy-staging` and
   `deploy-production`.

The staging promotion follows the same order, and rule 1 reads the repository's own promotion script
when it has one. A repository with a `promote` script gets `run: {{PACKAGE_MANAGER}} run promote` in
`50-promote-to-staging.yml`. Rule 2 supplies an environment name, `staging` for the promotion file
and `production` for the deploy files, and it supplies no promotion command. A Worker repository
with no promotion script therefore falls to rule 3, and the summary reports `promote-to-staging`.

A replacement edits the `run:` block and deletes the marker comment. The step name stays, so the
workflow reads the same before and after.

---

## 7. Extending the pipeline

### Adding a file

1. Choose the band by role. A check goes in `07`-`49`, a staging step in `61`-`79`, a production step
   in `91`-`99`.
2. Take the lowest free number in that band and never reuse a retired number.
3. Name the file `NN-slug.yml`, set `name:` to the sentence-case label, and set `concurrency.group:`
   to the lower-case hyphenated form of that label with a trailing hyphen, matching the six checked
   files.
4. Declare `permissions:` at the top and keep it least privilege.
5. Add the entry to the `workflows` group in `assets/manifest.json`, ascending by number, with
   `template` and `dest` both pointing at the new file.
6. Run `python3 skills/start-github-repo/scripts/validate_repo.py --self-test`, scaffold into a
   scratch directory, and validate that scaffold. Refresh the file list and the template count in
   `README.md` and in `commands/start-github-repo.md` when the count changes.

A new file takes a number inside its band, so the read order stays true and no existing file moves.

### Renumbering a full band

A band is full when every number in its range is taken. Take the next free number above the band,
move that band's files up by one in descending order, and record the new range. Only the files whose
number changed move.

The move is one commit: `git mv` every affected file, update each `name:` and `concurrency.group:`
prefix, re-sort the manifest entries, then run the validator. The validator proves the tree matches
the manifest, because every `dest` must exist and every workflow in the tree must have an entry.

If the last band would pass `99`, widen the scheme to three digits (`001`-`099`) across all ten
files in the same commit. Two digits hold the pipeline until one stage needs more than ten files. At
that point the pipeline wants splitting.
