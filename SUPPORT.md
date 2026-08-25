# Support

This is a maintained-in-the-open skills library, not a supported product. There is no SLA.
Issues are read and answered as time allows.

## Choose the right channel

| You want to | Go here |
| --- | --- |
| Understand what a skill does | Read its `SKILL.md`. The `description` frontmatter says when to use it and what to use instead. |
| Find a skill for a task | The generated index in [README.md](./README.md), or `skills/engineering/ask-matt` which recommends a skill for a situation. |
| Work on your resume, interviews or job search | [`skills/job-hunt/`](./skills/job-hunt/). Start with `get-started`, which sets up the workspace the other ten skills read. |
| Report a skill that misbehaves | A bug report issue. Include the skill path, the agent and model you ran it with, and what it did. |
| Propose a new skill | A new-skill issue, or read [CONTRIBUTING.md](./CONTRIBUTING.md) and open a pull request. |
| Propose importing someone else's skills | A vendored-import issue. Attribution requirements are in CONTRIBUTING.md. |
| Report a security or prompt-injection concern | [SECURITY.md](./SECURITY.md). Do not open a public issue. |
| Fix a wrong attribution | Open an issue. These are treated as high priority. |

## Before you file

State which agent runner and which model you used. Skill behaviour varies substantially
between them, and "the skill did not work" is not actionable without it. Some vendored
skills, `poteto-mode`, `setup-pstack` and `arena` in particular, assume a Cursor-style
multi-model runner. The engineering discipline in them travels anywhere; the model names do
not.

## Vendored skills

Two directories are verbatim copies of upstream projects:

| Directory | Upstream | Report logic bugs to |
| --- | --- | --- |
| [`skills/pstack/`](./skills/pstack/) | [backnotprop/pstack](https://github.com/backnotprop/pstack) | [upstream issues](https://github.com/backnotprop/pstack/issues) |
| [`skills/job-hunt/`](./skills/job-hunt/) | [Remotivated/job-hunt-skills](https://github.com/Remotivated/job-hunt-skills) | [upstream issues](https://github.com/Remotivated/job-hunt-skills/issues) |

A bug in a skill's own logic belongs upstream, and fixing it there means everyone downstream
gets the fix. Open an issue here if the copy is stale, misattributed, or should be excluded.

## Two things that catch people out with the job-hunt skills

**They need a workspace.** The skills read and write a `my-documents/` directory in your own
working folder. Run [`get-started`](./skills/job-hunt/skills/get-started/SKILL.md) first, or
scaffold it from the upstream repository. Without it the skills have nothing to read and will
say so.

**DOCX and PDF export is not vendored here.** Upstream ships a Node 22 plus Typst toolchain
for ATS-safe export. It is not included, on purpose. Markdown output works normally. For
export, clone [the upstream repository](https://github.com/Remotivated/job-hunt-skills) and
run it there. This is not a bug, and the full reasoning is in
[`skills/job-hunt/ATTRIBUTION.md`](./skills/job-hunt/ATTRIBUTION.md).

## Response expectations

Best effort, usually within a week. Attribution and security reports are looked at first.
Requests to make a skill work with a specific proprietary runner are usually declined.
