"""Behavior and mutation tests. Approval fixtures are not real authorization."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "sdd.py"
spec = importlib.util.spec_from_file_location("sdd", SCRIPT)
sdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdd)


class SDDTests(unittest.TestCase):
    def setUp(self):
        # Test data only. No repository files or real approval records change.
        self.temp = tempfile.TemporaryDirectory(prefix="sdd-test-")
        self.addCleanup(self.temp.cleanup)
        self.temp_root = Path(self.temp.name).resolve()
        self.root = self.temp_root / "project"
        shutil.copytree(SKILL / "examples" / "minimal", self.root)
        self.target = self.root / ".specs"

    def replace(self, name, old, new):
        path = self.target / f"{name}.md"
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def rejected(self, function, *args, contains=None):
        with self.assertRaises((sdd.Invalid, ValueError, OSError)) as caught:
            function(*args)
        if contains:
            self.assertIn(contains, str(caught.exception))

    def approve_fixture(self, phase="pre-build", completed=None, task="TASK-1"):
        """Simulated human record solely for testing authorization conditions."""
        review_path = self.root / "review.example.json"
        review = json.loads(review_path.read_text())
        review["phase"] = phase
        review["reviewed_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        if phase == "post-build":
            review["task"] = task
        planned = sdd.lint(self.root, self.target, "tasks")
        relevant = set(planned["tasks"]) if phase == "pre-build" else {
            key for key, row in planned["execution"].items() if row["Status"] == "completed"
        } | {task}
        review["scope_files"] = sorted({raw for key in relevant for raw in sdd.values(planned["tasks"][key]["Files"])})
        review["implementation_files"] = [raw for raw in review["scope_files"] if not raw.startswith("tests/")]
        review_path.write_text(json.dumps(review), encoding="utf-8")
        result = sdd.analyze(self.root, self.target, review_path)
        analysis_path = self.root / result["analysis"]
        approval = {
            "decision": "approved",
            "authority": "human",
            "authorizer": "TEST FIXTURE ONLY, not a real authorizer",
            "statement": "Simulated approval for automated tests only",
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "analysis": result["analysis"],
            "snapshot": result["snapshot"],
            "analysis_hash": sdd.digest(analysis_path.read_bytes()),
            "cross_analysis_hash": sdd.digest((self.target / "CROSS_ANALYSIS.md").read_bytes()),
            "completed": completed or {},
            "task": task,
        }
        approval_path = self.root / "test-only-approval.json"
        approval_path.write_text(json.dumps(approval), encoding="utf-8")
        return approval_path

    def execution_fixture(self, task="TASK-1", status="in-progress"):
        proof = {}
        for field in ("red", "green", "refactor", "verified"):
            file = self.root / "evidence" / f"{task.lower()}-{field}.txt"
            file.write_text(f"TEST FIXTURE {field} evidence only; not real results.")
            proof[field] = file.relative_to(self.root).as_posix()
        path = self.target / "TASKS.md"
        text = path.read_text()
        old = next(line for line in text.splitlines() if line.startswith(f"| {task} |") and "| REQ" not in line)
        verification = proof["verified"] if status == "completed" else "-"
        text = text.replace(old, f"| {task} | {status} | {proof['red']} | {proof['green']} | {proof['refactor']} | {verification} |")
        path.write_text(text)
        return proof

    def completed_fixture(self):
        proof = self.execution_fixture()
        post = self.approve_fixture("post-build")
        sdd.gate(self.root, self.target, post, purpose="verify")
        data = json.loads(post.read_text())
        self.execution_fixture(status="completed")
        return {"TASK-1": {"path": proof["verified"],
                            "sha256": sdd.file_digest(self.root / proof["verified"]),
                            "analysis": data["analysis"], "analysis_hash": data["analysis_hash"]}}

    def add_second_task(self, depends="TASK-1", future_files=False):
        path = self.target / "TASKS.md"
        text = path.read_text()
        row = next(line for line in text.splitlines() if line.startswith("| TASK-1 | REQ"))
        second = row.replace("TASK-1", "TASK-2").replace("| OBS-1 | - |", f"| OBS-1 | {depends} |")
        if future_files:
            second = second.replace(
                "| app.py, tests/test_app.py |",
                "| app.py, tests/test_app.py, app2.py, tests/test_app2.py |").replace(
                "tests/test_app.py#test_accept,",
                "tests/test_app2.py#test_future, tests/test_app.py#test_accept,")
        text = text.replace("\n\n## Execution log", "\n" + second + "\n\n## Execution log")
        text = text.replace("| TASK-1 | planned | - | - | - | - |",
                            "| TASK-1 | planned | - | - | - | - |\n| TASK-2 | planned | - | - | - | - |")
        path.write_text(text)

    def test_filled_structural_example(self):
        result = sdd.lint(self.root, self.target)
        self.assertEqual(result["order"], ["TASK-1"])
        self.assertEqual(len(result["criteria"]), 3)

    def test_bounded_legacy_adapter_is_invoked_when_adjacent(self):
        installed = self.temp_root / "engineering"
        scripts = installed / "spec-driven-development" / "scripts"
        scripts.mkdir(parents=True)
        legacy = installed / "skills" / "spec-driven-workflow" / "scripts"
        legacy.mkdir(parents=True)
        (legacy / "test_extractor.py").write_text(
            "class SpecParser:\n"
            "    def __init__(self, content): self.content = content\n"
            "    def extract_acceptance_criteria(self):\n"
            "        raise ValueError('LEGACY_PARSER_INVOKED')\n")
        with patch.object(sdd, "HERE", scripts):
            self.rejected(sdd.lint, self.root, self.target, "spec", contains="LEGACY_PARSER_INVOKED")

    def test_demo_tests_actually_run(self):
        run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                             cwd=self.root, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Ran 4 tests", run.stderr)

    def test_draft_scaffold_rejected_and_no_clobber(self):
        blank = self.temp_root / "blank"
        blank.mkdir()
        root, target = sdd.resolve(blank)
        result = sdd.scaffold(root, target)
        self.assertEqual(result["status"], "draft")
        self.assertEqual(len(result["created"]), 11)
        before = {p.name: p.read_bytes() for p in target.glob("*.md")}
        self.rejected(sdd.lint, root, target, contains="draft")
        self.rejected(sdd.scaffold, root, target, contains="clobber")
        self.assertEqual(before, {p.name: p.read_bytes() for p in target.glob("*.md")})

    def test_all_ears_noun_types_and_mixed_case(self):
        valid = {
            "ubiquitous": "The preview service shall return a decision.",
            "event": "When text arrives, the preview service shall return a decision.",
            "state": "While preview is active, the preview service shall return a decision.",
            "optional": "Where preview is included, the preview service shall return a decision.",
            "unwanted": "If text is empty, then the preview service shall reject the request.",
            "complex": "While preview is active, When text arrives, the preview service shall return a decision.",
        }
        for kind, text in valid.items():
            with self.subTest(kind=kind):
                sdd.ears(kind, text)
                sdd.ears(kind.upper(), text.lower())

    def test_malformed_ears_each_requirement_checked(self):
        invalid = (
            ("ubiquitous", "The shall return a decision."),
            ("event", "While preview is active, the service shall return a decision."),
            ("state", "When text arrives, the service shall return a decision."),
            ("optional", "Where , the service shall return a decision."),
            ("unwanted", "If text is empty, the service shall reject."),
            ("complex", "When text arrives, While active, the service shall respond."),
            ("event", "When text arrives, the service shall ."),
        )
        for kind, text in invalid:
            with self.subTest(text=text):
                self.rejected(sdd.ears, kind, text)
        self.replace("SPECIFICATION", "The preview service shall exclude", "The shall exclude")
        self.rejected(sdd.lint, self.root, self.target, contains="EARS")

    def test_missing_requirement_reference(self):
        self.replace("TASKS", "| REQ-1, REQ-2, REQ-3 |", "| REQ-1, REQ-2, REQ-999 |")
        self.rejected(sdd.lint, self.root, self.target, contains="unknown reference")

    def test_duplicate_ids(self):
        self.replace("SPECIFICATION", "| REQ-2 | unwanted", "| REQ-1 | unwanted")
        self.rejected(sdd.lint, self.root, self.target, contains="duplicate")

    def test_wrong_id_noun_type(self):
        self.replace("INVARIANTS", "| INV-2 |", "| OBS-2 |")
        self.rejected(sdd.lint, self.root, self.target, contains="malformed INV")

    def test_dag_cycles_and_unknown_dependencies(self):
        self.replace("TASKS", "| OBS-1 | - |", "| OBS-1 | TASK-1 |")
        self.rejected(sdd.lint, self.root, self.target, contains="cycle")
        self.replace("TASKS", "| OBS-1 | TASK-1 |", "| OBS-1 | TASK-999 |")
        self.rejected(sdd.lint, self.root, self.target, contains="unknown dependency")

    def test_valid_dependency_order(self):
        nodes = {"TASK-2": {"Depends": "TASK-1"}, "TASK-1": {"Depends": "-"},
                 "TASK-3": {"Depends": "-"}}
        self.assertEqual(sdd.dag(nodes), ["TASK-1", "TASK-2", "TASK-3"])

    def test_dependency_gate_requires_verified_markdown_completion(self):
        path = self.target / "TASKS.md"
        text = path.read_text()
        row = next(line for line in text.splitlines() if line.startswith("| TASK-1 | REQ"))
        second = row.replace("TASK-1", "TASK-2").replace("| OBS-1 | - |", "| OBS-1 | TASK-1 |")
        text = text.replace("\n\n## Execution log", "\n" + second + "\n\n## Execution log")
        text = text.replace("| TASK-1 | planned | - | - | - | - |",
                            "| TASK-1 | planned | - | - | - | - |\n| TASK-2 | planned | - | - | - | - |")
        path.write_text(text)
        approval = self.approve_fixture(task="TASK-2")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="dependencies")
        completed = self.completed_fixture()
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        self.assertEqual(sdd.gate(self.root, self.target, approval)["task"], "TASK-2")
        proof_path = self.root / "evidence" / "task-1-red.txt"
        proof_path.write_text("Altered test fixture red evidence.")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="stale analysis")

    def test_postbuild_scopes_active_task_not_future_missing_files(self):
        self.add_second_task(future_files=True)
        self.execution_fixture()
        approval = self.approve_fixture("post-build")
        self.assertEqual(sdd.gate(self.root, self.target, approval, purpose="verify")["task"], "TASK-1")
        self.assertFalse((self.root / "tests" / "test_app2.py").exists())
        self.rejected(sdd.lint, self.root, self.target, "ready", contains="missing")

    def test_completed_requires_code_tests_and_distinct_evidence(self):
        self.execution_fixture(status="completed")
        self.replace("TASKS", "| evidence/task-1-red.txt | evidence/task-1-green.txt | evidence/task-1-refactor.txt | evidence/task-1-verified.txt |",
                     "| evidence/review.txt | evidence/review.txt | evidence/review.txt | evidence/review.txt |")
        self.rejected(sdd.lint, self.root, self.target, "tasks", contains="four distinct")
        self.execution_fixture(status="completed")
        (self.root / "app.py").unlink()
        self.rejected(sdd.lint, self.root, self.target, "tasks", contains="missing regular file")

    def test_completed_map_matching_hash_and_postbuild_proof(self):
        self.add_second_task()
        completed = self.completed_fixture()
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        original = json.loads(approval.read_text())
        cases = []
        missing = json.loads(json.dumps(original))
        missing["completed"] = {}
        cases.append((missing, "does not match TASKS"))
        changed_hash = json.loads(json.dumps(original))
        changed_hash["completed"]["TASK-1"]["sha256"] = "0" * 64
        cases.append((changed_hash, "completed evidence changed"))
        wrong_path = json.loads(json.dumps(original))
        path = self.root / "evidence" / "same-bytes.txt"
        path.write_bytes((self.root / completed["TASK-1"]["path"]).read_bytes())
        wrong_path["completed"]["TASK-1"]["path"] = path.relative_to(self.root).as_posix()
        cases.append((wrong_path, "does not match TASKS execution log"))
        wrong_phase = json.loads(json.dumps(original))
        wrong_phase["completed"]["TASK-1"]["analysis"] = original["analysis"]
        wrong_phase["completed"]["TASK-1"]["analysis_hash"] = original["analysis_hash"]
        cases.append((wrong_phase, "own post-build review"))
        for data, message in cases:
            with self.subTest(message=message):
                approval.write_text(json.dumps(data))
                self.rejected(sdd.gate, self.root, self.target, approval, contains=message)
        approval.write_text(json.dumps(original))

    def receipt_fixture(self):
        self.add_second_task()
        return self.completed_fixture()

    def test_receipt_outside_feature_reviews_is_rejected(self):
        completed = self.receipt_fixture()
        item = completed["TASK-1"]
        copied = self.root / "evidence" / Path(item["analysis"]).name
        shutil.copyfile(self.root / item["analysis"], copied)
        item["analysis"] = copied.relative_to(self.root).as_posix()
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="selected feature reviews")

    def test_receipt_analysis_hash_mismatch_is_rejected(self):
        completed = self.receipt_fixture()
        completed["TASK-1"]["analysis_hash"] = "0" * 64
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="analysis hash changed")

    def test_receipt_tampered_content_with_refreshed_hash_is_rejected(self):
        completed = self.receipt_fixture()
        path = self.root / completed["TASK-1"]["analysis"]
        record = json.loads(path.read_text())
        record["review"]["summary"] += " Altered immutable receipt."
        path.write_text(json.dumps(record))
        completed["TASK-1"]["analysis_hash"] = sdd.file_digest(path)
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="content/address")

    def test_receipt_authoritative_spec_change_after_review_is_rejected(self):
        completed = self.receipt_fixture()
        self.replace("DESIGN", "Implement preview as a plain function", "Implement preview as a single plain function")
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="authoritative specs changed")

    def test_receipt_predecessor_code_change_with_fresh_current_analysis_is_rejected(self):
        completed = self.receipt_fixture()
        path = self.root / "app.py"
        path.write_text(path.read_text() + "\n# Changed after predecessor review.\n")
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="code/test differs")

    def test_receipt_execution_evidence_change_with_fresh_analysis_is_rejected(self):
        completed = self.receipt_fixture()
        (self.root / "evidence" / "task-1-red.txt").write_text("Changed predecessor red evidence.")
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="execution evidence differs")

    def test_receipt_missing_cross_analysis_heading_is_rejected(self):
        completed = self.receipt_fixture()
        record = json.loads((self.root / completed["TASK-1"]["analysis"]).read_text())
        log = self.target / "CROSS_ANALYSIS.md"
        log.write_text(log.read_text().replace(f"## Review {record['id']}", "## Removed predecessor review"))
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="predecessor CROSS_ANALYSIS")

    def test_already_completed_task_cannot_be_reauthorized(self):
        completed = self.receipt_fixture()
        approval = self.approve_fixture(completed=completed, task="TASK-1")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="valid pending task")

    def test_postbuild_future_owned_files_in_scope_are_rejected(self):
        self.add_second_task(future_files=True)
        self.execution_fixture()
        (self.root / "app2.py").write_text("# Future implementation is not active.\n")
        (self.root / "tests" / "test_app2.py").write_text("def test_future():\n    pass\n")
        review = self.root / "review.example.json"
        data = json.loads(review.read_text())
        data["phase"], data["task"] = "post-build", "TASK-1"
        data["scope_files"] += ["app2.py", "tests/test_app2.py"]
        review.write_text(json.dumps(data))
        self.rejected(sdd.analyze, self.root, self.target, review, contains="unstarted future task")

    def test_inprogress_same_red_green_refactor_evidence_is_rejected(self):
        self.execution_fixture()
        self.replace("TASKS", "evidence/task-1-green.txt | evidence/task-1-refactor.txt",
                     "evidence/task-1-red.txt | evidence/task-1-red.txt")
        review = self.root / "review.example.json"
        data = json.loads(review.read_text())
        data["phase"], data["task"] = "post-build", "TASK-1"
        review.write_text(json.dumps(data))
        self.rejected(sdd.analyze, self.root, self.target, review, contains="distinct red/green/refactor")

    def test_receipt_binds_task_definition_not_only_execution_log(self):
        completed = self.receipt_fixture()
        self.replace("TASKS", "| python3 -m unittest discover -s tests -v |",
                     "| python3 -m unittest discover -s tests -q |")
        approval = self.approve_fixture(completed=completed, task="TASK-2")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="task definition changed")

    def test_task_must_include_invariant_and_observation_tests(self):
        self.replace("TASKS", "tests/test_app.py#test_reject, ", "")
        self.rejected(sdd.lint, self.root, self.target, "tasks", contains="tests missing from task")

    def test_task_owned_files_must_include_test_paths(self):
        self.replace("TASKS", "| app.py, tests/test_app.py |", "| app.py |")
        self.rejected(sdd.lint, self.root, self.target, "tasks", contains="Files must include")

    def test_duplicate_ac_id_is_rejected(self):
        self.replace("SPECIFICATION", "### AC-2:", "### AC-1:")
        self.rejected(sdd.lint, self.root, self.target, "spec", contains="duplicate acceptance ID")

    def test_duplicate_list_items_are_rejected(self):
        self.replace("TASKS", "tests/test_app.py#test_accept, ", "tests/test_app.py#test_accept, tests/test_app.py#test_accept, ")
        self.rejected(sdd.lint, self.root, self.target, "tasks", contains="invalid list")

    def test_unknown_execution_status_is_rejected(self):
        self.replace("TASKS", "| TASK-1 | planned |", "| TASK-1 | waved-through |")
        self.rejected(sdd.lint, self.root, self.target, "tasks", contains="unknown execution status")

    def test_sparse_done_condition_is_rejected(self):
        self.replace("TASKS", "Exact outcomes and safe field allowlist verified by assertions and human review.", "OK")
        self.rejected(sdd.lint, self.root, self.target, "tasks", contains="sparse completion")

    def test_sensitive_field_aliases_and_empty_exclusion_are_rejected(self):
        path = self.target / "OBSERVABILITY.md"
        baseline = path.read_text()
        for field in ("useremail", "authorization", "api_key", "apikey", "passwd", "pwd",
                      "credential", "session", "card", "address", "dob", "message_text"):
            with self.subTest(field=field):
                path.write_text(baseline.replace("event,outcome,correlation_id", f"event,outcome,correlation_id,{field}"))
                self.rejected(sdd.lint, self.root, self.target, "tasks", contains="sensitive telemetry")
        path.write_text(baseline.replace("exclude=message,password,secret,token", "exclude=none"))
        self.rejected(sdd.lint, self.root, self.target, "tasks", contains="exact allowlist")

    def test_none_question_escape_is_rejected(self):
        path = self.target / "SPECIFICATION.md"
        text = path.read_text()
        path.write_text(text.replace(sdd.section(text, "Open questions"), "None: but should another path be supported? owner undecided."))
        self.rejected(sdd.lint, self.root, self.target, "plan", contains="unresolved question text")

    def test_nested_python_function_is_not_a_test_declaration(self):
        path = self.root / "tests" / "test_app.py"
        path.write_text("def helper():\n    def test_accept():\n        pass\n")
        self.rejected(sdd.lint, self.root, self.target, contains="declaration not found")

    def test_behavior_queue_table_column_class_not_implementation_by_themselves(self):
        path = self.target / "SPECIFICATION.md"
        text = path.read_text()
        for phrase in ("joins the waiting queue", "displays a table", "selects a column", "shows a class name"):
            with self.subTest(phrase=phrase):
                path.write_text(text.replace("return an accepted outcome", phrase))
                sdd.lint(self.root, self.target, "spec")
        for phrase in ("persist a record in Postgres", "send a record via gRPC"):
            with self.subTest(phrase=phrase):
                path.write_text(text.replace("return an accepted outcome", phrase))
                self.rejected(sdd.lint, self.root, self.target, "spec", contains="implementation detail")

    def test_lint_rejects_completed_task_skipping_dependency(self):
        self.add_second_task()
        self.execution_fixture("TASK-2", "completed")
        self.rejected(sdd.lint, self.root, self.target, "tasks", contains="completed dependency")

    def test_unsafe_feature_ids(self):
        for feature in ("", "../escape", "/tmp/escape", "a/b", "a\\b", "A", "-a", "a--b", "a" * 65):
            with self.subTest(feature=feature):
                self.rejected(sdd.resolve, self.root, feature)

    def test_symlink_root_and_scaffold_target(self):
        alias = self.temp_root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        self.rejected(sdd.resolve, alias, contains="symlink")
        blank = self.temp_root / "blank"
        blank.mkdir()
        (blank / ".specs").symlink_to(self.target, target_is_directory=True)
        self.rejected(sdd.resolve, blank, contains="symlink")

    def test_symlink_mapped_document_or_test(self):
        path = self.target / "DESIGN.md"
        saved = self.root / "real-design.md"
        path.rename(saved)
        path.symlink_to(saved)
        self.rejected(sdd.lint, self.root, self.target, contains="symlink")

    def test_sparse_empty_incomplete_docs(self):
        for contents in ("", "# Mission\n", "# Mission\n## Problem\nN/A\n"):
            with self.subTest(contents=contents):
                path = self.target / "MISSION.md"
                original = path.read_text()
                path.write_text(contents)
                self.rejected(sdd.lint, self.root, self.target)
                path.write_text(original)
        self.replace("MISSION", "A local preview operation", "FILL_ME")
        self.rejected(sdd.lint, self.root, self.target, contains="draft")

    def test_unresolved_questions(self):
        self.replace("SPECIFICATION", "None: demonstration", "- [ ] Q1: unresolved\nNone: demonstration")
        self.rejected(sdd.lint, self.root, self.target, contains="unresolved")

    def test_each_ac_requires_gwt(self):
        self.replace("SPECIFICATION", "Then the outcome is rejected", "Outcome is rejected")
        self.rejected(sdd.lint, self.root, self.target, contains="Given/When/Then")

    def test_best_effort_behavior_implementation_leak(self):
        self.replace("SPECIFICATION", "A caller submits a message", "Use PostgreSQL database schema. A caller submits a message")
        self.rejected(sdd.lint, self.root, self.target, contains="implementation detail")

    def test_missing_tests_marker_and_prebuild_no_deadlock(self):
        path = self.root / "tests" / "test_app.py"
        path.rename(path.with_suffix(".saved"))
        sdd.lint(self.root, self.target, "tasks")
        self.rejected(sdd.lint, self.root, self.target, contains="missing regular file")
        approval = self.approve_fixture()
        self.assertEqual(sdd.gate(self.root, self.target, approval)["task"], "TASK-1")
        path.write_text("# test_accept test_reject test_safe_event")
        self.rejected(sdd.lint, self.root, self.target, contains="declaration not found")

    def test_explicit_observation_optout(self):
        path = self.target / "OBSERVABILITY.md"
        text = path.read_text()
        body = sdd.section(text, "Observations")
        path.write_text(text.replace(body, "N/A: local design has no runtime event requirement for this opt-out variant."))
        self.replace("TASKS", "| OBS-1 | - |", "| - | - |")
        sdd.lint(self.root, self.target)

    def test_unsafe_telemetry_and_trace_mismatch(self):
        self.replace("OBSERVABILITY", "allowlist=event,outcome,correlation_id; exclude=message,password,secret,token", "raw message permitted")
        self.rejected(sdd.lint, self.root, self.target, contains="telemetry")
        self.replace("OBSERVABILITY", "raw message permitted", "allowlist=event,outcome,correlation_id; exclude=message,password,secret,token")
        self.replace("OBSERVABILITY", "| REQ-1, REQ-2, REQ-3 |", "| REQ-1, REQ-2 |")
        self.rejected(sdd.lint, self.root, self.target, contains="mismatch")

    def test_telemetry_allowlist_exact_fields_sensitive_and_negated_policy(self):
        baseline = (self.target / "OBSERVABILITY.md").read_text()
        cases = (
            ("event,outcome,correlation_id", "outcome,correlation_id", "fields required"),
            ("event,outcome,correlation_id", "event,outcome,correlation_id,password", "sensitive"),
            ("allowlist=event,outcome,correlation_id; exclude=message,password,secret,token",
             "no allowlist; never redact or exclude", "exact allowlist"),
        )
        for old, new, error in cases:
            with self.subTest(new=new):
                path = self.target / "OBSERVABILITY.md"
                path.write_text(baseline.replace(old, new))
                self.rejected(sdd.lint, self.root, self.target, contains=error)
                path.write_text(baseline)
        self.replace("OBSERVABILITY", "allowlist=event,outcome,correlation_id;",
                     "allowlist=event,outcome,correlation_id,extra;")
        self.rejected(sdd.lint, self.root, self.target, contains="exact allowlist")

    def test_positive_negative_must_differ_and_unwanted_needs_violation(self):
        baseline = (self.target / "INVARIANTS.md").read_text()
        self.replace("INVARIANTS", "tests/test_app.py#test_reject", "tests/test_app.py#test_accept")
        self.rejected(sdd.lint, self.root, self.target, contains="must differ")
        (self.target / "INVARIANTS.md").write_text(baseline)
        text = (self.target / "INVARIANTS.md").read_text()
        (self.target / "INVARIANTS.md").write_text(text.replace(sdd.section(text, "Rules"), "N/A: no invariants were considered by this unsafe fixture."))
        self.rejected(sdd.lint, self.root, self.target, contains="attempted-violation")

    def test_acceptance_and_task_requirement_coverage(self):
        baseline = (self.target / "SPECIFICATION.md").read_text()
        path = self.target / "SPECIFICATION.md"
        text = baseline.replace(
            "### AC-3: Keep message contents private (REQ-3)\nGiven a message containing confidential text\nWhen the caller requests preview\nThen no observation field contains that text\n", "")
        path.write_text(text)
        self.rejected(sdd.lint, self.root, self.target, contains="every requirement")
        path.write_text(baseline.replace(
            "| REQ-3 | ubiquitous |", "| REQ-4 | ubiquitous | The preview service shall report its availability. |\n| REQ-3 | ubiquitous |").replace(
            "## Exclusions", "### AC-4: Availability (REQ-4)\nGiven a request\nWhen preview runs\nThen availability is reported\n\n## Exclusions"))
        self.rejected(sdd.lint, self.root, self.target, contains="cover all Requirements")

    def test_task_exit_range_and_separator_columns(self):
        self.replace("TASKS", "| . | 0 |", "| . | 256 |")
        self.rejected(sdd.lint, self.root, self.target, contains="invalid cwd or expected exit")
        self.replace("TASKS", "| . | 256 |", "| . | 0 |")
        self.replace("TASKS", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                     "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        self.rejected(sdd.lint, self.root, self.target, contains="table header")

    def test_strict_gwt_order_single_word_and_indentation(self):
        path = self.target / "SPECIFICATION.md"
        baseline = path.read_text()
        path.write_text(baseline.replace("Given a nonempty message\nWhen the caller requests preview\nThen the outcome is accepted",
                                        "  Given x\n  When y\n  Then z"))
        sdd.lint(self.root, self.target, "spec")
        path.write_text(baseline.replace("Given a nonempty message\nWhen the caller requests preview\nThen the outcome is accepted",
                                        "Then accepted\nWhen requested\nGiven text"))
        self.rejected(sdd.lint, self.root, self.target, "spec", contains="ordered")

    def test_comment_and_prefix_are_not_test_declarations(self):
        path = self.root / "tests" / "test_app.py"
        path.write_text("# def test_accept():\n# test_reject test_safe_event test_confidential_not_logged\n")
        self.rejected(sdd.lint, self.root, self.target, contains="declaration not found")
        path.write_text("def test_accept_extra():\n    pass\n")
        self.rejected(sdd.lint, self.root, self.target, contains="declaration not found")

    def test_plain_unresolved_questions_block_planning(self):
        path = self.target / "SPECIFICATION.md"
        text = path.read_text()
        path.write_text(text.replace(sdd.section(text, "Open questions"), "Should another path be supported? Unknown, owner undecided."))
        sdd.lint(self.root, self.target, "spec")
        self.rejected(sdd.lint, self.root, self.target, "plan", contains="Open questions")

    def test_how_heuristic_only_behavior_blocks(self):
        self.replace("SPECIFICATION", "Transport, persistence, UI", "No SQL reporting is in scope. Transport, persistence, UI")
        sdd.lint(self.root, self.target)
        self.replace("SPECIFICATION", "A caller submits a message", "Store a Redis key via the REST API in Python. A caller submits a message")
        self.rejected(sdd.lint, self.root, self.target, contains="implementation detail")

    def test_binary_evidence_hash_freshness_and_size_limit(self):
        binary = self.root / "evidence" / "keyboard.png"
        binary.write_bytes(b"\x89PNG\r\n\x1a\n\x00\xff")
        review = self.root / "review.example.json"
        data = json.loads(review.read_text())
        data["evidence"].append("evidence/keyboard.png")
        review.write_text(json.dumps(data))
        approval = self.approve_fixture()
        self.assertEqual(sdd.gate(self.root, self.target, approval)["task"], "TASK-1")
        binary.write_bytes(b"\x89PNG\r\n\x1a\n\xff\x00")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="stale analysis")
        with binary.open("wb") as file:
            file.truncate(20_000_001)
        self.rejected(sdd.file_digest, binary, contains="oversized")

    def test_future_dates_predating_approval_and_self_review_policy(self):
        approval = self.approve_fixture()
        data = json.loads(approval.read_text())
        data["approved_at"] = "2099-01-01T00:00:00Z"
        approval.write_text(json.dumps(data))
        self.rejected(sdd.gate, self.root, self.target, approval, contains="future")
        data["approved_at"] = "2000-01-01T00:00:00Z"
        approval.write_text(json.dumps(data))
        self.rejected(sdd.gate, self.root, self.target, approval, contains="predates")
        data["approved_at"] = datetime.now(timezone.utc).isoformat()
        data["authorizer"] = "Illustrative reviewer, not real authorization"
        approval.write_text(json.dumps(data))
        self.rejected(sdd.gate, self.root, self.target, approval, contains="self_review_policy")

    def test_review_cannot_optout_security_or_inject_headings(self):
        review = self.root / "review.example.json"
        data = json.loads(review.read_text())
        data["checks"]["security_negative"] = "N/A: skip security negative path review in this unsafe fixture."
        review.write_text(json.dumps(data))
        self.rejected(sdd.analyze, self.root, self.target, review, contains="cannot opt out")
        data["checks"]["security_negative"] = "Denied-path assertions are planned and not yet run."
        data["reviewer"] = "Name\n## Review deadbeef"
        review.write_text(json.dumps(data))
        self.rejected(sdd.analyze, self.root, self.target, review, contains="single-line")
        data["reviewer"] = "Illustrative reviewer"
        data["summary"] += "\n## Review deadbeef"
        review.write_text(json.dumps(data))
        sdd.analyze(self.root, self.target, review)
        log = (self.target / "CROSS_ANALYSIS.md").read_text()
        self.assertIn("> ## Review deadbeef", log)
        self.assertNotIn("\n## Review deadbeef", log)

    def test_hardlinked_documents_rejected(self):
        path = self.root / "hardlinked.txt"
        path.hardlink_to(self.root / "evidence" / "review.txt")
        self.rejected(sdd.file_digest, path, contains="hardlinked")

    def test_missing_evidence(self):
        path = self.root / "review.example.json"
        data = json.loads(path.read_text())
        data["evidence"] = ["evidence/missing.txt"]
        path.write_text(json.dumps(data))
        self.rejected(sdd.analyze, self.root, self.target, path, contains="missing")

    def test_no_approval_and_invalid_authority(self):
        self.rejected(sdd.gate, self.root, self.target, self.root / "missing.json", contains="missing")
        approval = self.approve_fixture()
        data = json.loads(approval.read_text())
        data["authority"] = "agent"
        approval.write_text(json.dumps(data))
        self.rejected(sdd.gate, self.root, self.target, approval, contains="human")

    def test_approved_fixture_is_valid_and_analysis_append_only(self):
        approval = self.approve_fixture()
        self.assertEqual(sdd.gate(self.root, self.target, approval)["task"], "TASK-1")
        log = (self.target / "CROSS_ANALYSIS.md").read_text()
        self.assertIn("Demonstration scope", log)
        self.assertIn("## Review ", log)
        review = self.root / "review.example.json"
        self.rejected(sdd.analyze, self.root, self.target, review, contains="not overwritten")
        self.assertEqual((self.target / "CROSS_ANALYSIS.md").read_text(), log)

    def test_stale_spec_analysis_and_approval(self):
        approval = self.approve_fixture()
        self.replace("MISSION", "message preview", "local message preview")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="stale analysis")

    def test_exact_bytes_freshness_and_task_scope(self):
        approval = self.approve_fixture()
        path = self.root / "app.py"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.rejected(sdd.gate, self.root, self.target, approval, contains="stale analysis")
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        data = json.loads(approval.read_text())
        data.pop("task")
        approval.write_text(json.dumps(data))
        self.rejected(sdd.gate, self.root, self.target, approval, contains="explicit task")
        data["task"] = "TASK-1"
        approval.write_text(json.dumps(data))
        self.rejected(sdd.gate, self.root, self.target, approval, "TASK-2", contains="human-authorized")

    def test_stale_reviewed_code_and_test(self):
        for raw in ("app.py", "tests/test_app.py", "evidence/review.txt"):
            with self.subTest(path=raw):
                approval = self.approve_fixture()
                path = self.root / raw
                original = path.read_text()
                path.write_text(original + "\n# changed\n")
                self.rejected(sdd.gate, self.root, self.target, approval, contains="stale analysis")
                path.write_text(original)
                # Different review timestamp makes the next immutable record unique.
                review = self.root / "review.example.json"
                data = json.loads(review.read_text())
                data["reviewed_at"] = data["reviewed_at"].replace("00:00:", "00:01:") if "00:00:" in data["reviewed_at"] else "2026-10-04T00:02:00Z"
                review.write_text(json.dumps(data))

    def test_expected_missing_code_becomes_stale(self):
        (self.root / "app.py").rename(self.root / "app.saved")
        approval = self.approve_fixture()
        (self.root / "app.py").write_text("# new code")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="stale analysis")

    def test_approval_hash_and_analysis_tamper(self):
        approval = self.approve_fixture()
        data = json.loads(approval.read_text())
        data["snapshot"] = "0" * 64
        approval.write_text(json.dumps(data))
        self.rejected(sdd.gate, self.root, self.target, approval, contains="approval hash")
        data["snapshot"] = sdd.snapshot(self.root, self.target)["hash"]
        approval.write_text(json.dumps(data))
        analysis = self.root / data["analysis"]
        record = json.loads(analysis.read_text())
        record["review"]["summary"] += " tampered"
        analysis.write_text(json.dumps(record))
        self.rejected(sdd.gate, self.root, self.target, approval, contains="content/address")

    def test_cross_analysis_change_requires_new_approval(self):
        approval = self.approve_fixture()
        path = self.target / "CROSS_ANALYSIS.md"
        path.write_text(path.read_text() + "\nNew contradiction awaiting review.\n")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="CROSS_ANALYSIS changed")

    def test_scope_cannot_omit_owned_test_or_code(self):
        path = self.root / "review.example.json"
        data = json.loads(path.read_text())
        data["scope_files"] = ["app.py"]
        path.write_text(json.dumps(data))
        self.rejected(sdd.analyze, self.root, self.target, path, contains="every task-owned")

    def test_postbuild_ready_requires_files_and_correct_gate_purpose(self):
        review = self.root / "review.example.json"
        data = json.loads(review.read_text())
        data["phase"], data["task"] = "post-build", "TASK-1"
        review.write_text(json.dumps(data))
        self.rejected(sdd.analyze, self.root, self.target, review, contains="execution evidence")
        self.execution_fixture()
        approval = self.approve_fixture("post-build")
        self.rejected(sdd.gate, self.root, self.target, approval, contains="pre-build")
        self.assertEqual(sdd.gate(self.root, self.target, approval, purpose="verify")["status"], "structurally_reviewed")

    def test_incomplete_manual_review_and_blockers(self):
        path = self.root / "review.example.json"
        data = json.loads(path.read_text())
        data["checks"]["security_negative"] = "pass"
        path.write_text(json.dumps(data))
        self.rejected(sdd.analyze, self.root, self.target, path, contains="human assessment")
        data["checks"]["security_negative"] = "Denied path assessment records planned coverage."
        data["blockers"] = ["Material contract contradiction"]
        path.write_text(json.dumps(data))
        self.rejected(sdd.analyze, self.root, self.target, path, contains="blockers")

    def test_mapping_existing_documents_no_duplication(self):
        design = self.target / "DESIGN.md"
        content = design.read_text()
        external = self.root / "TRD.md"
        external.write_text("# Existing TRD\n\n# Feature design\n\n" + content.replace("# Message preview design\n", ""))
        rows = []
        for key in sdd.ARTIFACTS:
            location = "TRD.md#Feature design" if key == "DESIGN" else f".specs/{key}.md"
            rows.append(f"| {key} | {location} |")
        (self.target / "INDEX.md").write_text(
            "# Index\n\n## Artifacts\n| Artifact | Location |\n| --- | --- |\n" + "\n".join(rows))
        design.unlink()
        sdd.lint(self.root, self.target)
        self.assertIn("TRD.md", sdd.snapshot(self.root, self.target)["files"])

    def test_feature_scaffold_shared_globals_and_module_dag(self):
        blank = self.temp_root / "multi"
        blank.mkdir()
        root, first = sdd.resolve(blank, "preview")
        sdd.scaffold(root, first, "preview")
        global_path = root / ".specs" / "CONSTITUTION.md"
        before = global_path.read_bytes()
        _, second = sdd.resolve(blank, "delivery")
        sdd.scaffold(root, second, "delivery")
        self.assertEqual(before, global_path.read_bytes())
        self.assertFalse((second / "CONSTITUTION.md").exists())
        self.assertIn(".specs/CONSTITUTION.md", (second / "INDEX.md").read_text())

    def test_multi_feature_module_cycle_blocks_spec_stage(self):
        feature = self.target / "features" / "preview"
        feature.mkdir(parents=True)
        for name in sdd.LOCALS:
            shutil.copyfile(self.target / f"{name}.md", feature / f"{name}.md")
        contract = self.root / "contracts" / "preview.md"
        contract.parent.mkdir()
        contract.write_text("# Preview contract\nCaller owns text input.")
        cap = self.target / "CAPABILITY_MAP.md"
        cap.write_text(
            "# Map\n## Modules\n| ID | Depends | Owner | Contract | Feature |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| MOD-PREVIEW | - | preview team | contracts/preview.md | preview |\n"
            "| MOD-NEXT | MOD-PREVIEW | next team | contracts/preview.md | next |\n")
        sdd.lint(self.root, feature, "spec")
        cap.write_text(cap.read_text().replace("| MOD-PREVIEW | - |", "| MOD-PREVIEW | MOD-NEXT |"))
        self.rejected(sdd.lint, self.root, feature, "spec", contains="cycle")

    def test_specs_commands_never_executed(self):
        self.replace("TECH_STACK", "Command is python3", "Dangerous command text: touch NEVER_RUN. Command is python3")
        with patch("subprocess.run", side_effect=AssertionError("checker must not execute commands")):
            sdd.lint(self.root, self.target)
            sdd.snapshot(self.root, self.target)
        self.assertFalse((self.root / "NEVER_RUN").exists())

    def test_duplicate_json_keys_and_cli_exit_contract(self):
        path = self.root / "duplicate.json"
        path.write_text('{"authority":"human","authority":"agent"}')
        self.rejected(sdd.json_file, path, contains="duplicate JSON key")
        run = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), "lint"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.replace("SPECIFICATION", "When a caller submits", "While a caller submits")
        run = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), "lint"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stderr)["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
