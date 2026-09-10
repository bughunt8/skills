#!/usr/bin/env node
// Runner-local proof of the real smoke command. No public requests or uploads.
// Only the in-memory BUILD-INFO response changes. Site files stay untouched.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createServer } from "node:http";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const expectedSha = "0123456789abcdef0123456789abcdef01234567";
const wrongSha = "89abcdef0123456789abcdef0123456789abcdef";
const marker = (sha) => `local-deploy-gate-fixture\ncommit: ${sha}\n`;
const timeoutMs = 5 * 60 * 1000;
const protectedFiles = [
  "scripts/smoke.mjs", "scripts/prove-deploy-gate.mjs",
  "index.html", "app.js", "data.js", "styles.css", ".htaccess",
  "build.py", "network.py", "compose.py", "sources.json", "favicon.svg",
  "fonts/fonts.css", "fonts/inter-latin.woff2", "fonts/space-grotesk-latin.woff2"
];
const hashFiles = () => Object.fromEntries(protectedFiles.map((file) => [
  file, createHash("sha256").update(readFileSync(resolve(root, file))).digest("hex")
]));
const before = hashFiles();
const types = {
  ".html": "text/html; charset=utf-8", ".js": "application/javascript",
  ".css": "text/css", ".svg": "image/svg+xml", ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8", ".json": "application/json"
};
let buildInfo = marker(expectedSha);
let requests = [];
let activeChild;
const cases = [];
const server = createServer((req, res) => {
  res.on("finish", () => requests.push({ path: req.url, status: res.statusCode }));
  try {
    if (req.method !== "GET") {
      res.writeHead(405).end("GET only");
      return;
    }
    const pathname = decodeURIComponent(new URL(req.url, "http://127.0.0.1").pathname);
    if (pathname === "/BUILD-INFO.txt") {
      res.writeHead(buildInfo === null ? 404 : 200, {
        "content-type": types[".txt"], "cache-control": "no-store"
      }).end(buildInfo ?? "Not found");
      return;
    }
    const file = resolve(root, "." + (pathname === "/" ? "/index.html" : pathname));
    if (!file.startsWith(resolve(root) + sep)) {
      res.writeHead(403).end("Forbidden");
      return;
    }
    const body = readFileSync(file);
    res.writeHead(200, {
      "content-type": types[extname(file)] || "application/octet-stream",
      "cache-control": "no-store", "x-content-type-options": "nosniff",
      "referrer-policy": "strict-origin-when-cross-origin"
    }).end(body);
  } catch {
    res.writeHead(404).end("Not found");
  }
});

function killChild(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  // Kill the whole group on CI, including any Chromium started by smoke.mjs.
  if (process.platform !== "win32") process.kill(-child.pid, "SIGKILL");
  else child.kill("SIGKILL");
}

async function runSmoke(origin) {
  let stdout = "";
  let stderr = "";
  let timedOut = false;
  const child = spawn(process.execPath, ["scripts/smoke.mjs", origin, expectedSha], {
    cwd: root,
    env: process.env,
    detached: process.platform !== "win32",
    stdio: ["ignore", "pipe", "pipe"]
  });
  activeChild = child;
  child.stdout.on("data", (chunk) => { stdout += chunk; process.stdout.write(chunk); });
  child.stderr.on("data", (chunk) => { stderr += chunk; process.stderr.write(chunk); });
  const timer = setTimeout(() => {
    timedOut = true;
    console.error(`Deploy gate case exceeded ${timeoutMs}ms; terminating smoke and browser`);
    killChild(child);
  }, timeoutMs);
  try {
    const result = await new Promise((done, reject) => {
      child.once("error", reject);
      child.once("close", (code, signal) => done({ code, signal }));
    });
    return { ...result, timedOut, stdout, stderr };
  } finally {
    clearTimeout(timer);
    activeChild = undefined;
  }
}

