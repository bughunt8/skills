#!/usr/bin/env python3
"""Deployment gate contracts and in-memory regression proofs.

Run from the repository root: python3 site/tests/test_deploy_workflows.py
Requires PyYAML and Node. The browser proof runs separately in site-validate.
These tests read workflow files but never rewrite them or contact a live site.
"""

from copy import deepcopy
from pathlib import Path
import re
import subprocess
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
STAGING = "https://mediumvioletred-coyote-692292.hostingersite.com/"
PRODUCTION = "https://skills.ronald.ng"
WORKFLOW_NAMES = (
    "site-deploy-staging", "site-deploy-production", "site-deploy",
    "site-verify", "site-validate",
)
SMOKE_COMMAND = 'node scripts/smoke.mjs "$SITE_URL" "$EXPECTED_SHA"'
TARGET_COMMAND = (
    'node site/scripts/check-deploy-target.mjs "$DEPLOY_ENVIRONMENT" "$SITE_URL"'
)
DELETE = object()


class WorkflowLoader(yaml.SafeLoader):
    """Keep GitHub's `on` key a string, without losing true/false booleans."""


WorkflowLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in values
          if tag != "tag:yaml.org,2002:bool"]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
WorkflowLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.IGNORECASE),
    list("tTfF"),
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load_workflows():
    return {
        name: yaml.load(
            (ROOT / ".github" / "workflows" / f"{name}.yml").read_text(),
            Loader=WorkflowLoader,
        )
        for name in WORKFLOW_NAMES
    }


def get_job(workflow, name, label):
    value = workflow.get("jobs", {}).get(name)
    require(isinstance(value, dict), f"{label}: missing {name} job")
    return value


def needs(job):
    value = job.get("needs", [])
    require(isinstance(value, (list, str)), "needs must be a job name or list")
    return [value] if isinstance(value, str) else value


def blocking(value, label, allow_if=False):
    require("continue-on-error" not in value, f"{label}: continue-on-error is forbidden")
    if not allow_if:
        require("if" not in value, f"{label}: conditional skips are forbidden")


def required_input(workflow, name, label):
    value = workflow.get("on", {}).get("workflow_call", {}).get("inputs", {}).get(name)
    require(isinstance(value, dict), f"{label}: missing {name} input")
    require(value.get("required") is True, f"{label}: {name} must be required")
    require(value.get("type") == "string", f"{label}: {name} must be a string")
    require("default" not in value, f"{label}: {name} must not have a default")


def find_step(job, script, label):
    found = [step for step in job.get("steps", [])
             if script in step.get("run", "")]
    require(len(found) == 1, f"{label}: must run {script} exactly once")
    return found[0]


def effective_run_setting(workflow, job, step, key, default):
    value = workflow.get("defaults", {}).get("run", {}).get(key, default)
    value = job.get("defaults", {}).get("run", {}).get(key, value)
    return step.get(key, value)


def check_command(workflow, job, step, commands, label):
    blocking(step, label)
    shell = effective_run_setting(workflow, job, step, "shell", "bash")
    require(shell in ("bash", "sh"), f"{label}: use a normal failing shell")
    directory = effective_run_setting(
        workflow, job, step, "working-directory", "."
    )
    require((directory, step.get("run", "").strip()) in commands,
            f"{label}: command must run directly without tolerated failure")


def check_env(workflow, job, step, expected, label):
    env = {**workflow.get("env", {}), **job.get("env", {}), **step.get("env", {})}
    for name, value in expected.items():
        require(env.get(name) == value, f"{label}: {name} must come from the input")


