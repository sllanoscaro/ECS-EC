/** Session context starts empty and cannot retain private data during revalidation or failures. */
import React from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { SessionProvider, useSession } from "../../../src/components/identity/SessionProvider";
import { sessionApi } from "../../../src/lib/api/session";

vi.mock("../../../src/lib/api/session", async (original) => ({
  ...await original<object>(), sessionApi: { read: vi.fn(), logout: vi.fn() },
}));
afterEach(cleanup);

function Probe() {
  /** Expose only context status to verify pending/error distinction. */
  return <span>{useSession().status}</span>;
}

test("a network failure stays an error rather than an authenticated empty account", async () => {
  /** Reject session lookup and check no cached identity is displayed. */
  vi.mocked(sessionApi.read).mockRejectedValue(new Error("synthetic network failure"));
  render(<SessionProvider><Probe /></SessionProvider>);
  expect(screen.getByText("loading")).toBeTruthy();
  await waitFor(() => expect(screen.getByText("error")).toBeTruthy());
});
