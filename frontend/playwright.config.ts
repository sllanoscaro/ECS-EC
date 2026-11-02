/** Browser tests use the real local monolith; transport origin is explicitly configurable. */
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8000" },
});
