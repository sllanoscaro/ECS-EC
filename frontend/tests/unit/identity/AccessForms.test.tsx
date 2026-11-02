/** Accessible login preserves passwords exactly and clears secrets after a rejected submission. */
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { LoginForm } from "../../../src/components/identity/LoginForm";
import { SessionProvider } from "../../../src/components/identity/SessionProvider";
import { Problem, sessionApi } from "../../../src/lib/api/session";

vi.mock("../../../src/lib/api/session", async (original) => ({
  ...await original<object>(), sessionApi: { read: vi.fn(), login: vi.fn() },
}));
afterEach(cleanup);

test("rejected login clears the password and displays the shared message", async () => {
  /** Exercise labels and submit through a mounted provider, without storing a credential. */
  vi.mocked(sessionApi.read).mockRejectedValue(new Problem(401, "session_required", "Debe ingresar."));
  vi.mocked(sessionApi.login).mockRejectedValue(new Problem(401, "invalid_credentials", "No fue posible ingresar con esas credenciales"));
  render(<SessionProvider><LoginForm /></SessionProvider>);
  await waitFor(() => expect(screen.getByLabelText("Correo")).toBeTruthy());
  fireEvent.change(screen.getByLabelText("Correo"), { target: { value: "person@example.test" } });
  const password = screen.getByLabelText("Contraseña") as HTMLInputElement;
  fireEvent.change(password, { target: { value: "  Exact synthetic pass  " } });
  fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));
  await screen.findByText("No fue posible ingresar con esas credenciales");
  expect(password.value).toBe("");
  expect(sessionApi.login).toHaveBeenCalledWith("person@example.test", "  Exact synthetic pass  ");
});
