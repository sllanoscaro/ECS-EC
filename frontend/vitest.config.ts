/** Component tests run in a browser-like DOM and exclude Playwright scenarios. */
import { defineConfig } from "vitest/config";
export default defineConfig({ test: { environment: "jsdom", include: ["tests/unit/**/*.test.tsx"] } });
