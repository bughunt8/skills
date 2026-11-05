#!/usr/bin/env python3
"""Track the pinned Matt Pocock release across the manifest and dependency registry.

The tracker is deliberately conservative. It updates pins, hashes, source URLs,
attribution, docs and generated visualisation. It refuses a release that changes
the provider set, provider paths, invocation policy or operative graph evidence,
because those require a parser review.

    scripts/track_matt_release.py --check [--ref main] [--json]
    scripts/track_matt_release.py --write [--ref main]
    scripts/track_matt_release.py --self-test

Exit codes: 0 current or updated, 1 update available (--check), 2 semantic or
gate refusal, 3 copy-back rollback.
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import check_skill_dependencies as checker
import check_legacy_bindings as legacy

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("skills/vendor.manifest.json")
REGISTRY = Path(".agents/skill-dependencies.json")
MATT = "mattpocock-"
CURRENT_DOCS = (
    Path(".agents/invocation.md"),
    Path("AGENTS.md"),
    Path("README.md"),
    Path("docs/legacy-harness-bindings.md"),
)
TRACKING_DOC = Path("docs/matt-pocock-tracking.md")
LIBRARY_SIZE = Path("site/tests/library-size.mjs")


class Refusal(Exception):
    def __init__(self, status: str, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def _run(args, cwd=ROOT):
    proc = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _git(args, cwd=ROOT):
    return _run(["git", *args], cwd)


def _load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _write(path, text, root=ROOT):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _today():
    return _dt.date.today().isoformat()


def _clean(root):
    return _git(["status", "--porcelain"], root) == ""


def latest_tag(repo):
    for tag in _git(["tag", "--sort=-v:refname"], repo).splitlines():
        if re.fullmatch(r"v\d+\.\d+\.\d+", tag):
            return tag
    raise Refusal("refused_invalid_upstream", "upstream has no semver release tag")


def resolve_target(upstream, ref):
    ref = ref or latest_tag(upstream)
    commit = _git(["rev-parse", f"{ref}^{{commit}}"], upstream)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise Refusal("refused_invalid_upstream", f"cannot resolve {ref}")
    return ref, commit


def upstream_tree(upstream_dir, upstream_url):
    """Return (path, transport, cleanup). transport is what sync_vendor fetches."""
    if upstream_dir:
        path = Path(upstream_dir).resolve()
        if not (path / ".git").is_dir():
            raise Refusal("refused_invalid_upstream", f"not a git repository: {path}")
        return path, str(path), lambda: None
    url = upstream_url or checker.REPO
    temp = Path(tempfile.mkdtemp(prefix="matt-upstream-"))
    _run(["git", "clone", "--quiet", url, str(temp)])
    return temp, str(temp), lambda: shutil.rmtree(temp, ignore_errors=True)


def _release_version(upstream, ref):
    plugin = upstream / ".claude-plugin/plugin.json"
    if plugin.is_file():
        value = json.loads(plugin.read_text(encoding="utf-8")).get("version")
        if isinstance(value, str) and value:
            return value
    return ref[1:] if ref.startswith("v") else ref


def build_proposal(upstream, commit, release_ref, transport, root=ROOT):
    registry = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    old_pin = registry["upstream_commit"]
    old_ref = registry["release_ref"]
    old_count = registry.get("provider_count", len(registry["providers"]))

    providers = registry["providers"]
    expected = {e["source_path"] for e in providers}
    scopes = {"/".join(Path(e["source_path"]).parts[:2]) for e in providers}
    ignored = set(registry.get("untracked_scopes", []))
    upstream_skills = upstream / "skills"
    domains = {
        "skills/" + p.relative_to(upstream_skills).parts[0]
        for p in upstream_skills.rglob("SKILL.md")
        if not p.is_symlink()
    }
    new_scopes = sorted(domains - scopes - ignored)
    if new_scopes:
        raise Refusal(
            "refused_semantic",
            f"new upstream scope requires review: {new_scopes}",
        )
    actual = {
        p.parent.relative_to(upstream).as_posix()
        for scope in scopes
        for p in (upstream / scope).rglob("SKILL.md")
        if not p.is_symlink()
    }
    if actual != expected:
        missing = sorted(expected - actual)
        added = sorted(actual - expected)
        raise Refusal(
            "refused_semantic",
            f"provider set changed: missing={missing} added={added}",
        )

    licence = upstream / "LICENSE"
    if not licence.is_file():
        raise Refusal("refused_invalid_upstream", "upstream has no LICENSE")
    legal_sha = _sha(licence)
    release = _release_version(upstream, release_ref)

    new_registry = copy.deepcopy(registry)
    new_registry["upstream_commit"] = commit
    new_registry["release"] = release
    new_registry["release_ref"] = release_ref
    new_registry["legal_resource"] = {
        "source_path": "LICENSE",
        "sha256": legal_sha,
        "source_url": f"{checker.REPO}/blob/{commit}/LICENSE",
    }
    for e in new_registry["providers"]:
        source = upstream / e["source_path"]
        skill = source / "SKILL.md"
        codex = source / "agents/openai.yaml"
        if not skill.is_file() or not codex.is_file():
            raise Refusal("refused_invalid_upstream", f"missing provider files: {e['name']}")
        try:
            fm = checker.frontmatter(skill)
            meta = checker.codex(codex)
        except Exception as exc:
            raise Refusal("refused_semantic", f"invalid provider metadata: {e['name']}: {exc}")
        disabled = checker.disabled(fm)
        mode = "user_only" if disabled else "model_or_user"
        implicit = meta.get("policy", {}).get("allow_implicit_invocation", True)
        if mode != e["invocation"] or implicit == disabled:
            raise Refusal("refused_semantic", f"invocation policy changed: {e['name']}")
        lines = skill.read_text(encoding="utf-8").splitlines()
        for edge in e["operative"]:
            for evidence in edge["evidence_occurrences"]:
                line = evidence["line"]
                if (line < 1 or line > len(lines) or lines[line - 1] != evidence["text"]):
                    raise Refusal(
                        "refused_semantic",
                        f"graph evidence changed: {e['name']} -> {edge['target']}",
                    )
        e["upstream_commit"] = commit
        e["source_url"] = f"{checker.REPO}/blob/{commit}/{e['path']}"
        for f in e["files"]:
            path = upstream / f["path"]
            if not path.is_file() or path.is_symlink():
                raise Refusal("refused_invalid_upstream", f"missing resource: {f['path']}")
            f["sha256"] = _sha(path)
            f["source_url"] = f"{checker.REPO}/blob/{commit}/{f['source_path']}"
    new_registry["provider_count"] = len(providers)
    new_registry["file_count"] = sum(len(e["files"]) for e in providers)
    new_registry["operative_count"] = sum(len(e["operative"]) for e in providers)

    new_manifest = copy.deepcopy(manifest)
    for source in new_manifest["sources"]:
        if not source["id"].startswith(MATT):
            continue
        source["ref"] = release_ref
        source["pinned_commit"] = commit
        source["expected_commit"] = commit
        source["pinned_at"] = _today()
        source["fetch_repo"] = transport
        first = source.get("paths", [{}])[0].get("from", "")
        source["homepage"] = (
            f"{checker.REPO}/tree/{commit}/{first}" if first else f"{checker.REPO}/tree/{commit}"
        )
    return {
        "registry": new_registry,
        "manifest": new_manifest,
        "old_pin": old_pin,
        "old_ref": old_ref,
        "old_count": old_count,
        "release": release,
        "release_ref": release_ref,
        "commit": commit,
    }


def _write_proposal(root, proposal, with_fetch):
    manifest = copy.deepcopy(proposal["manifest"])
    if not with_fetch:
        for source in manifest["sources"]:
            source.pop("fetch_repo", None)
    _write(MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", root)
    _write(
        REGISTRY,
        json.dumps(proposal["registry"], indent=2, ensure_ascii=False) + "\n",
        root,
    )


def _matt_ids(manifest):
    return [s["id"] for s in manifest["sources"] if s["id"].startswith(MATT)]


def _sync(root, manifest):
    args = [sys.executable, "scripts/sync_vendor.py", "--sync"]
    for source_id in _matt_ids(manifest):
        args += ["--source", source_id]
    _run(args, root)


def _regenerate(root):
    _run([sys.executable, "scripts/generate_index.py", "--write"], root)
    _run([sys.executable, "site/build.py", "--write"], root)
    harness = "skills/engineering/agent-harness/skills/agent-harness"
    _run(
        [
            sys.executable,
            f"{harness}/scripts/harness_manifest_builder.py",
            "--all",
            "--repo-root",
            ".",
            "--no-timestamp",
            "--out-dir",
            f"{harness}/assets/harnesses",
        ],
        root,
    )
    _update_library_size(root)
    _update_docs(root, proposal=None)


def _update_library_size(root):
    path = root / LIBRARY_SIZE
    data = (root / "site/data.js").read_text(encoding="utf-8")
    match = re.search(r"window\.SKILLDATA=(\{.*\});", data, re.S)
    if not match:
        raise Refusal("failed_gates", "site/data.js has no SKILLDATA")
    payload = json.loads(match.group(1))
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"export const EXPECTED_TOTAL = \d+;", f"export const EXPECTED_TOTAL = {payload['total']};", text)
    text = re.sub(r"export const EXPECTED_CATEGORIES = \d+;", f"export const EXPECTED_CATEGORIES = {payload['categories']};", text)
    text = re.sub(r"export const EXPECTED_SOLUTIONS = \d+;", f"export const EXPECTED_SOLUTIONS = {payload['solutions']};", text)
    text = re.sub(r"\nexport const EXPECTED_COMMUNITIES = \d+;", "", text)
    path.write_text(text, encoding="utf-8")


def _update_docs(root, proposal, old=None, new=None):
    """Replace current-pin references, never a historical release name or link.

    Versioned guides such as ``docs/matt-pocock-v1.3.1.md`` keep their own
    filename and link text. Rewriting the release string here would produce a
    link to a document that does not exist. The generated block below is the
    live release snapshot.
    """
    registry = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    if old is not None:
        old_pin, _old_ref, old_count = old
        new_pin = proposal["commit"]
        new_count = registry["provider_count"]
        for relative in CURRENT_DOCS:
            path = root / relative
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            updated = text.replace(old_pin, new_pin).replace(
                f"{old_count} stable", f"{new_count} stable"
            )
            if updated != text:
                path.write_text(updated, encoding="utf-8")
    block = (
        "<!-- BEGIN MATT RELEASE -->\n"
        f"| Release | `{registry['release_ref']}` |\n"
        f"| Commit | `{registry['upstream_commit']}` |\n"
        f"| Providers | {registry['provider_count']} |\n"
        f"| Files | {registry['file_count']} |\n"
        f"| Operative edges | {registry['operative_count']} |\n"
        "<!-- END MATT RELEASE -->"
    )
    doc = root / TRACKING_DOC
    if doc.is_file():
        text = doc.read_text(encoding="utf-8")
        if "<!-- BEGIN MATT RELEASE -->" in text:
            text = re.sub(
                r"<!-- BEGIN MATT RELEASE -->.*?<!-- END MATT RELEASE -->",
                block,
                text,
                flags=re.S,
            )
            doc.write_text(text, encoding="utf-8")


def _verify(root):
    checks = [
        [sys.executable, "scripts/check_skill_dependencies.py", "--include-legacy"],
        [sys.executable, "scripts/sync_vendor.py", "--validate-manifest"],
        [sys.executable, "scripts/generate_index.py", "--check"],
        [sys.executable, "site/build.py", "--check"],
        [sys.executable, "scripts/lint_skills.py"],
        [sys.executable, "scripts/audit_third_party.py"],
        [sys.executable, "scripts/check_links.py"],
        [sys.executable, "scripts/check_solutions.py"],
        [sys.executable, "skills/engineering/agent-harness/skills/agent-harness/scripts/harness_manifest_builder.py", "--check", "--repo-root", "."],
    ]
    for command in checks:
        _run(command, root)


def apply_proposal(root, proposal, copy_back=True):
    """Apply a proposal to a checkout root. Used by the CLI and fixture tests."""
    _write_proposal(root, proposal, with_fetch=True)
    _sync(root, proposal["manifest"])
    _write_proposal(root, proposal, with_fetch=False)
    registry = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    registry["legacy_bindings"] = legacy.build_records(root)
    _write(REGISTRY, json.dumps(registry, indent=2, ensure_ascii=False) + "\n", root)
    _regenerate(root)
    _update_docs(root, proposal, old=(proposal["old_pin"], proposal["old_ref"], proposal["old_count"]))
    _verify(root)


def _copy_back(root, worktree):
    status = _git(["status", "--porcelain", "-uall"], worktree)
    for line in status.splitlines():
        code, _, path = line.partition(" ")
        path = path.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if not path:
            continue
        source = worktree / path
        target = root / path
        if code.strip() == "D" or not source.exists():
            if target.exists():
                target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    try:
        _verify(root)
    except Exception as exc:
        _git(["restore", "--source=HEAD", "."], root)
        _git(["clean", "-fd"], root)
        raise Refusal("rolled_back", f"post-copy verification failed: {exc}")


def run_check(root, upstream_dir, upstream_url, ref):
    upstream, transport, cleanup = upstream_tree(upstream_dir, upstream_url)
    try:
        release_ref, commit = resolve_target(upstream, ref)
        proposal = build_proposal(upstream, commit, release_ref, transport, root)
        current = proposal["old_pin"] == commit and proposal["old_ref"] == release_ref
        if current:
            return {"status": "current", "changed": False, "target": commit}
        worktree = Path(tempfile.mkdtemp(prefix="matt-check-"))
        worktree.rmdir()
        _git(["worktree", "add", "--detach", str(worktree), "HEAD"], root)
        try:
            apply_proposal(worktree, proposal)
        finally:
            _git(["worktree", "remove", "--force", str(worktree)], root)
        return {"status": "update_available", "changed": True, "target": commit}
    finally:
        cleanup()


def run_write(root, upstream_dir, upstream_url, ref):
    if not _clean(root):
        raise Refusal("refused_invalid_upstream", "working tree is not clean")
    upstream, transport, cleanup = upstream_tree(upstream_dir, upstream_url)
    try:
        release_ref, commit = resolve_target(upstream, ref)
        proposal = build_proposal(upstream, commit, release_ref, transport, root)
        registry = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
        if registry["upstream_commit"] == commit and registry["release_ref"] == release_ref:
            return {"status": "current", "changed": False, "target": commit}
        worktree = Path(tempfile.mkdtemp(prefix="matt-write-"))
        worktree.rmdir()
        _git(["worktree", "add", "--detach", str(worktree), "HEAD"], root)
        try:
            apply_proposal(worktree, proposal)
            _copy_back(root, worktree)
        finally:
            _git(["worktree", "remove", "--force", str(worktree)], root)
        return {"status": "updated", "changed": True, "target": commit}
    finally:
        cleanup()


def self_test():
    registry = _load(REGISTRY)
    manifest = _load(MANIFEST)
    assert registry["upstream_repository"] == checker.REPO
    assert registry["provider_count"] == len(registry["providers"])
    assert registry["file_count"] == sum(len(e["files"]) for e in registry["providers"])
    assert registry["operative_count"] == sum(len(e["operative"]) for e in registry["providers"])
    assert _matt_ids(manifest)
    print("PASS: registry counts, manifest Matt sources and canonical repository")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    parser.add_argument("--ref")
    parser.add_argument("--upstream-dir")
    parser.add_argument("--upstream-url")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            self_test()
            return 0
        result = (
            run_check(ROOT, args.upstream_dir, args.upstream_url, args.ref)
            if args.check
            else run_write(ROOT, args.upstream_dir, args.upstream_url, args.ref)
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"{result['status']}: {result['target']}")
        return 0 if result["status"] in ("current", "updated") else 1
    except Refusal as exc:
        if args.json:
            print(json.dumps({"status": exc.status, "message": exc.message}, indent=2))
        else:
            print(f"{exc.status}: {exc.message}", file=sys.stderr)
        return 3 if exc.status == "rolled_back" else 2
    except Exception as exc:
        if args.json:
            print(json.dumps({"status": "failed_gates", "message": str(exc)}, indent=2))
        else:
            print(f"failed_gates: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