def check_contract(workflows):
    for environment, url in (("staging", STAGING), ("production", PRODUCTION)):
        workflow = workflows[f"site-deploy-{environment}"]
        caller = get_job(workflow, "deploy", environment)
        gate = get_job(workflow, "gate", environment)
        blocking(caller, f"{environment} deploy")
        blocking(gate, f"{environment} gate")
        require(gate.get("uses") == "./.github/workflows/site-validate.yml",
                f"{environment}: must call site-validate")
        require("gate" in needs(caller), f"{environment}: deploy must need gate")
        require(caller.get("uses") == "./.github/workflows/site-deploy.yml",
                f"{environment}: must call shared deploy")
        require(caller.get("with", {}).get("environment") == environment,
                f"{environment}: wrong deployment environment")
        require(caller.get("with", {}).get("url") == url,
                f"{environment}: URL must be the approved literal")

    deploy = workflows["site-deploy"]
    required_input(deploy, "url", "shared deploy")
    target = get_job(deploy, "target", "shared deploy")
    publish = get_job(deploy, "deploy", "shared deploy")
    blocking(target, "target")
    blocking(publish, "publish")
    require("target" in needs(publish), "publish must need target before uploading")
    for step in target.get("steps", []):
        blocking(step, "target step")
    target_step = find_step(target, "check-deploy-target.mjs", "target")
    check_command(deploy, target, target_step, {(".", TARGET_COMMAND)}, "target command")
    check_env(deploy, target, target_step, {
        "DEPLOY_ENVIRONMENT": "${{ inputs.environment }}",
        "SITE_URL": "${{ inputs.url }}",
    }, "target")

    verifier = get_job(deploy, "verify", "shared deploy")
    blocking(verifier, "deploy verifier")
    require("deploy" in needs(verifier), "verifier must need deploy")
    require(verifier.get("uses") == "./.github/workflows/site-verify.yml",
            "deploy verifier must call site-verify")
    require(verifier.get("with", {}).get("url") == "${{ inputs.url }}",
            "deploy verifier URL must come from inputs.url")
    require(verifier.get("with", {}).get("expected_sha") == "${{ github.sha }}",
            "deploy verifier SHA must be github.sha")

    verify = workflows["site-verify"]
    for name in ("url", "expected_sha"):
        required_input(verify, name, "site-verify")
    job = get_job(verify, "verify", "site-verify")
    blocking(job, "site-verify job")
    for step in job.get("steps", []):
        blocking(step, "site-verify step")
    smoke = find_step(job, "scripts/smoke.mjs", "site-verify")
    check_command(verify, job, smoke, {("site", SMOKE_COMMAND)}, "smoke")
    check_env(verify, job, smoke, {
        "SITE_URL": "${{ inputs.url }}",
        "EXPECTED_SHA": "${{ inputs.expected_sha }}",
    }, "smoke")

    validate = workflows["site-validate"]
    contract = get_job(validate, "deployment_contract", "site-validate")
    blocking(contract, "deployment_contract")
    for step in contract.get("steps", []):
        blocking(step, "deployment_contract step")
    for script, commands in (
        ("test_deploy_workflows.py", {
            (".", "python3 site/tests/test_deploy_workflows.py"),
            ("site", "python3 tests/test_deploy_workflows.py"),
        }),
        ("prove-deploy-gate.mjs", {
            (".", "node site/scripts/prove-deploy-gate.mjs"),
            ("site", "node scripts/prove-deploy-gate.mjs"),
        }),
    ):
        step = find_step(contract, script, "deployment_contract")
        check_command(validate, contract, step, commands, f"deployment_contract {script}")
    aggregate = get_job(validate, "gate", "site-validate")
    blocking(aggregate, "aggregate gate", allow_if=True)
    require("deployment_contract" in needs(aggregate),
            "aggregate gate must need deployment_contract")
    require(aggregate.get("if") in ("always()", "${{ always() }}"),
            "aggregate gate must run even when a required job fails")


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflows = load_workflows()

    def prove_mutation(self, label, path, value, message):
        # A broken baseline must fail, not make every negative test look useful.
        check_contract(self.workflows)
        changed = deepcopy(self.workflows)
        parent = changed
        for key in path[:-1]:
            parent = parent[key]
        if value is DELETE:
            del parent[path[-1]]
        else:
            parent[path[-1]] = value
        with self.assertRaisesRegex(AssertionError, message):
            check_contract(changed)
        self.assertEqual(self.workflows, load_workflows(), "mutation touched source files")
        print(f"PROVED workflow mutation: {label}", flush=True)

    def step_path(self, workflow, job, script):
        steps = self.workflows[workflow]["jobs"][job]["steps"]
        index = next(index for index, step in enumerate(steps)
                     if script in step.get("run", ""))
        return (workflow, "jobs", job, "steps", index)

    def test_yaml_on_and_required_booleans_keep_their_types(self):
        parsed = yaml.load(
            "on:\n  workflow_call:\n    required: true\ncontinue-on-error: false\n",
            Loader=WorkflowLoader,
        )
        self.assertIs(parsed["on"]["workflow_call"]["required"], True)
        self.assertIs(parsed["continue-on-error"], False)
        self.assertEqual(yaml.safe_load("on: true"), {True: True},
                         "custom loader must not change PyYAML's global resolver")

    def test_checked_in_workflows_obey_contract(self):
        check_contract(self.workflows)

    def test_caller_url_regressions_are_detected(self):
        for environment in ("staging", "production"):
            for label, value in (("empty URL", ""), ("out-of-scope vars", "${{ vars.SITE_URL }}"),
                                 ("wrong URL", "https://unexpected.invalid/")):
                with self.subTest(environment=environment, defect=label):
                    self.prove_mutation(
                        f"{environment} {label}",
                        (f"site-deploy-{environment}", "jobs", "deploy", "with", "url"),
                        value, "URL must be the approved literal",
                    )

    def test_required_input_regressions_are_detected(self):
        for workflow, name in (("site-deploy", "url"), ("site-verify", "url"),
                               ("site-verify", "expected_sha")):
            path = (workflow, "on", "workflow_call", "inputs", name)
            for key, value, message in (
                ("required", False, "must be required"),
                ("required", DELETE, "must be required"),
                ("default", "", "must not have a default"),
                ("type", "boolean", "must be a string"),
            ):
                with self.subTest(workflow=workflow, input=name, defect=key, value=value):
                    self.prove_mutation(f"{workflow} {name} {key}", (*path, key), value, message)
            with self.subTest(workflow=workflow, input=name, defect="missing input"):
                self.prove_mutation(f"{workflow} missing {name}", path, DELETE, f"missing {name} input")

    def test_removed_jobs_and_dependencies_are_detected(self):
        mutations = (
            ("site-deploy", "verify", "shared deploy: missing verify job"),
            ("site-deploy", "target", "shared deploy: missing target job"),
            ("site-verify", "verify", "site-verify: missing verify job"),
            ("site-validate", "deployment_contract", "missing deployment_contract job"),
        )
        for workflow, job, message in mutations:
            with self.subTest(workflow=workflow, job=job):
                self.prove_mutation(f"removed {workflow}/{job}",
                                    (workflow, "jobs", job), DELETE, message)
        for workflow, job, message in (
            ("site-deploy", "verify", "verifier must need deploy"),
            ("site-deploy", "deploy", "publish must need target"),
            ("site-deploy-staging", "deploy", "deploy must need gate"),
            ("site-deploy-production", "deploy", "deploy must need gate"),
            ("site-validate", "gate", "aggregate gate must need deployment_contract"),
        ):
            with self.subTest(workflow=workflow, dependency=job):
                self.prove_mutation(f"omitted {workflow}/{job} dependency",
                                    (workflow, "jobs", job, "needs"), [], message)

    def test_empty_skip_and_tolerated_job_failures_are_detected(self):
        for workflow, job in (
            ("site-deploy-staging", "deploy"), ("site-deploy-production", "deploy"),
            ("site-deploy", "target"), ("site-deploy", "deploy"),
            ("site-deploy", "verify"), ("site-verify", "verify"),
            ("site-validate", "deployment_contract"),
        ):
            for key, value, message in (
                ("if", "inputs.url != ''", "conditional skips are forbidden"),
                ("continue-on-error", True, "continue-on-error is forbidden"),
            ):
                with self.subTest(workflow=workflow, job=job, defect=key):
                    self.prove_mutation(f"{workflow}/{job} {key}",
                                        (workflow, "jobs", job, key), value, message)

    def test_verifier_wiring_regressions_are_detected(self):
        path = ("site-deploy", "jobs", "verify")
        for suffix, value, message in (
            (("uses",), "./.github/workflows/site-validate.yml", "must call site-verify"),
            (("with", "url"), "${{ vars.SITE_URL }}", "URL must come from inputs.url"),
            (("with", "expected_sha"), "${{ github.event.before }}", "SHA must be github.sha"),
            (("with", "expected_sha"), DELETE, "SHA must be github.sha"),
        ):
            with self.subTest(defect=suffix):
                self.prove_mutation(f"verifier {suffix}", (*path, *suffix), value, message)

    def test_smoke_command_cannot_skip_or_swallow_failure(self):
        path = self.step_path("site-verify", "verify", "scripts/smoke.mjs")
        for key, value, message in (
            ("run", SMOKE_COMMAND + " || true", "without tolerated failure"),
            ("run", "set +e\n" + SMOKE_COMMAND + "\nexit 0", "without tolerated failure"),
            ("run", f"if {SMOKE_COMMAND}; then echo ok; fi", "without tolerated failure"),
            ("run", 'node scripts/smoke.mjs "$SITE_URL"', "without tolerated failure"),
            ("run", "echo skipped", "must run scripts/smoke.mjs exactly once"),
            ("if", "inputs.url != ''", "conditional skips are forbidden"),
            ("continue-on-error", True, "continue-on-error is forbidden"),
            ("shell", "bash {0} || true", "normal failing shell"),
            ("working-directory", ".", "without tolerated failure"),
        ):
            with self.subTest(defect=key, value=value):
                self.prove_mutation(f"smoke {key}: {value}", (*path, key), value, message)
        for name in ("SITE_URL", "EXPECTED_SHA"):
            with self.subTest(env=name):
                self.prove_mutation(f"smoke {name} from vars", (*path, "env", name),
                                    "${{ vars.SITE_URL }}", f"{name} must come from the input")

    def test_validation_proofs_cannot_be_omitted_or_tolerated(self):
        for script in ("test_deploy_workflows.py", "prove-deploy-gate.mjs"):
            path = self.step_path("site-validate", "deployment_contract", script)
            original = self.workflows["site-validate"]["jobs"]["deployment_contract"]["steps"][path[-1]]
            for key, value, message in (
                ("run", "echo skipped", f"must run {re.escape(script)} exactly once"),
                ("run", original["run"] + " || true", "without tolerated failure"),
                ("if", "false", "conditional skips are forbidden"),
                ("continue-on-error", True, "continue-on-error is forbidden"),
            ):
                with self.subTest(script=script, defect=key):
                    self.prove_mutation(f"{script} {key}", (*path, key), value, message)

    def test_target_preflight_cannot_be_bypassed(self):
        path = self.step_path("site-deploy", "target", "check-deploy-target.mjs")
        for key, value, message in (
            ("run", "echo skipped", "must run check-deploy-target.mjs exactly once"),
            ("run", TARGET_COMMAND + " || true", "without tolerated failure"),
            ("if", "inputs.url != ''", "conditional skips are forbidden"),
            ("continue-on-error", True, "continue-on-error is forbidden"),
        ):
            with self.subTest(defect=key):
                self.prove_mutation(f"target preflight {key}", (*path, key), value, message)
        for name in ("DEPLOY_ENVIRONMENT", "SITE_URL"):
            with self.subTest(env=name):
                self.prove_mutation(f"target preflight {name}", (*path, "env", name),
                                    "", f"{name} must come from the input")

    def test_aggregate_cannot_skip_or_tolerate_failed_contract(self):
        for key, value, message in (
            ("if", "success()", "must run even when a required job fails"),
            ("continue-on-error", True, "continue-on-error is forbidden"),
        ):
            with self.subTest(defect=key):
                self.prove_mutation(f"aggregate gate {key}",
                                    ("site-validate", "jobs", "gate", key), value, message)

    def test_additional_jobs_do_not_overconstrain_the_contract(self):
        changed = deepcopy(self.workflows)
        changed["site-deploy"]["jobs"]["extra"] = {"runs-on": "ubuntu-latest", "steps": []}
        changed["site-deploy"]["jobs"]["verify"]["needs"] = ["deploy", "extra"]
        check_contract(changed)


