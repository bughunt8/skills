# AGENTS.md — `.github/`

Rules for anything in this directory. These are security constraints, not style preferences.

## Workflows

- Set `permissions:` explicitly at workflow level, starting from `contents: read`, and narrow further
  per job. Never rely on the default token scope.
- Pin every action to a full-length commit SHA, with the human-readable version as a trailing
  comment. A tag can be moved; a SHA cannot.
- Never use `pull_request_target` together with checking out the pull request head. If a privileged
  operation is genuinely required, use `pull_request` plus a separate `workflow_run` workflow.
- Prefer OIDC over long-lived secrets for any cloud authentication.
- Add `concurrency` with cancel-in-progress to every pull-request-triggered workflow.
- Grant `id-token: write` and `attestations: write` only on the specific job that needs them.
- Never interpolate untrusted input (`github.event.*` titles, bodies, branch names) directly into a
  `run:` block. Pass it through `env:` instead.

## Issue forms

- `required: true` validation only works in public repositories. In a private repository, state the
  requirement in the field label as well.
- `config.yml` must exist. Route questions to Discussions and vulnerabilities to the security
  advisory flow, never to a public issue.

## CODEOWNERS

- The last matching pattern wins, so order rules from general to specific.
- Every owner must have write access or the rule silently does nothing.
- Gitignore-style negation is not supported here.
