# Project-management routing

Use the installed [PM command](commands/cs-pm.md) and
[orchestrator definition](agents/cs-pm-orchestrator.md) for qualified routing.
The repository root AGENTS.md and invocation policy retain approval authority.

## Retrospectives

The supported PM request is `/cs:pm sprint retrospective action items`.
It selects the existing [scrum-master](skills/scrum-master/SKILL.md)
discipline through the deterministic PM router.
Matt's `skills/engineering/retro/SKILL.md` is a human-only agent-environment
retrospective, not a team or sprint retrospective.

The historical CLAUDE.md advertises PM `/retro`, `/sprint-health` and
`/project-health` labels without matching installed command files.
Preserve that historical file, but do not treat those labels as active
bindings or permission to substitute Matt's skill. No Claude integration
is installed by this correction.

## Provider checks

From the trusted skills checkout root, run:

```bash
python3 skills/project-management/skills/pm-skills/scripts/pm_goal_router.py \
  --repo-root . --text "sprint retrospective action items" --output json
python3 scripts/check_skill_dependencies.py --include-legacy
python3 scripts/check_skill_dependencies.py --resolve-pm-retrospective --invoker user
```

Require a verified exact provider path. An output classification without
`--repo-root` is unqualified and cannot authorize dispatch.
The supplied root must be this router's own checkout. Foreign roots, dangling
client metadata links and drift from the registered PM hashes block qualification.
The resolver emits metadata only and invokes nothing. Host registration,
MCP access, data handling and mutation approvals remain separate checks.
