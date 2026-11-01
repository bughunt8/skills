# Workflow pipeline

Answers one question: **how does the pipeline run, and how does the skill fill in a deployment
target?**

The number in front of each workflow filename sets the order work moves through the pipeline. The
`SCAFFOLD-PLACEHOLDER` marker marks the step that depends on the target repository, and the skill
either derives that step or reports it.

---

## 1. The funnel

Ten templates live in `assets/templates/github/workflows/`. Each filename starts with a zero-padded
two-digit number, and GitHub lists workflows in filename order, so the number is the order an
operator reads.

Five bands:

| Band | Range | Meaning |
|---|---|---|
| Checks | `01`-`49` | Runs on a pull request, a schedule or the default branch. Quality, review, tests, security, release and scorecard work. None of these files deploys the application. |
| Staging promotion | `50`-`59` | Moves a verified commit from the default branch into the staging environment. |
| Staging actions | `60`-`79` | The work that happens at staging once the code is live there. |
| Production promotion | `80`-`89` | Moves a verified staging candidate into the default branch. A person starts it. |
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
| `60-staging-checks.yml` | Staging actions | Staging checks |
| `80-promote-to-production.yml` | Production promotion | Promote Staging to Main |
| `90-deploy-production.yml` | Production deployment | Deploy Production |

Six files fill the checks band. One file fills each of the other four bands. The numbers left free
inside a band take the next file that arrives.

Three of the ten are conditional. `03-e2e.yml` needs a user interface, `05-release.yml` needs the
changesets release tooling and `06-scorecard.yml` needs a public repository. A default scaffold
emits nine of the ten.

---

## 2. Why a band is a range

The number is a position, so a change of position stays local. A workflow that changes role changes
its own number and never renumbers another band, because no other band's position moved. A check
that starts gating a merge stays in the checks band and keeps its number, because the band says
what role a file has and a gate is not a new role. The other nine filenames stay as they are.

The free numbers hold the checks that arrive later. `07` through `49` takes the next check: coverage
reporting, a bundle-size limit, a migration dry run. Staging and production keep smaller reserves,
`61`-`79` and `91`-`99`, because a stage rarely needs more than a few files.

A flat list of names orders itself alphabetically, so `deploy-staging` lands beside `dependabot` and
the pipeline order disappears. The numeric prefix fixes that, and it sorts correctly with no
tooling because two digits pad every name and every name shares the same width.

---

## 3. The chain

### What fires when

| Workflow | Trigger | Starts |
|---|---|---|
| `01-quality-gates.yml` | `pull_request`; push to `{{DEFAULT_BRANCH}}` | GitHub, on the event |
| `02-docs-review.yml` | `pull_request` on documentation paths | GitHub, on the event |
| `03-e2e.yml` | `pull_request` labelled or synchronized; schedule; `workflow_dispatch` | GitHub, on the event |
| `04-security.yml` | `pull_request`; push to `{{DEFAULT_BRANCH}}`; schedule | GitHub, on the event |
| `05-release.yml` | push to `{{DEFAULT_BRANCH}}`; `workflow_dispatch` with the commit to publish | GitHub, on the event, or the promotion |
| `06-scorecard.yml` | `branch_protection_rule`; schedule; push to `{{DEFAULT_BRANCH}}` | GitHub, on the event |
| `50-promote-to-staging.yml` | push to `{{DEFAULT_BRANCH}}`; `workflow_dispatch` from the default branch | GitHub, on the event |
| `60-staging-checks.yml` | `workflow_run` after `Promote to Staging` completes | GitHub, after the promotion succeeds |
| `80-promote-to-production.yml` | `workflow_dispatch` only, with `confirm` set to `PROMOTE`, dispatched from the branch holding the commit to promote | A person |
| `90-deploy-production.yml` | `workflow_run` after `Promote Staging to Main` completes | GitHub, after the promotion succeeds |

### The path a commit takes

```text
push to the default branch
  ├─ 01-quality-gates.yml      the checks run in parallel
  ├─ 04-security.yml
  ├─ 05-release.yml            publishes, when the release tooling is changesets
  └─ 50-promote-to-staging.yml
       guard  ── refuses a dispatch that did not start on the default branch
       verify ── lint, typecheck, test against the pushed commit
       deploy ── moves the staging branch to that commit, then ships it
            │
            └─ 60-staging-checks.yml   runs only when the promotion succeeded
                 checks ── the work that happens at staging
                     └─ publishes the result on the commit it checked out

a person dispatches 80-promote-to-production.yml with confirm set to PROMOTE
  guard        ── refuses anything but the exact string PROMOTE
  candidate    ── records the staging commit, and refuses when the dispatched commit is not it
  staging-gate ── requires a successful staging deployment and staging checks of that commit
  verify       ── lint, typecheck and test against that commit, unless the operator opts out
  promote      ── moves the default branch to that commit
       ├─ 05-release.yml               dispatched by hand, because a bot push starts no run
       └─ 90-deploy-production.yml     runs only when the promotion succeeded
            deploy ── ships the promoted commit, behind the production environment
```

