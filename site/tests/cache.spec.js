import { test, expect } from "@playwright/test";
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("runtime asset URLs carry their exact content digest", () => {
  for (const name of ["styles.css", "app.js", "data.js"]) {
    const bytes = readFileSync(new URL(`../${name}`, import.meta.url));
    const digest = createHash("sha256").update(bytes).digest("hex").slice(0, 12);
    expect(html).toContain(`./${name}?v=${digest}`);
  }
});

test("returning visitor with old cached assets gets the new workspace", async ({ browser }) => {
  let phase = "old";
  const requests = [];
  const types = { ".html": "text/html", ".js": "application/javascript",
    ".css": "text/css", ".woff2": "font/woff2", ".svg": "image/svg+xml" };
  const server = createServer((req, res) => {
    const url = new URL(req.url, "http://localhost");
    requests.push({ phase, path: url.pathname, version: url.searchParams.get("v") });
    if (url.pathname === "/" && phase === "old") {
      res.writeHead(200, { "content-type": "text/html", "cache-control": "no-store" });
      res.end('<!doctype html><html><head><link rel="stylesheet" href="./styles.css"></head><body><script src="./data.js"></script><script src="./app.js"></script></body></html>');
      return;
    }
    if (phase === "old" && ["/app.js", "/data.js", "/styles.css"].includes(url.pathname)) {
      res.writeHead(200, { "content-type": types[extname(url.pathname)],
        "cache-control": "public, max-age=3600" });
      res.end(url.pathname === "/app.js" ? "window.oldCachePrimed=true;" :
        url.pathname === "/data.js" ? "window.SKILLDATA={};" : "body{font-size:7px}");
      return;
    }
    try {
      const path = resolve(root, "." + (url.pathname === "/" ? "/index.html" : url.pathname));
      if (!path.startsWith(root.endsWith(sep) ? root : root + sep)) throw new Error("path");
      const bytes = readFileSync(path);
      res.writeHead(200, { "content-type": types[extname(path)] || "text/plain",
        "cache-control": url.pathname === "/" ? "no-store" : "public, max-age=3600" });
      res.end(bytes);
    } catch { res.writeHead(404); res.end(); }
  });
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  const origin = `http://127.0.0.1:${server.address().port}/`;
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  try {
    await page.goto(origin);
    expect(await page.evaluate(() => window.oldCachePrimed)).toBe(true);
    phase = "new";
    await page.goto("about:blank");
    await page.goto(origin);
    await expect(page.locator('#top[data-ready="true"]')).toBeVisible();
    await page.locator("#gsearch").fill("NDA");
    await page.locator("#gresults button[data-key]").first().click();
    expect(await page.locator("#top").getAttribute("data-selected-key")).toBeTruthy();
    expect(await page.evaluate(() => window.oldCachePrimed)).toBeUndefined();
    for (const name of ["styles.css", "app.js", "data.js"]) {
      expect(requests.some((r) => r.phase === "new" && r.path === `/${name}` && r.version)).toBe(true);
    }
  } finally {
    await context.close();
    server.closeAllConnections();
    await new Promise((done) => server.close(done));
  }
});