class DeployTargetCliTests(unittest.TestCase):
    def run_target(self, *args):
        return subprocess.run(
            ["node", str(ROOT / "site/scripts/check-deploy-target.mjs"), *args],
            cwd=ROOT, text=True, capture_output=True, timeout=15, check=False,
        )

    def test_approved_targets_and_optional_final_slash_pass(self):
        for environment, url in (("staging", STAGING), ("production", PRODUCTION)):
            for value in (url.rstrip("/"), url.rstrip("/") + "/"):
                with self.subTest(environment=environment, url=value):
                    result = self.run_target(environment, value)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(result.stdout, f"Verified deployment target: {url.rstrip('/')}/\n")

    def test_empty_mismatched_and_unexpected_targets_fail_exactly_one(self):
        invalid = [
            ("staging", ""), ("production", ""), ("staging",),
            ("staging", PRODUCTION), ("production", STAGING),
            ("preview", STAGING), ("", STAGING),
            ("staging", "https://unexpected.invalid/"),
            ("staging", STAGING + "other-path"),
            ("staging", STAGING.replace("https:", "http:")),
            ("staging", STAGING + "?different=1"),
            ("staging", STAGING + "#fragment"),
            ("staging", STAGING + "/"),
            ("staging", " " + STAGING), ("staging", STAGING + " "),
        ]
        for args in invalid:
            with self.subTest(args=args):
                result = self.run_target(*args)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr.startswith("Invalid deployment target: "), result.stderr)
                self.assertNotIn("Verified deployment target:", result.stderr)

    def test_rejected_url_does_not_echo_credentials(self):
        userinfo_parts = (
            "fixture-user-not-a-real-credential", "fixture-pass-not-a-real-credential",
        )
        credential_url = STAGING.replace("https://", f"https://{':'.join(userinfo_parts)}@")
        result = self.run_target("staging", credential_url)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("Invalid deployment target: "))
        for part in userinfo_parts:
            self.assertNotIn(part, result.stdout + result.stderr)
        self.assertNotIn(credential_url, result.stdout + result.stderr)