### Inside one workflow

`needs:` orders jobs in the same file. `50-promote-to-staging.yml` runs `guard`, then `verify`,
then `deploy`, and `deploy` declares `needs: [verify]`, so a red lint, typecheck or test result
stops the promotion before it starts. The `guard` job refuses a manual dispatch whose ref is not
the default branch, because a ref that is not the default branch never passed the repository
ruleset. The comparison is on the whole ref, so a tag named after the default branch is refused
as well.

`80-promote-to-production.yml` chains five jobs. `guard` checks the confirmation. `candidate`
records the staging commit and refuses to continue when the commit the run started from is not that
commit. `staging-gate` requires a successful staging deployment of the same commit and a
successful staging check of the same commit. `verify` runs the suite unless the operator set
`run_verification` to `false`. `promote` runs when every gate succeeded and `verify` either
succeeded or was skipped:

```yaml
  promote:
    needs: [guard, candidate, staging-gate, verify]
    if: ${{ always() && needs.guard.result == 'success' && needs.candidate.result == 'success' && needs.staging-gate.result == 'success' && (needs.verify.result == 'success' || needs.verify.result == 'skipped') }}
```

`always()` is there because a skipped `verify` would otherwise skip `promote` as well, and the
operator who turned verification off could never promote. The condition reads all four results and
decides.

`run_verification` is a Boolean input. The condition reads it directly as
`${{ inputs.run_verification }}`. Comparing a Boolean with the string `'true'` does not work:
GitHub coerces the string to a number when the types differ, and the comparison is then always
false, which skips the verification even when the operator asked for it.

The confirmation is compared in the shell, not in an expression. GitHub ignores case when it
compares strings, so an expression would accept `promote` as well as `PROMOTE`. The shell test
`[ "$CONFIRM" != "PROMOTE" ]` is case-sensitive.

### Across workflows

GitHub has no `needs:` between workflow files. Two mechanisms carry the gate instead.

`workflow_run` chains the deployment workflows. `60-staging-checks.yml` declares `workflow_run` for
the `Promote to Staging` workflow and its job checks
`github.event.workflow_run.conclusion == 'success'`, so a failed promotion leaves the checks
unstarted. `90-deploy-production.yml` does the same for `Promote Staging to Main`.

Three rules govern that mechanism, and each one breaks a chain when it is ignored.

The `workflows` list names a workflow by its **display name**, the value of its `name:` field, not
by its file path. GitHub's own documentation shows `workflows: [Run Tests]` for a workflow whose
`name:` is `Run Tests`. A path in that list matches nothing, and the dependent workflow never
starts. `scaffold.py`'s self-test checks every dependency against the names the workflow templates
declare, so a path in that list fails the build.

A `workflow_run` event fires whatever the conclusion of the previous run was, so the job needs the
`conclusion == 'success'` condition. Without it the deployment runs after a failed promotion.

A `workflow_run` workflow runs the workflow file from the default branch, and the event only
arrives when that file exists there. On a repository whose default branch does not carry
`60-staging-checks.yml` yet, the staging checks never start.

The repository ruleset gates the pull request. It must require the status check published by
`01-quality-gates.yml`. That workflow is named `Quality gates` and its only job is named `check`,
and GitHub identifies a required status check by the job name, so the required list carries
`check`. The skill's manual settings list already carries the instruction. Its first item tells
the operator to create a repository ruleset on the default branch that requires a pull request, the
`check` status check and linear history, and blocks force pushes. The scaffold does not create
rulesets: `gh api` calls are a separate, individually confirmed step.

A ruleset that requires a pull request also refuses a direct `git push` to the default branch, and
the `promote` job in `80` does exactly that. The identity that runs the promotion needs a bypass
entry. A bypass also waives the required status checks for that push, so the pull request gate does
not apply to the promoted commit. The verification inside `80` is what covers it, and it runs
against the exact candidate that is promoted.

### The commit that ships is the commit that was verified

No step ships a commit that the suite did not test.

