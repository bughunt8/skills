#!/usr/bin/env python3
"""Conservatively analyze and organize a project's documentation structure."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable


@dataclass(frozen=True)
class Suggestion:
    """One explicit, reviewable filesystem operation."""

    action: str
    source: str | None
    destination: str | None
    reason: str
    risk: str


class SafeProjectOrganizer:
    """Create and execute a deliberately narrow, safe organization plan."""

    PROTECTED_DIRECTORY_NAMES = {
        ".git",
        ".hg",
        ".svn",
        ".next",
        ".nuxt",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "out",
        "vendor",
        "venv",
    }
    PROTECTED_FILE_PATTERNS = (
        ".env*",
        "*.lock",
        "credentials.*",
        "secrets.*",
    )
    ROOT_DOCUMENTATION_EXCLUSIONS = {
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "LICENSE.md",
        "NOTICE",
        "README.md",
        "SECURITY.md",
    }
    DOCUMENTATION_EXTENSIONS = {".adoc", ".md", ".rst", ".txt"}

    def __init__(self, project_root: str) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        if not self.project_root.is_dir():
            raise ValueError(f"Project root is not a directory: {self.project_root}")

    def _relative_path(self, path: Path) -> Path:
        """Resolve *path* and reject values outside the project root."""
        resolved = path.resolve()
        try:
            return resolved.relative_to(self.project_root)
        except ValueError as error:
            raise ValueError(f"Path escapes project root: {path}") from error

    def _is_protected(self, path: Path) -> bool:
        """Return whether a project-relative path must never be modified."""
        relative = self._relative_path(path)
        if any(part in self.PROTECTED_DIRECTORY_NAMES for part in relative.parts):
            return True
        return any(
            fnmatch.fnmatch(relative.name, pattern)
            for pattern in self.PROTECTED_FILE_PATTERNS
        )

    def _walk_unprotected(self) -> Iterable[tuple[Path, list[str], list[str]]]:
        """Walk the project without descending into protected directories."""
        for root, directories, files in os.walk(self.project_root):
            root_path = Path(root)
            directories[:] = [
                name
                for name in directories
                if not self._is_protected(root_path / name)
            ]
            yield root_path, directories, files

    def scan(self) -> dict[str, object]:
        """Return a read-only inventory needed to make conservative suggestions."""
        files = 0
        directories = 0
        protected = 0
        empty_directories: list[str] = []
        root_files: list[str] = []
        root_directories: list[str] = []
        file_types: Counter[str] = Counter()

        for root, child_directories, child_files in self._walk_unprotected():
            directories += len(child_directories)
            if root == self.project_root:
                root_files = sorted(child_files)
                root_directories = sorted(child_directories)
            if root != self.project_root and not child_directories and not child_files:
                empty_directories.append(str(self._relative_path(root)))

            for file_name in child_files:
                file_path = root / file_name
                if self._is_protected(file_path):
                    protected += 1
                    continue
                try:
                    file_path.stat()
                except OSError as error:
                    print(f"Warning: cannot access {file_path}: {error}")
                    continue
                files += 1
                file_types[file_path.suffix.lower() or "[no extension]"] += 1

        return {
            "directories": directories,
            "empty_directories": sorted(empty_directories),
            "files": files,
            "file_types": dict(sorted(file_types.items())),
            "protected_items": protected,
            "root_directories": root_directories,
            "root_files": root_files,
        }

    def _documentation_moves(self, root_files: Iterable[str]) -> list[Suggestion]:
        """Suggest only non-canonical root documentation moves."""
        suggestions: list[Suggestion] = []
        for name in root_files:
            path = self.project_root / name
            if (
                name in self.ROOT_DOCUMENTATION_EXCLUSIONS
                or path.suffix.lower() not in self.DOCUMENTATION_EXTENSIONS
                or self._is_protected(path)
            ):
                continue
            destination = self.project_root / "docs" / name
            if destination.exists():
                continue
            suggestions.append(
                Suggestion(
                    action="move",
                    source=name,
                    destination=str(Path("docs") / name),
                    reason="Move non-canonical root documentation into docs/",
                    risk="medium",
                )
            )
        return suggestions

    def analyze(self, scan: dict[str, object]) -> list[Suggestion]:
        """Produce a stable and duplicate-free plan from a completed scan."""
        suggestions = self._documentation_moves(scan["root_files"])  # type: ignore[arg-type]
        if suggestions and "docs" not in scan["root_directories"]:  # type: ignore[operator]
            suggestions.insert(
                0,
                Suggestion(
                    action="create_dir",
                    source=None,
                    destination="docs",
                    reason="Create docs/ for approved documentation moves",
                    risk="low",
                ),
            )

        suggestions.extend(
            Suggestion(
                action="delete_empty_dir",
                source=directory,
                destination=None,
                reason="Remove a verified empty directory",
                risk="low",
            )
            for directory in scan["empty_directories"]  # type: ignore[union-attr]
        )
        return suggestions

    def _path_for(self, relative_path: str) -> Path:
        """Convert a planned relative path to a contained absolute path."""
        return self.project_root / self._relative_path(self.project_root / relative_path)

    def preflight(self, suggestions: Iterable[Suggestion]) -> list[str]:
        """Return all reasons a plan is no longer safe to execute."""
        failures: list[str] = []
        destinations: set[Path] = set()
        for suggestion in suggestions:
            if suggestion.action == "move":
                assert suggestion.source and suggestion.destination
                source = self._path_for(suggestion.source)
                destination = self._path_for(suggestion.destination)
                if not source.is_file():
                    failures.append(f"Move source is unavailable: {suggestion.source}")
                if self._is_protected(source) or self._is_protected(destination):
                    failures.append(f"Move touches a protected path: {suggestion.source}")
                if destination.exists():
                    failures.append(f"Move destination exists: {suggestion.destination}")
                if destination in destinations:
                    failures.append(f"Duplicate destination: {suggestion.destination}")
                destinations.add(destination)
            elif suggestion.action == "create_dir":
                assert suggestion.destination
                destination = self._path_for(suggestion.destination)
                if destination.exists() and not destination.is_dir():
                    failures.append(f"Directory target is a file: {suggestion.destination}")
                if self._is_protected(destination):
                    failures.append(f"Directory target is protected: {suggestion.destination}")
            elif suggestion.action == "delete_empty_dir":
                assert suggestion.source
                target = self._path_for(suggestion.source)
                if not target.is_dir():
                    failures.append(f"Empty directory is unavailable: {suggestion.source}")
                elif any(target.iterdir()):
                    failures.append(f"Directory is no longer empty: {suggestion.source}")
                elif self._is_protected(target):
                    failures.append(f"Directory is protected: {suggestion.source}")
            else:
                failures.append(f"Unknown action: {suggestion.action}")
        return failures

    @staticmethod
    def print_scan(scan: dict[str, object]) -> None:
        """Print a compact scan summary without disclosing file contents."""
        print("Read-only scan complete")
        print(f"  Directories: {scan['directories']}")
        print(f"  Files: {scan['files']}")
        print(f"  Protected items skipped: {scan['protected_items']}")
        print(f"  Empty directories: {len(scan['empty_directories'])}")

    @staticmethod
    def print_preview(suggestions: Iterable[Suggestion]) -> None:
        """Print each proposed operation for user review."""
        suggestions = list(suggestions)
        print("\nPREVIEW MODE — no changes will be made")
        if not suggestions:
            print("No conservative organization suggestions found.")
            return
        for number, suggestion in enumerate(suggestions, start=1):
            print(f"\n{number}. [{suggestion.risk.upper()}] {suggestion.reason}")
            if suggestion.source:
                print(f"   from: {suggestion.source}")
            if suggestion.destination:
                print(f"   to:   {suggestion.destination}")

    def execute(self, suggestions: Iterable[Suggestion], dry_run: bool) -> dict[str, object]:
        """Apply a preflighted plan, or report exactly what a dry run would do."""
        suggestions = list(suggestions)
        failures = self.preflight(suggestions)
        if failures:
            raise RuntimeError("Preflight failed:\n- " + "\n- ".join(failures))

        results: list[dict[str, object]] = []
        rollback: list[dict[str, str]] = []
        for suggestion in suggestions:
            result = asdict(suggestion)
            result["status"] = "simulated" if dry_run else "executed"
            results.append(result)
            if suggestion.action == "move":
                assert suggestion.source and suggestion.destination
                if not dry_run:
                    self._path_for(suggestion.source).rename(
                        self._path_for(suggestion.destination)
                    )
                rollback.append(
                    {
                        "action": "move",
                        "source": suggestion.destination,
                        "destination": suggestion.source,
                    }
                )
            elif suggestion.action == "create_dir":
                assert suggestion.destination
                target = self._path_for(suggestion.destination)
                if not dry_run and not target.exists():
                    target.mkdir()
                    rollback.append({"action": "remove_empty_dir", "path": suggestion.destination})
            elif suggestion.action == "delete_empty_dir":
                assert suggestion.source
                if not dry_run:
                    self._path_for(suggestion.source).rmdir()
                rollback.append({"action": "create_dir", "path": suggestion.source})

        return {"dry_run": dry_run, "results": results, "rollback": rollback}

    def save_log(self, outcome: dict[str, object]) -> None:
        """Atomically write the audit record after real execution."""
        log_path = self.project_root / ".project_organizer.log"
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **outcome,
        }
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.project_root, delete=False
        ) as temporary:
            json.dump(record, temporary, indent=2)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        temporary_path.replace(log_path)
        print(f"Audit log: {log_path}")


def main() -> None:
    """Parse CLI arguments and guide the scan-preview-execute workflow."""
    parser = argparse.ArgumentParser(description="Safe Project Organizer")
    parser.add_argument("project_path", help="path to the project root")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--scan", action="store_true", help="scan only (default)")
    mode.add_argument("--preview", action="store_true", help="show suggestions")
    mode.add_argument("--execute", action="store_true", help="simulate suggestions")
    mode.add_argument(
        "--execute-real", action="store_true", help="apply suggestions after confirmation"
    )
    arguments = parser.parse_args()

    organizer = SafeProjectOrganizer(arguments.project_path)
    scan = organizer.scan()
    organizer.print_scan(scan)
    if arguments.scan or not (arguments.preview or arguments.execute or arguments.execute_real):
        return

    suggestions = organizer.analyze(scan)
    organizer.print_preview(suggestions)
    if arguments.preview:
        return

    dry_run = arguments.execute
    if arguments.execute_real:
        confirmation = input("\nApply this exact plan? Type 'yes' to continue: ")
        if confirmation.strip().lower() != "yes":
            print("Cancelled; no changes were made.")
            return

    outcome = organizer.execute(suggestions, dry_run=dry_run)
    print(f"\n{'Simulated' if dry_run else 'Executed'} {len(outcome['results'])} operation(s).")
    if not dry_run:
        organizer.save_log(outcome)


if __name__ == "__main__":
    main()
