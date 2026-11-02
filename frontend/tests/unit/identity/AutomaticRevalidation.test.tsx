/** Rechecking a tab must never create a chain of interactive data reloads that keeps idle sessions alive. */
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { AccountAdministration } from "../../../src/components/identity/AccountAdministration";
import { identityApi } from "../../../src/lib/api/identity";
import { useSession } from "../../../src/components/identity/SessionProvider";
import { AdministrationHistory } from "../../../src/components/identity/AdministrationHistory";

vi.mock("../../../src/lib/api/identity", () => ({ identityApi: { list: vi.fn(), history: vi.fn() } }));
vi.mock("../../../src/components/identity/SessionProvider", () => ({
  useSession: vi.fn(), SessionGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
afterEach(cleanup);

test("activation reload is background and a person filter change is interactive", async () => {
  /** Exercise actual panel effects/client classification; authentication itself is covered by real API/browser tests. */
  const context = { status: "authenticated", session: { account: { id: "synthetic" }, permissions: ["identity.accounts.read"] } } as ReturnType<typeof useSession>;
  vi.mocked(useSession).mockReturnValue(context);
  vi.mocked(identityApi.list).mockResolvedValue({ items: [], next_cursor: null });
  const view = render(<AccountAdministration />);
  await waitFor(() => expect(identityApi.list).toHaveBeenLastCalledWith({ role: "", status: "", cursor: undefined }, "interactive"));
  vi.mocked(useSession).mockReturnValue({ ...context, status: "loading", session: null });
  view.rerender(<AccountAdministration />);
  vi.mocked(useSession).mockReturnValue(context);
  view.rerender(<AccountAdministration />);
  await waitFor(() => expect(identityApi.list).toHaveBeenLastCalledWith({ role: "", status: "", cursor: undefined }, "background"));
  fireEvent.change(screen.getByRole("combobox", { name: "Filtrar perfil" }), { target: { value: "operador" } });
  await waitFor(() => expect(identityApi.list).toHaveBeenLastCalledWith({ role: "operador", status: "", cursor: undefined }, "interactive"));
});

test("history revalidation is background and explicit Consultar is interactive", async () => {
  /** Verify the history panel cannot extend a session merely by rechecking a restored tab. */
  const context = { status: "authenticated", session: { permissions: ["administration.history.read"] } } as ReturnType<typeof useSession>;
  vi.mocked(useSession).mockReturnValue(context);
  vi.mocked(identityApi.history).mockResolvedValue({ items: [], next_cursor: null, cutoff_at: "2026-01-01T00:00:00Z" });
  const view = render(<AdministrationHistory />);
  await waitFor(() => expect(identityApi.history).toHaveBeenLastCalledWith({}, "interactive"));
  vi.mocked(useSession).mockReturnValue({ ...context, status: "loading", session: null });
  view.rerender(<AdministrationHistory />);
  vi.mocked(useSession).mockReturnValue(context);
  view.rerender(<AdministrationHistory />);
  await waitFor(() => expect(identityApi.history).toHaveBeenLastCalledWith({}, "background"));
  fireEvent.click(screen.getByRole("button", { name: "Consultar historial" }));
  await waitFor(() => expect(identityApi.history).toHaveBeenLastCalledWith(expect.objectContaining({ result: "" }), "interactive"));
});