`50-promote-to-staging.yml` checks out `${{ github.sha }}` in `verify` and hands that same SHA to
`deploy` as a job output. The commit that reaches staging is the commit the suite tested. The
`deploy` job then moves the `staging` branch to that commit, so the branch records what is live
in staging. A push that is not a fast-forward is refused by the server, which is the point: a
staging branch that diverged is reconciled by hand, not overwritten here.

`60-staging-checks.yml` checks out `${{ github.event.workflow_run.head_sha }}`, which is the commit
the promotion ran on, so the checks run against the deployed commit.

`80-promote-to-production.yml` records the staging commit in `candidate` and checks out that SHA in
`verify`. The recorded commit is the commit the run started from, so it cannot drift while the run
is in flight:

```bash
git fetch --force origin '+refs/heads/staging:refs/remotes/origin/staging'
candidate="$(git rev-parse refs/remotes/origin/staging)"
if [ "$candidate" != "$DISPATCH_SHA" ]; then
  echo "The commit this run started from is not the current staging head."
  echo "Dispatch this workflow from the branch that holds $candidate."
  exit 1
fi
```

The fetch names the tracking ref on purpose. `git fetch origin staging` fills `FETCH_HEAD` and
leaves `refs/remotes/origin/staging` as the checkout found it, so a staging branch that moved
after the checkout would be read at its old commit.

The promotion moves the branch rather than merging into it, because a merge creates a commit that
nobody tested:

```bash
git push origin "$CANDIDATE:{{DEFAULT_BRANCH}}"
```

A push that is not a fast-forward is refused by the server, so a default branch that diverged
from staging is reconciled by hand. The job also refuses to continue when the staging branch moved
after the candidate was recorded:

```bash
if [ "$current" != "$CANDIDATE" ]; then
  echo "The staging branch moved during verification. Run the promotion again."
  exit 1
fi
```

`90-deploy-production.yml` checks out `${{ github.event.workflow_run.head_sha }}`. The promotion ran
on the commit it moved the default branch to, so that head commit is the promoted commit. Checking
out the commit rather than the branch keeps the deployment bound to the commit that was verified,
whatever happens to the branch afterwards.

### The staging gate

The promotion into production needs two facts about the candidate commit, and neither comes from
the run that promotes.

The staging deployment of the candidate is the run of `50-promote-to-staging.yml` for that commit.
That workflow runs on the commit it promotes, so the run list finds it by commit.

The staging checks publish their result as a commit status on the commit they checked out. A
`workflow_run` consumer carries the default branch commit in its own SHA, not the commit it checked
out, so the run list cannot tell the two apart. The commit status carries the deployed commit
instead, and the gate reads that status on the candidate.

The staging checks name the promotion they belong to in their run name, and the gate finds the
checks of the attempt it is waiting for through that name. The context of the status they publish
carries the promotion, the attempt of the promotion, the run of the check and the attempt of the
check. A rerun keeps the run id and moves the attempt, so the attempt number is what tells two
attempts apart.

The checks publish a pending status before they run and the outcome afterwards, and the gate reads
the status of the attempt that is current. A check that was rerun and cancelled before it
published anything leaves the earlier status standing, and the gate does not read it, because the
attempt in it is no longer the current one.

The attempt and the conclusion of the check run come from one response. Two responses can straddle
a rerun, and the gate would then pair the result of one attempt with the outcome of another.

An unresolved placeholder publishes `error` rather than a result, and the gate refuses at once. A
repository that has not resolved the staging checks therefore cannot promote into production, and
that is the point: a promotion needs evidence that the staged code passed.

The gate waits in four places, ten minutes each: for the staging deployment to report success, for
the staging checks of that promotion to start, for their result to be published, and for the check
run to finish. The last one matters, because the checks publish their result before the workflow
that carries it finishes, so a result that is already published can still belong to a run that is
running. Every window fails closed: a promotion that arrives too late is refused rather than
promoted on incomplete evidence.

### A bot push starts no workflow

A push made with the repository's default `GITHUB_TOKEN` starts no new workflow run, apart from
`workflow_dispatch` and `repository_dispatch`. The `promote` job in `80` pushes with that token, so
`05-release.yml` does not start. The job dispatches it by hand instead:

```bash
lookup_err="$RUNNER_TEMP/release-lookup.err"
if ! gh api "repos/$GH_REPO/actions/workflows/05-release.yml" >/dev/null 2>"$lookup_err"; then
  if grep -q "HTTP 404" "$lookup_err"; then
    echo "This repository has no release workflow, so the promotion did not publish."
    exit 0
  fi
  echo "The release workflow could not be read:"
  cat "$lookup_err"
  exit 1
fi
nonce="promote-$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
gh workflow run 05-release.yml --ref {{DEFAULT_BRANCH}} \
  --field commit="$CANDIDATE" --field correlation="$nonce"
run_id=$(gh run list --workflow 05-release.yml --limit 20 --json displayTitle,databaseId --jq "map(select(.displayTitle == \"Release $nonce\")) | .[0].databaseId // empty")
```

