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
afterEach(() => { cleanup(); vi.clearAllMocks(); });

test("rejected login clears the password and displays the shared message", async () => {
  /** Exercise labels and submit through a mounted provider, without storing a credential. */
  vi.mocked(sessionApi.read).mockRejectedValue(new Problem(401, "session_required", "Debe ingresar."));
  vi.mocked(sessionApi.login).mockRejectedValue(new Problem(401, "invalid_credentials", "No fue posible ingresar con esas credenciales"));
  render(<SessionProvider><LoginForm /></SessionProvider>);
  await waitFor(() => expect(screen.getByLabelText("Correo electrónico")).toBeTruthy());
  fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "person@example.test" } });
  const password = screen.getByLabelText("Contraseña") as HTMLInputElement;
  fireEvent.change(password, { target: { value: "  Exact synthetic pass  " } });
  fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));
  await screen.findByText("No fue posible ingresar con esas credenciales");
  expect(password.value).toBe("");
  expect(sessionApi.login).toHaveBeenCalledWith("person@example.test", "  Exact synthetic pass  ");
});

test("rate limiting blocks another form submission until Retry-After ends", async () => {
  /** Keyboard submission cannot bypass the waiting period and secrets are cleared on rejection. */
  vi.mocked(sessionApi.read).mockRejectedValue(new Problem(401, "session_required", "Debe ingresar."));
  vi.mocked(sessionApi.login).mockRejectedValue(new Problem(429, "rate_limited", "Demasiados intentos. Espere antes de volver a ingresar.", 1));
  render(<SessionProvider><LoginForm /></SessionProvider>);
  const email = await screen.findByLabelText("Correo electrónico");
  fireEvent.change(email, { target: { value: "person@example.test" } });
  const password = screen.getByLabelText("Contraseña") as HTMLInputElement;
  fireEvent.change(password, { target: { value: "synthetic password" } });
  const button = screen.getByRole("button", { name: "Ingresar" }) as HTMLButtonElement;
  fireEvent.click(button);
  await screen.findByRole("alert");
  expect(button.disabled).toBe(true);
  expect(password.value).toBe("");
  fireEvent.submit(button.closest("form")!);
  expect(sessionApi.login).toHaveBeenCalledTimes(1);
  await waitFor(() => expect(button.disabled).toBe(false), { timeout: 2500 });
});
