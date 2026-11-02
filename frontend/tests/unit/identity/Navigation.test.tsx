/** Navigation uses current runtime permissions and only explicitly registered installed modules. */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Navigation } from "../../../src/components/identity/Navigation";
import { useSession } from "../../../src/components/identity/SessionProvider";

vi.mock("../../../src/components/identity/SessionProvider", () => ({ useSession: vi.fn() }));
afterEach(cleanup);

test("an Operator receives no administrative link", () => {
  /** Supply current permissions; a role label alone does not add a link. */
  vi.mocked(useSession).mockReturnValue({ status: "authenticated", session: { permissions: ["session.read"], must_change_password: false } } as ReturnType<typeof useSession>);
  render(<Navigation links={[{ href: "/administracion/usuarios/", label: "Usuarios", permission: "identity.accounts.read" }]} />);
  expect(screen.queryByRole("link", { name: "Usuarios" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Consumo" })).toBeNull();
});