async function proveCase(origin, name, response, diagnostic = null) {
  buildInfo = response;
  requests = [];
  console.log(`\n=== Deploy gate proof: ${name} ===`);
  const result = await runSmoke(origin);
  const evidence = {
    name, expectedExit: diagnostic ? 1 : 0, exitCode: result.code,
    signal: result.signal, timedOut: result.timedOut, diagnostic, requests
  };
  cases.push(evidence);
  console.log(`DEPLOY_GATE_CASE ${JSON.stringify(evidence)}`);
  assert.equal(result.timedOut, false, `${name}: smoke exceeded the case timeout`);
  assert.equal(result.signal, null, `${name}: smoke was killed by a signal`);
  assert.equal(result.code, evidence.expectedExit, `${name}: unexpected smoke exit`);
  assert.deepEqual(requests.filter((request) => request.path === "/BUILD-INFO.txt"), [
    { path: "/BUILD-INFO.txt", status: response === null ? 404 : 200 }
  ], `${name}: smoke must fetch the marker once`);
  assert.deepEqual(requests.filter((request) =>
    request.status !== 200 && !(response === null && request.path === "/BUILD-INFO.txt")
  ), [], `${name}: an unrelated local resource failed`);

  if (diagnostic) {
    // Match the entire report, not just a substring or a nonzero exit. A browser
    // launch failure, network error, or second finding cannot satisfy this proof.
    assert.equal(result.stderr,
      `\nSmoke test FAILED: 1 finding(s)\n\n  FAIL  ${diagnostic}\n\n`,
      `${name}: expected only the build-marker finding`);
    assert.ok(!result.stdout.includes("Smoke test passed:"), `${name}: false success`);
  } else {
    assert.equal(result.stderr, "", `${name}: unexpected smoke error output`);
    assert.ok(result.stdout.includes(`  ok    serving commit ${expectedSha.slice(0, 8)}\n`),
      `${name}: the expected marker was not verified`);
    assert.ok(result.stdout.includes(`Smoke test passed: ${origin} is live and correct.`),
      `${name}: smoke did not report success`);
  }
  for (const label of ["phone 390px", "desktop 1440px"]) {
    assert.ok(result.stdout.includes(`  ok    ${label}: no console or page errors\n`),
      `${name}: ${label} browser checks did not pass`);
  }
  assert.match(result.stdout, /  ok    JavaScript disabled: \d+ cards, \d+ characters of text\n/,
    `${name}: native fallback check did not pass`);
  console.log(`PROVED ${name}: exit ${result.code}${diagnostic ? ", only the expected marker failure" : ""}`);
}

let passed = false;
try {
  await new Promise((done, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", done);
  });
  const origin = `http://127.0.0.1:${server.address().port}/`;
  console.log(`Local fixture only: ${origin}`);
  console.log(`Smoke source SHA-256: ${before["scripts/smoke.mjs"]}`);
  await proveCase(origin, "correct marker", marker(expectedSha));
  await proveCase(origin, "wrong marker", marker(wrongSha),
    `served build does not match ${expectedSha.slice(0, 8)}; BUILD-INFO says:\n      ` +
    marker(wrongSha).trim().replace(/\n/g, "\n      "));
  await proveCase(origin, "missing marker", null,
    "BUILD-INFO.txt was not served, cannot confirm which commit is live");
  await proveCase(origin, "restored correct marker", marker(expectedSha));
  passed = true;
} finally {
  killChild(activeChild);
  await new Promise((done) => {
    server.close(done);
    server.closeAllConnections();
  });
  const after = hashFiles();
  const unchanged = JSON.stringify(before) === JSON.stringify(after);
  console.log(`DEPLOY_GATE_PROOF ${JSON.stringify({
    purpose: "Runner-local marker proof; no public upload or live deployment",
    expectedSha, timeoutMs, passed: passed && unchanged, cases,
    sourceHashesBefore: before, sourceHashesAfter: after, sourceFilesUnchanged: unchanged
  })}`);
  assert.deepEqual(after, before, "The proof must not change smoke or site source files");
}
