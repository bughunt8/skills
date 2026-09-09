import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve, join } from "node:path";

// Only served response bytes are altered in disposable browser contexts. Never
// edit app.js/styles.css in a shared checkout while the implementation worker
// owns them. The same Node Playwright assertions run clean, planted and restored.
const root = fileURLToPath(new URL("../", import.meta.url));
const evidence = resolve(process.env.WORKSPACE_EVIDENCE_DIR || join(root, "..", "..", "graph-workspace-evidence"));
mkdirSync(evidence, { recursive: true });
const files = ["app.js", "styles.css", "index.html", "data.js"];
const hashes = () => Object.fromEntries(files.map((file) => [file,
  createHash("sha256").update(readFileSync(join(root, file))).digest("hex")]));
const before = hashes(), runs = [];
const checks = [
  { defect: "hover-steals-search", grep: "SEARCH_HOVER_IMMUNITY", assertion: "SEARCH_HOVER_IMMUNITY: pointer entry" },
  { defect: "unreadable-font", grep: "VISIBLE_LABEL_CSS_PX every painted", assertion: "VISIBLE_LABEL_CSS_PX: every painted label" },
  { defect: "label-over-node", grep: "LABEL_NODE_CLEARANCE contextual", assertion: "LABEL_NODE_CLEARANCE: labels must not cover" }
];
const both = checks.map((c) => c.grep).join("|");
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
  const jsonPath = join(evidence, `defect-${name}.json`);
  const env = { ...process.env, WORKSPACE_PLANTED_DEFECT: defect,
    PLAYWRIGHT_JSON_OUTPUT_FILE: jsonPath, WORKSPACE_EVIDENCE_DIR: join(evidence, `defect-${name}-artifacts`) };
  const started = new Date().toISOString();
  const proc = spawnSync(process.execPath, [
    join(root, "node_modules", "@playwright", "test", "cli.js"), "test",
    "tests/workspace.spec.js", "--project=desktop", "--workers=2", "--retries=0",
    "--grep", grep, "--reporter=list,json"
  ], { cwd: root, env, encoding: "utf8", timeout: 180_000 });
  writeFileSync(join(evidence, `defect-${name}.log`), (proc.stdout || "") + (proc.stderr || ""));
  const report = JSON.parse(readFileSync(jsonPath, "utf8"));
  const item = { name, defect: defect || null, started, exitCode: proc.status,
    stats: report.stats, assertionErrors: allErrors(report), processError: proc.error?.message || null };
  runs.push(item);
  console.log(`${name}: exit ${proc.status}; expected ${report.stats?.expected}; unexpected ${report.stats?.unexpected}`);
  return item;
}
let failure = "";
try {
  const baseline = run("baseline", both);
  if (baseline.exitCode !== 0) throw new Error("Clean baseline failed; planted defects are not meaningful until this passes.");
  for (const check of checks) {
    if (interrupted) throw new Error(`Interrupted: ${interrupted}`);
    const planted = run(check.defect, check.grep, check.defect);
    if (planted.exitCode === 0) throw new Error(`Non-vacuity failed: ${check.defect} passed.`);
    if (!planted.assertionErrors.some((error) => error.includes(check.assertion)))
      throw new Error(`${check.defect} failed for an unrelated reason, not its acceptance assertion.`);
    console.log(`PROVED: ${check.defect} fails the matching real-input browser assertion.`);
  }
} catch (error) {
  failure = String(error);
  console.error(failure);
} finally {
  // Trap-like restoration: isolated routes died with each child browser context;
  // unset the defect for a mandatory clean rerun even after an assertion failed.
  const restored = run("restored", both);
  const after = hashes();
  const unchanged = JSON.stringify(before) === JSON.stringify(after);
  if (!unchanged) failure += "\nSource bytes changed during proof; inspect concurrent edits.";
  if (restored.exitCode !== 0) failure += "\nRestored clean run failed.";
  const proof = { mechanism: "isolated browser response mutation; source files never modified",
    before, after, sourceUnchanged: unchanged, restored: restored.exitCode === 0,
    interrupted, runs, passed: !failure && runs.length === checks.length + 2, failure };
  writeFileSync(join(evidence, "workspace-defect-proof.json"), JSON.stringify(proof, null, 2) + "\n");
  console.log(`Restoration: source unchanged=${unchanged}; clean rerun=${restored.exitCode === 0}`);
}
if (failure || interrupted) process.exitCode = 1;
