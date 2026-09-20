# CodeGraph setup and use

This profile uses `@colbymchenry/codegraph`, the tool referenced by AI-CMO,
not another similarly named graph product. Use the
[upstream README](https://github.com/colbymchenry/codegraph) and
[indexing guide](https://colbymchenry.github.io/codegraph/guides/indexing/)
to verify the selected version's commands and capabilities before installation.

## Install and configure

1. Inspect the existing CLI, package manager, supported languages, platform,
   `codegraph.json`, ignore rules, and configured agent clients. If installed,
   record `codegraph --version` and inspect its help. Do not replace a working
   version or agent configuration without an approved diff.
2. Choose an exact supported release and verify its package provenance and
   runtime requirements. Record the version and installation scope in README.
   Use the project's approved tool manager or exact-version npm installation,
   such as `npm install --global @colbymchenry/codegraph@EXACT_VERSION` only
   when a global install is authorized. `EXACT_VERSION` must be resolved.
   Do not pipe an unpinned remote installer into a shell.
3. Configure only the user's selected non-Claude client. First inspect
   `codegraph install --help` and, where supported,
   `codegraph install --print-config CLIENT_ID`. The MCP server command is
   `codegraph serve --mcp`; client configuration schemas differ.
4. Prefer project-local settings with an explicit target and
   `--location=local` if supported by the pinned release. Never use bare
   `--yes` or `--target=auto` here: they can configure undesired clients or
   global settings. Do not select Claude, create CLAUDE.md/Claude.md, modify
   `.claude/`, or add wildcard tool approvals. Review instruction-file changes.
   If the installer cannot respect this scope, merge the printed config into
   the approved client manually. Restart the client when needed.
5. Commit `codegraph.json` and ignore `.codegraph/`. Add ignore entries for
   any approved alternate local index directories. Do not commit SQLite
   databases, caches, locks, or machine-specific paths.
6. Run `codegraph init` in the repository/worktree to build its graph.
   Client installation alone does not prove indexing. Inspect the diff after
   initialization and preserve the no-Claude and single-protocol rules.
7. Run `codegraph status`, a known-symbol query and caller/impact query.
   Record CLI version, indexed path, commit, counts, excluded paths, and
   results. Verify `codegraph_explore` through the actual selected MCP client
   before calling the integration operational. If only CLI was tested, say so.

No client or version has been selected merely by installing this skill.
If the target environment prevents install, report setup as blocked and
retain source-search fallback instead of claiming CodeGraph is configured.

## Committed index policy

Use the inspected release's schema. The upstream configuration supports
root-relative gitignore-style `exclude` patterns; use actual paths, not a
blind copy of AI-CMO's fixture directory. For example, after confirming the
target contains that intentionally invalid fixture tree:

```json
{
  "exclude": ["tools/arch-check/test/fixtures/"]
}
```

Document each exclusion and its reason in AGENTS.md or a linked graph setup
section. Exclude deliberately invalid fixtures that masquerade as production
symbols, generated/build/vendor output as appropriate, and sensitive files.
Do not exclude all tests or first-party modules: impact analysis needs their
relationships. Do not use `include` to override ignored secrets.

`deprioritize` lowers ranking but does not exclude a path. Add it only with a
reason; do not copy AI-CMO's application ranking choices. Confirm both a
known real symbol is found and a unique invalid fixture symbol is absent
after reindexing. Search absence alone does not prove a symbol cannot exist.

## Freshness, worktrees and limits

- Run `codegraph sync` and `codegraph status` before relying on CLI analysis
  outside an active watcher session. Use `codegraph index --force` when
  required after configuration/version changes, confirming supported flags.
  Read live source when the tool reports pending changes or missing coverage.
- Initialize and query the correct task worktree. Verify the reported project
  path and a branch-specific symbol; do not let workers share a mutable index
  pointed at different revisions. Respect writer locks; never remove a live
  lock as a shortcut. Document supported daemon behavior for the pinned version.
- In AGENTS.md and Agent-Protocol.md, instruct agents to inspect relevant
  symbols, callers, dependencies and impact before editing, then confirm
  critical findings against source and tests. Graphs guide navigation;
  dynamic behavior, excluded files and unsupported languages can be missed.
- Local indexing does not mean model use is offline: snippets returned over
  MCP enter the selected agent's context. Apply the project's source-code
  disclosure policy and do not promise that nothing leaves the machine.
- Affected-test selection is an inner-loop optimization only. The full
  required verification suite remains the merge gate. If no affected tests
  are found, fall back to the full relevant suite rather than claiming success.
- Optional package scripts may wrap `codegraph index . --force`,
  `codegraph sync .`, and `codegraph status .` after command validation.
  Do not copy AI-CMO's test command, runtime pin, or timing claims.

Setup acceptance needs successful CLI indexing, a real positive query,
negative-fixture exclusion where applicable, a changed-file refresh check,
and a query from the chosen agent client. Record unavailable checks explicitly.
