## What changes and why

<!-- One paragraph. If this adds a skill, say what an agent will now do that it could not do before. -->

## Type of change

- [ ] New skill written here
- [ ] Change to an existing skill written here
- [ ] Import or refresh of someone else's skills (vendored)
- [ ] Scripts, workflows or repository governance
- [ ] Documentation only

## Checks

Run these locally. Standard library Python only, nothing to install.

- [ ] `python3 scripts/lint_skills.py` passes
- [ ] `python3 scripts/generate_index.py --check` passes
- [ ] `python3 scripts/sync_vendor.py --validate-manifest` passes
- [ ] I did not add an entry to `scripts/skill_lint_baseline.json` to silence a violation I introduced

## If this adds a skill

- [ ] Directory name and frontmatter `name` are identical, lowercase kebab-case
- [ ] The name is not already used anywhere in `skills/`
- [ ] `description` says what it does, when to use it, and what to use instead, under 1024 characters
- [ ] New domain, if any, is described in `docs/domain-descriptions.json` and the index is regenerated

## If this imports someone else's work

Attribution is not negotiable here. A public MIT repository redistributing unattributed work
is the one mistake that cannot be quietly corrected later.

- [ ] Added as a source in `skills/vendor.manifest.json`, not copied in by hand
- [ ] `scripts/sync_vendor.py --sync` produced the result in this diff
- [ ] Upstream author, licence and a full 40-character commit pin are recorded
- [ ] Every exclusion has a reason in `exclude_reasons`
- [ ] `THIRD_PARTY_NOTICES.md` and the per-skill `PROVENANCE.md` files are generated, not edited

## If this is an automated vendored refresh

- [ ] I read the upstream diff, not only this one
- [ ] No new upstream skill name collides with a local skill
- [ ] `unslop` is still present

## Prompt-injection review

Every file here is an instruction to an agent that may hold credentials.

- [ ] Nothing in this diff instructs an agent to read a secret, disable a check, or take a destructive action without confirmation
- [ ] No credential, token or private URL is included
