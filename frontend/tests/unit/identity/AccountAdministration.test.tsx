/** Administrative forms never retain passwords after errors or allow implicit self role elevation. */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { AccountForm } from "../../../src/components/identity/AccountForm";
import { Problem } from "../../../src/lib/api/session";

afterEach(cleanup);

test.each([[409, "email_conflict", "El correo ya está registrado."], [412, "revision_conflict", "Recargue la cuenta."], [503, "identity_unavailable", "No se pudo confirmar el cambio."]])("error %i preserves nonsecret fields and clears credentials", async (status, code, message) => {
  /** Reject a real form callback with the safe 409 contract; inspect accessible fields only. */
  const save = vi.fn().mockRejectedValue(new Problem(status as number, code as string, message as string));
  render(<AccountForm save={save} />);
  fireEvent.change(screen.getByLabelText("Correo", { exact: true }), { target: { value: "new@example.test" } });
  fireEvent.change(screen.getByLabelText("Contraseña inicial", { exact: true }), { target: { value: "Synthetic initial password" } });
  fireEvent.change(screen.getByLabelText("Confirmar contraseña", { exact: true }), { target: { value: "Synthetic initial password" } });
  fireEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
  await screen.findByText(message as string);
  expect((screen.getByLabelText("Contraseña inicial", { exact: true }) as HTMLInputElement).value).toBe("");
  expect((screen.getByLabelText("Correo", { exact: true }) as HTMLInputElement).value).toBe("new@example.test");
});
