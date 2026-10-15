# Provider bindings

Read this when a binding gate refuses, when regenerating assets, or when reviewing
provider selection. The shared `scripts/provider_bindings.py` supplies the same validation
to the builder, compiler and controller. It requires Python 3.10+ and PyYAML, already used
by repository CI. It does not import or edit the dependency checker or registry.

## Identity and invocation

The root is the checkout containing `AGENTS.md` and `skills/`. A `skills/` root is
unsupported. Provider directories and every tool/resource path are checkout-relative
POSIX paths starting with `skills/`. Absolute paths, traversal, empty components and
symlinked roots, providers or resources are refused.

Parse YAML, including quoted scalars, comments and anchors, rather than matching
identity with a line regex. The YAML `name` must match the provider directory.
Duplicate keys and malformed YAML, including an unquoted description containing
an invalid `: `, are refused. The parser never repairs metadata into a dispatchable binding.
Correct the actual owned source header through review, then regenerate and recompile.
Discovery skips resource/test directories, so bundled `SKILL.md` test fixtures are not providers.

Top-level and historical `metadata.disable-model-invocation` are both recognized.
Present values must be YAML booleans and must agree. Missing flags and explicit false
mean `model_or_user`; true means `user_only`. In particular, the existing nested false
on `start-github-repo` does not make it user-only.

If `agents/openai.yaml` exists, its policy must agree. Missing
`policy.allow_implicit_invocation` defaults to true; a present value must be boolean.
Codex false with model-allowed YAML, or Codex true/default with disabled YAML, refuses.
Registered providers must also match the read-only registry's identity, invocation and
required file hashes, including required Codex metadata and resources.

Do not invent a namespace. The path identifies the provider. Matt `grill-me` and
`handoff` are the actual `skills/productivity/` providers, not nonexistent engineering
providers. Matt research and hybrid research retain their distinct paths and names.
The compiler uses `--provider-path <exact-directory>` to resolve duplicate-name matches.
Every task and execute directive contains that path, the `SKILL.md` file and binding.
The host still must bind that exact file. A successful check does not prove it does.

## Inventory boundary and drift

`manifest.v2` records `provider_binding` with `provider.v1`, name, `skill_path`,
invocation and sorted file records of path, SHA-256 and file role. Tools also carry
their actual paths and hashes. References are full resource paths, not basenames.
The helper inventories the provider body, available client metadata, tools and
co-located non-derived files recursively. Standard ignored directories and Python
bytecode are excluded. This is file identity evidence, not proof of semantic correctness,
transitive dependencies outside the provider, approved side effects or worker budgets.

The harness's own `assets/harnesses/` are derived outputs and cannot hash themselves.
Only that canonical provider's generated manifest directory is excluded. Its schema
and other assets remain hashed. `harness_manifest_builder.py --check` separately
compares derived assets byte-for-byte with fresh timestamp-free generation.

The compiler validates manifest bindings against the live checkout. The controller
recomputes them for init, next, record, verify, close and status. Changing the body,
role, client policy, tool or resource, adding files, removing resources or forging a
task's role/path fails before state mutation or verification subprocess execution.
This does not authenticate plan/state authors, lock the filesystem against concurrent
writes, or validate every arbitrary verification command. Treat those JSON files as
trusted executable configuration and serialize source changes with runs.

## Refusal and recovery

- If any top-scoring match or selected task is user-only, compilation returns exit 8 with
  `HUMAN-COMMAND-REQUIRED` and no new output file. It does not fall through to a
  model provider. No executable task for any selected user-only provider is produced.
  An existing `--out` file is left unchanged; do not mistake it for a successful plan.
- Runtime user-only providers, forged bindings and live drift return exit 7. Re-check
  repository instructions and `python3 scripts/check_skill_dependencies.py --root .`.
  Do not update hashes to explain unexplained drift or use an approved setup plan as
  permission to call a user-only skill.
- Legacy manifests require regeneration. Legacy plans require recompilation. Legacy
  or drifted state requires review and a NEW state filename; preserve the original
  evidence. `init` refuses any existing state file, including an old-schema file.

From the final checkout, after all reviewed source edits:

```bash
H=skills/engineering/agent-harness/skills/agent-harness
python3 "$H/scripts/harness_manifest_builder.py" --all --repo-root . \
  --out-dir "$H/assets/harnesses" --no-timestamp
python3 "$H/scripts/harness_manifest_builder.py" --check --repo-root .
```

Both commands use exactly the 18 existing targets. `--domain` can narrow that set;
`--check --out-dir <fixture-dir>` can check temporary generated inventories. Check mode
never writes or resets state. Regenerate only with the builder, never hand-edit assets.
`--sample` inventory/plan outputs are marked `example_only`, use placeholder zero hashes
and illustrate JSON shape. They cannot be dispatched. The controller sample builds a real temporary fixture for its
transition demonstration; it does not prove a user's objective.

The harness's own SKILL.md uses the core Agent Skills fields. Provider-side
`disable-model-invocation`, `argument-hint` and `agents/openai.yaml` are client
extensions, not a claim that the core schema or every host implements them.
