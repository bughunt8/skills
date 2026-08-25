# Support

This is a maintained-in-the-open skills library, not a supported product. There is no SLA.
Issues are read and answered as time allows.

## Choose the right channel

| You want to | Go here |
| --- | --- |
| Understand what a skill does | Read its `SKILL.md`. The `description` frontmatter says when to use it and what to use instead. |
| Find a skill for a task | The generated index in [README.md](./README.md), or `skills/engineering/ask-matt` which recommends a skill for a situation. |
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

Anything under [`skills/pstack/`](./skills/pstack/) is a verbatim copy of
[backnotprop/pstack](https://github.com/backnotprop/pstack). A bug in the skill's own logic
belongs upstream, and fixing it there means everyone downstream gets the fix. Open an issue
here if the copy is stale, misattributed, or should be excluded.

## Response expectations

Best effort, usually within a week. Attribution and security reports are looked at first.
Requests to make a skill work with a specific proprietary runner are usually declined.