The dispatch names the commit to publish, so the release does not read the branch head. It also
carries an identifier that appears in the title of the run it starts, because `05-release.yml`
puts that identifier in its `run-name`, and a run name shows up as the run's display title. The
promotion then waits for the run whose display title is exactly `Release` and that identifier, and
for no other, so a release that started nearby cannot satisfy the wait. The lookup refuses a
failure that is not a missing workflow, so an expired token stops the promotion instead of quietly
publishing nothing.

The release is optional. The manifest emits `05-release.yml` only for the changesets release
tooling, so a repository on `manual` or `release-please` has no release workflow, and a promotion
there publishes nothing rather than failing.

The job then waits for the release run it dispatched, and fails the promotion when that run does
not succeed. The release sits behind the `production` environment, so the wait includes the time
its reviewers take, and the wait gives up after an hour. Giving up fails the promotion; it does not
cancel the release, which keeps running. `90-deploy-production.yml` waits for the `80` run, so the
production deployment never starts ahead of the publication.

`90-deploy-production.yml` needs no dispatch. Its `workflow_run` event comes from GitHub when the
`80` run finishes, not from the token, so it fires.

### The human gate

`80-promote-to-production.yml` is the only workflow a person starts for a deployment. Its `on:`
block is `workflow_dispatch` alone, with no push, pull request or schedule trigger, and
`90-deploy-production.yml` has no push trigger either, so a plain push to the default branch cannot
deploy to production. `03-e2e.yml`, `05-release.yml` and `50-promote-to-staging.yml` also accept a
dispatch, but none of them deploys to production.

The dispatch names the commit to promote. The workflow runs from the branch the operator picked, and
the `candidate` job refuses to continue unless that branch held the current staging head. The
promoted commit is therefore fixed when the operator confirms the promotion, and it stays fixed
while the suite runs.

Two other gates can ask for a person. The `deploy` job in `90` declares `environment: production`,
and the manual settings tell the operator to require reviewers on that environment, which is the
enforcement point for the production deployment. `05-release.yml` declares the same environment.

### What the pipeline cannot prove

The pipeline proves that the staging promotion of the candidate succeeded, that the staging checks
published a passing result for that same commit, and that the promotion, the release and the
production deployment all carry that commit. It cannot prove that the staged deployment behaved
correctly at runtime. A green run says the command exited 0, not that the application served the
right thing. A smoke check against the staging environment is the check for that, and it belongs in
`60-staging-checks.yml`.

---

## 4. Placeholders

A step that needs a command only the target repository knows carries a comment and a harmless body:

```yaml
      - name: Deploy the application to the production environment
        # SCAFFOLD-PLACEHOLDER: deploy-production
        # Replace this step with the deploy command for this repository. The
        # command must select the production environment itself, and the secrets
        # it needs must be declared.
        run: |
          echo "No deploy command is configured for this repository yet."
```

Three markers ship today, one per deployment-stage workflow: `promote-to-staging`,
`staging-checks` and `deploy-production`. The step echoes a message and exits 0, so the workflow
stays valid YAML and runs green while the command is still missing.

`validate_repo.py` counts the lines carrying `SCAFFOLD-PLACEHOLDER` and reports one warning per
file:

```
{rel}: {n} placeholder(s) still await a real command - replace the SCAFFOLD-PLACEHOLDER step before this workflow deploys anything
```

The count is the number of marker lines, which equals the number of steps in the templates that
ship today.

The `staging-checks` placeholder has one more effect. An unresolved staging check publishes the
state `error` rather than a result, and the promotion into production refuses that state. A
repository that has not resolved the staging checks therefore cannot promote into production.

The marker is a warning, so a fresh scaffold that still carries placeholders passes the
placeholder check. `SCAFFOLD-PIN-SHA` sits on the error side of that line, and the validator
refuses to pass while one unresolved pin survives. The split is deliberate. A missing pin is a
supply-chain hole. A missing deploy command is work still to do that the next step fills.

The two markers are read in different places, so they cannot be confused. The pin marker is
counted only when the file also references an action by a mutable tag, and only then does it
produce an error. A pin comment on a file with no action reference produces no finding at all.

The Hand off step lists every placeholder the skill could not fill, by marker name, in the final
summary. A summary that names `deploy-production` tells the operator which step will echo instead
of deploy.

---

## 5. The assessment rules

