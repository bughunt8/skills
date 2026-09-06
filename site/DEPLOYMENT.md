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
`site-deploy.yml`. There is no second code path, so staging cannot drift from
production, and a staging deploy exercises the exact mechanism production uses.
The only difference is which **GitHub Environment** supplies the secrets.

| | Branch | Environment | Public URL |
| --- | --- | --- | --- |
| Staging | `staging` | `staging` | whatever you set `SITE_URL` to |
| Production | `main` | `production` | `https://skills.ronald.ng` |

```
work ──▶ staging branch ──▶ staging env (Hostinger)
                 │
                 └── site-promote.yml, manual, type "promote"
                              │
                              ▼
                          main branch ──▶ production env (Hostinger)
```

## Nothing is served by a third party

The page loads no external resource. The motion libraries live in `site/vendor/`
and the two webfonts in `site/fonts/`, both served from the site's own origin.

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

| Workflow | Trigger | Does |
| --- | --- | --- |
| `site-validate.yml` | called | secret scan, gitleaks, build reproducibility, HTML validity, browser suite |
| `site-ci.yml` | push/PR touching `site/**`, `skills/**` | calls validate. Exposes the required check `site gates passed` |
| `site-deploy.yml` | called | the single deploy path: build, assemble, publish to Hostinger, smoke-test |
| `site-deploy-staging.yml` | push to `staging` | validate, then deploy to the `staging` environment |
| `site-deploy-production.yml` | push to `main`, or dispatched by promote | validate, then deploy to `production` |
| `site-promote.yml` | manual, typed confirmation | merge `staging` into `main`, then dispatch the production deploy |
| `site-refresh-sources.yml` | 1st and 15th | re-pin the external sources, open a PR against `staging` |

Validation is a reusable workflow called by every deploy path, so no deploy can
skip the gates, and nothing polls across a workflow boundary for another run's
result.

## Secrets you need to add

Three, and they are the same three already held by `bughunt8/profitrise-website`:

| Name | Notes |
| --- | --- |
| `FTP_SERVER` | Hostinger FTP host |
| `FTP_USERNAME` | |
| `FTP_PASSWORD` | |

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
| `SITE_URL` | empty | Enables the post-deploy smoke test. Empty skips it rather than guessing. |
| `SITE_FTP_REMOTE_DIR` | `./` | The Hostinger directory for this environment |

`site-deploy.yml` fails in its first step listing every missing secret, rather
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
main** and type `promote`. It shows what is being promoted, merges, and dispatches
the production deploy.

A push straight to `main` also deploys production, which is why `main` should be
protected.

## What a deploy verifies

Publishing is not the same as succeeding. When `SITE_URL` is set, CI then checks
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