class PromoteWorkflowGitTests(unittest.TestCase):
    """Git semantics the YAML contract cannot see.

    site-promote.yml checks out `staging`, so `git fetch origin staging:staging`
    aborts with "refusing to fetch into branch ... checked out" and the promotion
    never reaches its pull request. That shipped and failed in CI. The contract
    tests parse structure, so only an assertion about the commands catches it.
    """

    @staticmethod
    def promote_job():
        workflow = yaml.load(
            (ROOT / ".github" / "workflows" / "site-promote.yml").read_text(),
            Loader=WorkflowLoader,
        )
        return workflow, get_job(workflow, "promote", "site-promote.yml")

    @classmethod
    def checked_out_ref(cls, job):
        for step in job["steps"]:
            if "checkout" in str(step.get("uses", "")):
                return str((step.get("with") or {}).get("ref", "")).strip()
        raise AssertionError("site-promote.yml has no checkout step")

    @staticmethod
    def lines_starting(job, prefix):
        return [
            (step.get("name", "<unnamed>"), line.strip())
            for step in job["steps"]
            for line in str(step.get("run") or "").splitlines()
            if line.strip().startswith(prefix)
        ]

    def test_never_fetches_into_the_checked_out_branch(self):
        _, job = self.promote_job()
        branch = self.checked_out_ref(job)
        self.assertTrue(branch, "the checkout step must pin an explicit ref")
        commands = self.lines_starting(job, "git fetch")
        self.assertTrue(commands, "expected the promotion to fetch its base branch")
        for name, command in commands:
            for refspec in command.split():
                if ":" not in refspec or refspec.startswith("-"):
                    continue
                destination = refspec.rsplit(":", 1)[1]
                self.assertNotIn(
                    destination,
                    (branch, "refs/heads/" + branch),
                    "step %r fetches into the checked-out branch %r, which git refuses. "
                    "Fetch into refs/remotes/origin/* instead: %s" % (name, branch, command),
                )

    def test_revisions_are_remote_tracking_or_head(self):
        """A bare local branch name only resolves if something created that ref.

        The failing version compared main..staging after a fetch meant to create
        both local branches. With that fetch corrected, those names no longer
        resolve, so the comparisons must name origin/main and HEAD.
        """
        _, job = self.promote_job()
        branch = self.checked_out_ref(job)
        pattern = re.compile(r"\bgit (?:log|diff|rev-list|merge)\b[^\n]*")
        offenders = []
        for step in job["steps"]:
            for command in pattern.findall(str(step.get("run") or "")):
                bare = ("main.." + branch, branch + "..main")
                if any(token in command for token in bare) and "origin/" not in command:
                    offenders.append((step.get("name", "<unnamed>"), command.strip()))
        self.assertEqual(
            offenders,
            [],
            "these commands use bare branch names that do not exist locally; "
            "use origin/main and HEAD instead: %s" % (offenders,),
        )

    def test_pushes_head_to_an_explicit_ref_and_never_to_main(self):
        _, job = self.promote_job()
        branch = self.checked_out_ref(job)
        pushes = self.lines_starting(job, "git push")
        self.assertTrue(pushes, "expected the promotion to push the updated branch")
        for name, command in pushes:
            self.assertNotIn(
                "main",
                command,
                "step %r must never push to main; promotion goes through a pull "
                "request: %s" % (name, command),
            )
            self.assertIn(
                "HEAD:refs/heads/" + branch,
                command,
                "step %r should push HEAD to an explicit ref so it works when no "
                "local branch exists: %s" % (name, command),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
