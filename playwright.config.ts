import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

/** Dedicated test bind — never 8765, so a leftover operator Yoklama is never the target. */
const port = Number(process.env.YOKLAMA_PW_PORT || 18765);
const baseURL = `http://127.0.0.1:${port}`;
const projectRoot = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: "./webui/specs",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["json", { outputFile: "test-results/playwright-report.json" }]],
  use: {
    baseURL,
    headless: true,
    locale: "tr-TR",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    permissions: ["clipboard-read", "clipboard-write"],
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    command: `node webui/helpers/isolated-app.mjs --port ${port}`,
    cwd: projectRoot,
    url: `${baseURL}/api/meta`,
    reuseExistingServer: false,
    timeout: 30_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
