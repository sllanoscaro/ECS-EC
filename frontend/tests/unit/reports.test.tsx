/**005 static shell delegates access control to the installed006 session guard. */
import React, { type ReactNode } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import ReportsPage from "../../src/app/reportes/page";

vi.mock("../../src/components/identity/SessionProvider", () => ({
  /** Expose the required permission for this shell test;006 owns actual session tests. */
  SessionGuard: ({ permission, children }: { permission: string; children: ReactNode }) => <section aria-label={permission}>{children}</section>,
}));
afterEach(cleanup);

test("prepares a guarded route without a premature generation action", () => {
  /** No private data or active generation operation belongs to the static shell. */
  render(<ReportsPage />);
  expect(screen.getByRole("heading", { name: "Reportes PDF" })).toBeTruthy();
  expect(screen.getByRole("region", { name: "reports.generate" })).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});
