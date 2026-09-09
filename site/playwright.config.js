import { defineConfig, devices } from "@playwright/test";

// The site is static with no build step for the browser, so CI serves the repo
// directory as-is. That means the tests exercise exactly the bytes that ship.
const PORT = 8123;

export default defineConfig({
  testDir: "./tests",
  outputDir: process.env.WORKSPACE_EVIDENCE_DIR
    ? `${process.env.WORKSPACE_EVIDENCE_DIR}/playwright-artifacts`
    : "./test-results",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }], ["list"]]
    : [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    // Sandbox Chromium can be supplied explicitly. CI still uses the Playwright
    // browser installed for the locked Node package; no machine path is baked in.
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined
    },
    trace: "on-first-retry",
    screenshot: "only-on-failure"
  },
  webServer: {
    command: `python3 -m http.server ${PORT}`,
    url: `http://127.0.0.1:${PORT}/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { ...devices["Pixel 7"], viewport: { width: 390, height: 844 } } }
  ]
});
