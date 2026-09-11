# Deployment

Everything runs in GitHub Actions. No step here is meant to be carried out by
hand on a laptop, and no credential belongs in this repository.

**Hostinger is the only host.** No S3, no CloudFront, no ACM, no Cloudflare
anywhere — not in the deploy and not in the request path. The only AWS service
involved is Route 53, which holds one DNS record and is never touched by CI.

The FTP step follows `bughunt8/profitrise-website` `deploy-production.yml`; the
branch model and typed-confirmation promotion follow `bughunt8/www-resume`
`promote-staging-to-main.yml`.

## Staging and production are the same setup

Both publish the same artifact the same way, through one reusable workflow,
`s2-site-deploy.yml`. There is no second code path, so staging cannot drift from
production, and a staging deploy exercises the exact mechanism production uses.
The only difference is which **GitHub Environment** supplies the secrets.

| | Branch | Environment | Public URL |
| --- | --- | --- | --- |
| Staging | `staging` | `staging` | `https://mediumvioletred-coyote-692292.hostingersite.com/` |
| Production | `main` | `production` | `https://skills.ronald.ng` |

```
work ──▶ staging branch ──▶ staging env (Hostinger)
                 │
                 └── b1-site-promote-to-main.yml, manual, type "promote"
                              │
                              ▼
                     promotion pull request ──▶ code-owner approval
                              │
                              ▼
                          main branch ──▶ production env (Hostinger)
```

Promotion goes through a reviewed pull request. `main` requires a code-owner
approving review, so nothing, including a workflow, writes to `main` directly.

## Nothing is served by a third party

The page loads no external resource. It loads only `data.js` and `app.js` from
its own origin, and the webfonts in `site/fonts/`. There is no `site/vendor/`
any more: the scroll libraries that used to live there were deleted with the
scroll presentation, and motion is now plain CSS and one animation loop.

That is deliberate rather than tidy-mindedness. A CDN and a font service each see
every reader, each can be blocked by a network or an extension, and each is a
dependency that can change or disappear. Removing them also let the Content
Security Policy in `.htaccess` become same-origin only, so if a future change
reintroduces a CDN the browser will refuse it. A test asserts the page makes zero
third-party requests, and another asserts the fonts genuinely load rather than
silently falling back.

## Response headers, caching and TLS

CloudFront used to provide these. They now come from **`site/.htaccess`**, which
ships with the site, so the posture is reviewable in a diff rather than clicked
into hPanel:

- HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`,
  `Cross-Origin-Opener-Policy`, `Permissions-Policy`, and a same-origin CSP
- HTML uncached, CSS and JS for an hour, fonts and images for a week
- gzip on text types
- UTF-8 declared explicitly, because skill descriptions contain CJK and shared
  hosting defaults vary
- an HTTPS redirect that tests `X-Forwarded-Proto`, since Hostinger terminates TLS
  upstream and testing the scheme directly would loop forever behind their proxy

Every block is wrapped in `<IfModule>` so a missing module degrades rather than
returning a 500. On shared hosting that is the difference between one header not
being set and the whole site being unreachable.

**TLS** is Hostinger's free certificate, issued once the domain is pointed and
added in hPanel. Do not enable HSTS before that works, or a browser will pin
itself to HTTPS you cannot yet serve.

## Workflows

Filenames carry a prefix so the two flows read in order rather than
alphabetically. `A` is the everyday path, `B` is the release, `S` is shared and
called by both, `M` is scheduled maintenance. The prefix is in the filename and
in the workflow name, so the Actions sidebar lists them in flow order.

**Flow A, every change.** Open a pull request against `staging`.

| Workflow | Trigger | Does |
| --- | --- | --- |
| `a0-skills-checks.yml` | push, PR | the repository checks. Exposes the required check `validate skills and provenance` |
| `a1-site-checks.yml` | push/PR touching `site/**`, `skills/**` | calls S1. Exposes the required check `site gates passed` |
| `a2-site-deploy-staging.yml` | push to `staging` | validate, deploy to `staging`, verify the live staging origin |

Merging a green pull request into `staging` deploys and verifies automatically.
There is no approval gate on staging, deliberately: it is the rehearsal.

**Flow B, release.** Manual, and gated twice.

| Workflow | Trigger | Does |
| --- | --- | --- |
| `b1-site-promote-to-main.yml` | manual, type `promote` | refuses a revision whose required check is not green, then opens or updates the promotion pull request from `staging` into `main` |
| `b2-site-deploy-production.yml` | push to `main` | validate, wait for the `production` environment reviewer, deploy, verify `https://skills.ronald.ng` |

**Shared, called by both flows.** These have no triggers of their own.

| Workflow | Does |
| --- | --- |
| `s1-site-validate.yml` | secret scan, gitleaks, build reproducibility, HTML validity, browser suite, deploy-contract tests |
| `s2-site-deploy.yml` | the single deploy path: validate the target, build, assemble, publish over FTP |
| `s3-site-verify.yml` | read-only live verification. Fails on missing content or the wrong revision |

**Maintenance.**

| Workflow | Trigger | Does |
| --- | --- | --- |
| `m1-site-refresh-sources.yml` | 1st and 15th | re-pin the external sources, open a PR against `staging` |
| `sync-vendored-skills.yml` | fortnightly | refresh vendored skills. Deliberately unprefixed: generated `PROVENANCE.md` files across the vendored trees link to it by path, and those trees must not be hand-edited |

Validation is a reusable workflow called by every deploy path, so no deploy can
skip the gates, and nothing polls across a workflow boundary for another run's
result.

## Secrets you need to add

Three, and they are the same three already held by `bughunt8/profitrise-website`:

| Name | Kind | Notes |
| --- | --- | --- |
| `FTP_SERVER` | variable, or secret | Hostinger FTP host, bare, no `ftp://` |
| `FTP_USERNAME` | variable, or secret | The site's FTP account name |
| `FTP_PASSWORD` | **secret, always** | The only real credential here |

The host and username resolve from `vars` first and fall back to `secrets`, so an
environment can use either. Prefer variables. A masked host and username make an
FTP `530 Login incorrect` undiagnosable, because the log cannot show which account
the server rejected and there is nothing to compare against hPanel.

This repository is public, so variables appear in run logs. That is the deliberate
trade for a readable failure, and it is why the FTP password must be long and
unique. Never make `FTP_PASSWORD` a variable.

Set them on the repository's **Environments** (`Settings → Environments`), not as
plain repository secrets. Environment scoping is what lets staging and production
use identical names with different values, and it lets you require a reviewer on
production without affecting staging.

GitHub never reveals a secret's value, not even to a workflow that uses it, so
these must be entered per environment. They cannot be copied from another
repository programmatically, by you or by CI.

Optional **variables** (`vars`, not secrets), per environment:

| Name | Default | Use |
| --- | --- | --- |
| `SITE_FTP_REMOTE_DIR` | `./` | The Hostinger directory for this environment |

The two caller workflows pass literal public URLs. `SITE_URL` is not an
environment configuration input anymore. Environment-scoped variables are not
available at the reusable-workflow call site, which caused issue #38.
The shared deployment requires a URL and rejects empty or mismatched targets
before upload. After a successful upload, verification always runs.

`s2-site-deploy.yml` fails in its first step listing every missing secret, rather
than skipping the upload and reporting success.

**Point the two environments at different directories.** Set
`SITE_FTP_REMOTE_DIR` on each, for example `./skills/` and `./skills-staging/`.
If both point at the same directory, staging will overwrite production.

The FTP step keeps `dangerous-clean-slate: false`, because that Hostinger account
serves other sites and the option wipes the remote directory. The consequence is
that a file removed from the repository is **not** removed from the server; if the
site ever drops a file, delete it in hPanel once.

## What has to exist before the first deploy

CI deploys; it does not provision.

1. **A directory on Hostinger** for each environment, and `SITE_FTP_REMOTE_DIR`
   set to match.
2. **The domain added in hPanel** as a domain or subdomain pointing at the
   production directory, so Hostinger will serve it and issue a certificate.
3. **A DNS record** for `skills.ronald.ng` in Route 53, pointing at Hostinger.
   hPanel shows the exact target; it is normally an A record to a Hostinger IP.
4. **The Hostinger certificate** issued for `skills.ronald.ng` after DNS resolves.

### About DNS, since it has caused confusion

`ronald.ng` is authoritative on **AWS Route 53** — not Cloudflare, and not
Hostinger. Verified:

```
$ dig +short NS ronald.ng
ns-1173.awsdns-18.org.
ns-1548.awsdns-01.co.uk.
ns-381.awsdns-47.com.
ns-549.awsdns-04.net.
```

So the `skills.ronald.ng` record is created **in Route 53**, pointing at
Hostinger. This is the one place AWS is still involved, and nothing in CI touches
it, exactly as in www-resume.

Do **not** move the zone to Hostinger to avoid this. These records are live and
unrelated, and they would all have to be recreated correctly first:

| Record | Serves |
| --- | --- |
| `ronald.ng`, `www.ronald.ng` | the main site, on CloudFront |
| `resume.ronald.ng` | the résumé site, on CloudFront |
| `mcp.ronald.ng` | a live API Gateway endpoint in `ap-east-1` |

`skills.ronald.ng` did not previously exist, so nothing is being taken over.

## Protect the environments

`Settings → Environments`:

- **`production`** — require a reviewer, and restrict to the `main` branch.
- **`staging`** — no protection needed.

Also require the check **`site gates passed`** on `main`. It is a single stable
job name that depends on the others, so the required check does not change when a
job is added or renamed.

## Shipping

Push to `staging`, look at the staging URL, then run **Site promote staging to
main** and type `promote`. It shows what is being promoted, refuses to promote a
revision whose required check is not green, merges `main` into `staging` when
`staging` has fallen behind, and opens or updates the promotion pull request.

Approve and merge that pull request to release. The merge is a push to `main`, so
**Site deploy production** runs on it, revalidates the commit, waits for the
`production` environment reviewer, then publishes and smoke-tests the live URL.
The workflow no longer dispatches the production deploy, because it no longer
pushes; the old dispatch existed only to work around a `GITHUB_TOKEN` push not
triggering `on: push`.

Any push to `main` deploys production, which is why `main` is protected and the
promotion travels the same reviewed path as any other change.

Opening the pull request needs one of these, because a workflow cannot open a
pull request by default:

- **Settings → Actions → General → Allow GitHub Actions to create and approve
  pull requests**, enabled; or
- a fine-grained PAT in the `PROMOTE_TOKEN` secret with Contents and Pull
  requests write access. This option also lets the pull request trigger
  `pull_request`-scoped checks, which a `GITHUB_TOKEN`-opened one does not.

The workflow reports which of these is missing rather than failing opaquely.

## What a deploy verifies

Publishing is not the same as succeeding. After every successful upload, CI calls
`s3-site-verify.yml` with the target URL and the full deployed commit SHA. It checks
the live origin and fails the deploy unless:

- it returns 200 with `text/html`
- the served HTML contains 400+ prerendered cards
- `BUILD-INFO.txt` names the commit just deployed, so a cached previous deploy is
  detected rather than mistaken for success
- the page renders with no console or page errors at 390px and 1440px
- there is no horizontal overflow at either width
- it is still a complete list with JavaScript disabled

## Rollback

Re-run **Site deploy production** from an earlier commit, or revert on `main` and
let the push deploy. Because the artifact is rebuilt from source in CI on every
run, an older commit rebuilds to what that commit actually said.
