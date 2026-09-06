# Deployment

Everything runs in GitHub Actions. No step here is meant to be carried out by
hand on a laptop, and no credential belongs in this repository.

This mirrors the existing estate rather than inventing a pattern: the AWS steps
follow `bughunt8/www-resume` `.github/workflows/deploy.yml`, the Hostinger step
follows `bughunt8/profitrise-website` `deploy-production.yml`, and the branch
model and typed-confirmation promotion follow www-resume's
`promote-staging-to-main.yml`.

## Staging and production are the same setup

Both publish the same artifact to **both** targets:

- **AWS** — `aws s3 sync` in two passes (assets long-cached, HTML uncached), then
  a CloudFront invalidation
- **Hostinger** — the same directory over FTP

They share one reusable workflow, `site-deploy.yml`. There is no second code
path, so staging cannot drift from production, and a staging deploy exercises the
exact mechanism production will use. The only difference is which **GitHub
Environment** supplies the secrets.

| | Branch | Environment | Public URL |
| --- | --- | --- | --- |
| Staging | `staging` | `staging` | whatever you set `SITE_URL` to |
| Production | `main` | `production` | `https://skills.ronald.ng` |

```
work ──▶ staging branch ──▶ staging env  (AWS + Hostinger)
                 │
                 └── site-promote.yml, manual, type "promote"
                              │
                              ▼
                          main branch ──▶ production env (AWS + Hostinger)
```

## Workflows

| Workflow | Trigger | Does |
| --- | --- | --- |
| `site-validate.yml` | called | secret scan, gitleaks, build reproducibility, HTML validity, browser suite |
| `site-ci.yml` | push/PR touching `site/**`, `skills/**` | calls validate. Exposes the required check `site gates passed` |
| `site-deploy.yml` | called | the single deploy path: build, assemble, AWS, Hostinger, smoke-test |
| `site-deploy-staging.yml` | push to `staging` | validate, then deploy to the `staging` environment |
| `site-deploy-production.yml` | push to `main`, or dispatched by promote | validate, then deploy to `production` |
| `site-promote.yml` | manual, typed confirmation | merge `staging` into `main`, then dispatch the production deploy |
| `site-refresh-sources.yml` | 1st and 15th | re-pin the external sources, open a PR against `staging` |

Validation is a reusable workflow called by every deploy path, so no deploy can
skip the gates, and nothing polls across a workflow boundary for another run's
result.

## Secrets you need to add

Set these on the repository's **Environments** (`Settings → Environments`), not as
plain repository secrets. Environment scoping is what lets staging and production
use identical names with different values, and it lets you require a reviewer on
production without affecting staging.

The values are the ones you already hold elsewhere:

| Name | Same value as | Notes |
| --- | --- | --- |
| `AWS_ACCESS_KEY_ID` | `bughunt8/www-resume` | |
| `AWS_SECRET_ACCESS_KEY` | `bughunt8/www-resume` | |
| `AWS_REGION` | `bughunt8/www-resume` | CloudFront invalidation is global; any region works |
| `S3_BUCKET` | **new per environment** | See the warning below |
| `CLOUDFRONT_DISTRIBUTION_ID` | **new for production** | The distribution serving `skills.ronald.ng` |
| `FTP_SERVER` | `bughunt8/profitrise-website` | Hostinger |
| `FTP_USERNAME` | `bughunt8/profitrise-website` | Hostinger |
| `FTP_PASSWORD` | `bughunt8/profitrise-website` | Hostinger |

GitHub never reveals a secret's value, not even to a workflow that can use it, so
these must be entered per environment. They cannot be copied across repositories
programmatically.

Optional **variables** (`vars`, not secrets), per environment:

| Name | Default | Use |
| --- | --- | --- |
| `SITE_URL` | empty | Enables the post-deploy smoke test. Empty skips it rather than guessing. |
| `SITE_S3_PREFIX` | empty, bucket root | Deploy under a prefix so two environments can share a bucket safely |
| `SITE_FTP_REMOTE_DIR` | `./` | Hostinger directory for this environment |

`site-deploy.yml` fails in its first step listing every missing secret, rather
than skipping a target and reporting success. A deploy that publishes to one of
two targets and looks green is how the two silently diverge.

### One warning about `--delete`

The asset sync uses `--delete`, matching www-resume, so the destination ends up
matching the publish directory exactly. That means **anything else at that
location is removed.** Either:

- point `S3_BUCKET` at a bucket that holds nothing but this site, or
- set `SITE_S3_PREFIX` so the delete is confined to that prefix

Do not point staging and production at the same bucket root. They would take
turns deleting each other, and the symptom would be an intermittently missing
site rather than an obvious failure.

The Hostinger step keeps `dangerous-clean-slate: false` for the same reason: that
account serves other sites, and it wipes the remote directory.

## What production has to exist first

CI deploys; it does not provision. Create these once, as was done for
`resume.ronald.ng`:

1. **An S3 bucket** for the site, in your usual region.
2. **A CloudFront distribution** with that bucket as origin, an alternate domain
   name of `skills.ronald.ng`, and an ACM certificate for it **in `us-east-1`**
   (CloudFront only reads certificates from that region, regardless of where the
   bucket is).
3. **A Route 53 record** for `skills.ronald.ng` pointing at the distribution, as
   an A/AAAA alias.
4. **A Hostinger directory** for the site, and `SITE_FTP_REMOTE_DIR` set to it.

### About DNS, since it has caused confusion

`ronald.ng` is authoritative on **AWS Route 53**, not Cloudflare and not
Hostinger. Verified:

```
$ dig +short NS ronald.ng
ns-1173.awsdns-18.org.
ns-1548.awsdns-01.co.uk.
ns-381.awsdns-47.com.
ns-549.awsdns-04.net.
```

So the `skills.ronald.ng` record is created in Route 53 even though the content is
also pushed to Hostinger. Nothing in CI touches DNS, exactly as in www-resume.

`skills.ronald.ng` did not previously exist, so nothing is being taken over. These
records are live and unrelated; do not touch them:

| Record | Serves |
| --- | --- |
| `ronald.ng`, `www.ronald.ng` | the main site, CloudFront |
| `resume.ronald.ng` | the résumé site, CloudFront `d1srz7a0s8w38` |
| `mcp.ronald.ng` | a live API Gateway endpoint in `ap-east-1` |

Both targets serve the same bytes, but only one can be authoritative for the
hostname. The Route 53 record decides which; Hostinger is the mirror. Point the
record at whichever you want to serve readers and the other stays a warm copy.

## Protect the environments

`Settings → Environments`:

- **`production`** — require a reviewer, and restrict to the `main` branch.
- **`staging`** — no protection needed.

Also require the check **`site gates passed`** on `main`. It is a single stable
job name that depends on the others, so the required check does not change when a
job is added or renamed.

## Shipping

Push to `staging`, look at the staging URL, then run **Site promote staging to
main** and type `promote`. It shows you what is being promoted, merges, and
dispatches the production deploy.

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
