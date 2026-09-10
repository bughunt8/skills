import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve, join } from "node:path";

// Non-vacuity proof for the graph motion acceptance checks. Every defect is
// planted only in a COPY of the served response bytes inside a disposable browser
// context (see scripts/motion-test-helpers.mjs); app.js, styles.css and index.html
// in the checkout are never written, because the implementation worker owns them.
// For each defect: prove the intended assertion FAILS, restore, prove it PASSES,
// then verify the source hashes are byte-identical to the start.
const root = fileURLToPath(new URL("../", import.meta.url));
const evidence = resolve(process.env.WORKSPACE_EVIDENCE_DIR || join(root, "..", "..", "motion-evidence"));
mkdirSync(evidence, { recursive: true });
const files = ["app.js", "styles.css", "index.html", "data.js", "MOTION.md", "UI_NAVIGATION.md"];
const hashes = () => Object.fromEntries(files.map((file) => [file,
  createHash("sha256").update(readFileSync(join(root, file))).digest("hex")]));
const before = hashes(), runs = [];
const checks = [
  { defect: "motion-writes-state", grep: "MOTION_POINTER_IMMUNITY",
    assertion: "MOTION_POINTER_IMMUNITY:", intent: "an animation callback writes state/selection" },
  { defect: "tween-shrinks-label", grep: "MOTION_LABEL_FLOOR",
    assertion: "MOTION_LABEL_FLOOR:", intent: "a tween shrinks a label below 16 CSS px" },
  { defect: "reduced-motion-ignored", grep: "MOTION_REDUCED_MOTION",
    assertion: "MOTION_REDUCED_MOTION:", intent: "prefers-reduced-motion is ignored" },
  { defect: "stale-tween-wins", grep: "MOTION_INTERRUPTIBLE",
    assertion: "MOTION_INTERRUPTIBLE:", intent: "a transition is not interruptible: a stale tween target wins" },
  { defect: "label-layer-hidden-in-flight", grep: "MOTION_LABEL_FLOOR",
    assertion: "the label layer must stay visible during the flight",
    intent: "the label layer is blanked for the whole flight while geometry still reports 16 CSS px" },
  { defect: "edges-vanish-in-flight", grep: "MOTION_EDGE_CONTINUITY",
    assertion: "MOTION_EDGE_CONTINUITY:",
    intent: "every edge and the in-flight stand-in path fade to nothing mid-transition" },
  { defect: "camera-interpolation-disabled", grep: "MOTION_CAMERA_TRAVEL",
    assertion: "MOTION_CAMERA_TRAVEL:",
    intent: "camera interpolation is disabled while the animation clock keeps running" }
];
const all = checks.map((check) => check.grep).join("|");
let interrupted = "";
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => { interrupted = signal; });

function allErrors(report) {
  const errors = [];
  function visit(suite) {
    for (const spec of suite.specs || []) for (const test of spec.tests || [])
      for (const result of test.results || []) for (const error of result.errors || []) errors.push(error.message || "");
    for (const child of suite.suites || []) visit(child);
  }
  for (const suite of report.suites || []) visit(suite);
  return errors;
}
function run(name, grep, defect = "") {
  const jsonPath = join(evidence, `motion-defect-${name}.json`);
  const env = { ...process.env, MOTION_PLANTED_DEFECT: defect,
    PLAYWRIGHT_JSON_OUTPUT_FILE: jsonPath, WORKSPACE_EVIDENCE_DIR: join(evidence, `motion-defect-${name}-artifacts`) };
  const started = new Date().toISOString();
  const startedAt = Date.now();
  const proc = spawnSync(process.execPath, [
    join(root, "node_modules", "@playwright", "test", "cli.js"), "test",
    "tests/graph-motion.spec.js", "--project=desktop", "--workers=1", "--retries=0",
    "--grep", grep, "--reporter=list,json"
  ], { cwd: root, env, encoding: "utf8", timeout: 900_000 });
  writeFileSync(join(evidence, `motion-defect-${name}.log`), (proc.stdout || "") + (proc.stderr || ""));
  const report = JSON.parse(readFileSync(jsonPath, "utf8"));
  const item = { name, defect: defect || null, started, durationMs: Date.now() - startedAt,
    exitCode: proc.status, stats: report.stats, assertionErrors: allErrors(report),
    processError: proc.error?.message || null };
  runs.push(item);
  console.log(`${name}: exit ${proc.status}; expected ${report.stats?.expected}; unexpected ${report.stats?.unexpected}`);
  return item;
}
let failure = "";
const proved = [];
try {
  const baseline = run("baseline", all);
  if (baseline.exitCode !== 0) throw new Error("Clean baseline failed; planted defects are not meaningful until this passes.");
  for (const check of checks) {
    if (interrupted) throw new Error(`Interrupted: ${interrupted}`);
    const planted = run(check.defect, check.grep, check.defect);
    if (planted.exitCode === 0) throw new Error(`Non-vacuity failed: ${check.defect} passed.`);
    if (!planted.assertionErrors.some((error) => error.includes(check.assertion)))
      throw new Error(`${check.defect} failed for an unrelated reason, not its acceptance assertion.`);
    // Restoration is per defect as well as at the end: the planted route only
    // ever existed in that child process's browser contexts.
    const restored = run(`${check.defect}-restored`, check.grep);
    if (restored.exitCode !== 0) throw new Error(`${check.defect} did not restore: the clean rerun failed.`);
    proved.push({ defect: check.defect, intent: check.intent, assertion: check.assertion,
      failedWithDefect: true, passedRestored: true });
    console.log(`PROVED: ${check.defect} fails ${check.assertion} and passes again once removed.`);
  }
} catch (error) {
  failure = String(error);
  console.error(failure);
} finally {
  const restored = run("restored", all);
  const after = hashes();
  const unchanged = JSON.stringify(before) === JSON.stringify(after);
  if (!unchanged) failure += "\nSource bytes changed during proof; inspect concurrent edits.";
  if (restored.exitCode !== 0) failure += "\nFinal restored clean run failed.";
  const proof = { mechanism: "isolated browser response mutation in a copy; source files never modified",
    spec: "tests/graph-motion.spec.js", contract: "site/MOTION.md",
    before, after, sourceUnchanged: unchanged, restored: restored.exitCode === 0,
    interrupted, proved, runs,
    passed: !failure && proved.length === checks.length, failure };
  writeFileSync(join(evidence, "motion-defect-proof.json"), JSON.stringify(proof, null, 2) + "\n");
  console.log(`Restoration: source unchanged=${unchanged}; clean rerun=${restored.exitCode === 0}`);
}
if (failure || interrupted) process.exitCode = 1;