The assessment is read-only. It inspects the target repository, decides what each placeholder
should become, and reports the decision. The replacements go into the plan, the operator approves
them, and the Assess step applies them to the files the scaffold has just written. On a new
repository the workflows do not exist before the scaffold runs, so a step that edited them earlier
would have nothing to edit.

Run these in order for every placeholder. The first rule that matches wins, and the skill stops
looking.

1. If the target's `package.json` defines an environment-specific script, the placeholder becomes
   that script. A deployment placeholder needs a script that names its environment, such as
   `deploy:staging` and `deploy:production`. A repository with
   `"deploy:staging": "node scripts/deploy.mjs staging"` gets
   `run: {{PACKAGE_MANAGER}} run deploy:staging` in `50-promote-to-staging.yml` and
   `run: {{PACKAGE_MANAGER}} run deploy:production` in `90-deploy-production.yml`. Each script needs
   its own evidence. A `deploy:staging` script fills the staging deployment placeholder, and it
   does not fill the production placeholder unless the production script is there too. The
   `staging-checks` placeholder needs a check script instead, such as `check:staging`, and a deploy
   script never fills it.
2. Otherwise, for a deployment placeholder only, if the chosen profile carries `cloudflare` and the
   target's `wrangler.jsonc` defines both a `staging` and a `production` environment, the
   placeholder becomes `npx wrangler deploy --env staging` or
   `npx wrangler deploy --env production`. This rule never fills `staging-checks`: a command that
   deploys is not a check, and the promotion into production would then read a deployment as
   evidence that the staged code passed.
3. Otherwise the placeholder stays, and the skill reports it.

The staging checks follow rule 1 only, and read the repository's own check script when it has one.

A command that cannot name its environment is a wrong command, not an incomplete one, so a rule
that cannot establish the environment does not fill the placeholder. A generic `deploy` script
fails this test unless the target shows how it selects the environment.

A replacement edits the `run:` block and deletes the marker comment. The plan names the secrets
the command needs, and the skill lists those secrets next to the repository secrets it already asks
for. The plan also names the steps the command needs before it runs, such as a build step, a
generated file or a service it talks to. A command whose prerequisites the target does not
establish keeps its placeholder.

Every placeholder sits in a job that checks the code out and installs the dependencies, so a
command that runs a repository script finds the dependencies it needs. The install step runs after
the checkout, so the dependencies belong to the promoted tree.

A checkout and an install are not the whole of what a command needs. A replacement also declares the
environment variables the command reads, and the skill wires each one from a secret or a variable
the target repository already holds. A command that reads a token the workflow does not pass fails
at run time, so the plan names the variables next to the command that uses them.

---

## 6. Extending the pipeline

### Adding a file

1. Choose the band by role. A check goes in `07`-`49`, a staging step in `61`-`79`, a production
   step in `91`-`99`.
2. Take the lowest free number in that band and never reuse a retired number.
3. Name the file `NN-slug.yml`, give it a short `name:` label, and give `concurrency.group:` a name
   that identifies the workflow, the way the existing files do.
4. Declare `permissions:` at the top and keep it least privilege.
5. Add the entry to the `workflows` group in `assets/manifest.json`, ascending by number, with
   `template` and `dest` both pointing at the new file.
6. Run `python3 skills/start-github-repo/scripts/scaffold.py --self-test` and
   `python3 skills/start-github-repo/scripts/validate_repo.py --self-test`, scaffold into a scratch
   directory, and validate that scaffold. Refresh the file list and the template count in
   `README.md` and in `commands/start-github-repo.md` when the count changes.

The scaffolder's self-test proves every manifest entry points at a bundled template, that no two
entries share a destination, and that every `workflow_run` dependency names a workflow the templates
ship. It also proves that the promotion and the deployment workflows check out a commit rather than
a branch, that no template merges a branch, that the staging gate names the repository it reads and
the result it waits for, and that the release dispatch names the commit to publish. It checks the
manifest entries of the sample plan it renders, so an entry that no sample plan selects is not
covered by it. The validator works on a scaffolded repository and does not read the manifest.

A new file takes a number inside its band, so the read order stays true and no existing file moves.

### Renumbering a full band

A band is full when every number in its range is taken. Take the next free number above the band,
move that band's files up by one in descending order, and record the new range. Only the files whose
number changed move.

The move is one commit: `git mv` every affected file, update each `name:` and `concurrency.group:`
prefix, re-sort the manifest entries, then run the validator.

If the last band would pass `99`, widen the scheme to three digits (`001`-`099`) across all ten
files in the same commit. Two digits hold the pipeline until one stage needs more than ten files.
