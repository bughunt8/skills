# Xero Chart of Accounts Manager attribution

This skill is adapted from the Chart of Accounts manager in
[Cogni AI OÜ's xero-fin-ops](https://github.com/Cogni-AI-OU/xero-fin-ops),
at commit
[`7efe1f5b98b719d08936f2b70fb4464ad4e5b851`](https://github.com/Cogni-AI-OU/xero-fin-ops/tree/7efe1f5b98b719d08936f2b70fb4464ad4e5b851).

- **Original author:** Cogni AI OÜ
- **Original copyright:** Copyright (c) 2026 Cogni AI OÜ
- **Original license:** MIT License
- **Upstream component:** `scripts/xero_coa_manager.py`
- **Discovery source:** [MCP Market listing](https://mcpmarket.com/tools/skills/xero-chart-of-accounts-manager)

The upstream utility accesses Xero's Chart of Accounts through its API. This
repository packages a documentation-only skill in its productivity layout,
rather than vendoring executable integration code or credential-handling
configuration. The skill retains the upstream use case while adding explicit
tenant selection, confirmation before writes, structured filtering, and secret
handling safeguards.

The complete upstream MIT License and copyright notice are preserved in
[LICENSE](LICENSE).
