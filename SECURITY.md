# Security policy

## What this repository actually is

Every file here is an instruction to an AI agent. There is no compiled artifact, so the
threat model is not memory safety, it is influence over an agent that may hold credentials,
write to a repository, or call an API on someone's behalf.

Two consequences follow.

**A prompt is executable.** A malicious edit to a `SKILL.md` can instruct an agent to
exfiltrate an environment variable, weaken a check, or push to a branch. Review skill diffs
with the same care as a diff to a deployment script.

**Vendored content is supply chain.** [`skills/pstack/`](./skills/pstack/) is refreshed
automatically from an upstream repository every two weeks. A compromise upstream reaches
this repository on that schedule. The refresh is commit-pinned and always arrives as a pull
request, never as a direct push to `main`, so there is a review point. Use it.

## Reporting a vulnerability

Report privately, not in a public issue.

1. Preferred: open a draft advisory under the repository's **Security** tab, which uses
   GitHub private vulnerability reporting.
2. Alternative: contact the maintainer through the profile at
   [github.com/bughunt8](https://github.com/bughunt8).

Please include the file path, what an agent would be induced to do, and the smallest
reproduction you have. Expect an acknowledgement within five working days. There is no bug
bounty.

## In scope

- A `SKILL.md` or reference file that instructs an agent to leak secrets, disable a safety
  check, or take destructive action without confirmation.
- A script under `scripts/` that executes untrusted input, writes outside the repository, or
  can be induced to commit a secret.
- A workflow under `.github/workflows/` with excessive permissions, an unpinned third-party
  action, or a path by which a fork's pull request could obtain write access or read a
  secret.
- Attribution or licence metadata that misrepresents the origin of vendored content.
- A vendored upstream that has been compromised.

## Out of scope

- The behaviour of any third-party model, agent runner or IDE that consumes these skills.
- Vulnerabilities in an upstream project that do not affect the vendored subset here.
  Report those upstream; open an issue here so the skill can be excluded in the meantime.
- Skills that legitimately instruct an agent to run commands, where the user is the one
  invoking them.

## Controls in place

| Control | Where |
| --- | --- |
| Third-party actions pinned to full commit SHAs, never tags | `.github/workflows/` |
| Least-privilege `permissions:`, write scopes granted per job | `.github/workflows/` |
| Vendored refreshes arrive as reviewable pull requests, never direct pushes | `sync-vendored-skills.yml` |
| Upstream sources pinned to a 40-character commit and validated in CI | `skills/vendor.manifest.json` |
| Provenance, licence and attribution presence enforced on every pull request | `scripts/sync_vendor.py --validate-manifest` |
| Skill metadata validated on every pull request | `scripts/lint_skills.py` |
| Action and workflow updates proposed automatically | `.github/dependabot.yml` |

## Secrets

No skill, script or workflow in this repository should ever contain a credential. The only
secret referenced anywhere is the optional `SYNC_PAT`, used solely so that the fortnightly
pull request can trigger CI. If you find a committed credential, treat it as compromised,
report it privately, and rotate it before it is removed from history.
