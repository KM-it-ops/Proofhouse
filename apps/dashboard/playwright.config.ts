import { defineConfig, devices } from "@playwright/test";

// The dashboard is built and served by `vite preview`, bound to 127.0.0.1 only.
// E2E_APP_DIR / E2E_PORT let e2e/check-tests-have-teeth.mjs point the same tests
// at a deliberately broken copy of the dashboard.
const port = Number(process.env.E2E_PORT ?? 4173);
const appDir = process.env.E2E_APP_DIR ?? import.meta.dirname;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    ...devices["Desktop Chrome"],
  },
  projects: [{ name: "chromium" }],
  webServer: {
    command: `npm run build && npm run preview -- --port ${port} --strictPort`,
    cwd: appDir,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
