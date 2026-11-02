/** Browser tests use the real local monolith; transport origin is explicitly configurable. */
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  // Identity scenarios require an explicit protected fixture; base CI never invents credentials.
  testMatch: process.env.IDENTITY_E2E_PASSWORD_FILE ? "**/*.spec.ts" : "platform.spec.ts",
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8000", ignoreHTTPSErrors: Boolean(process.env.IDENTITY_E2E_CLOCK_FILE) },
});
