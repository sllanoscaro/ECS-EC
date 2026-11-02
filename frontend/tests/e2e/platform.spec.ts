/** Smoke-test the exported page and readiness from the same Uvicorn origin. */
import { expect, test } from "@playwright/test";

test("static web and API share the monolith", async ({ page, request }) => {
  /** Request real HTTP resources; require a healthy migrated database. */
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("ECS-EC");
  const response = await request.get("/api/v1/health/ready");
  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toEqual({ status: "ready" });
});
