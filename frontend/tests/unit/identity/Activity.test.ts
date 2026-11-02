/** Activity and safe navigation never grant permissions or permit external return destinations. */
import { expect, test } from "vitest";
import { safeReturn, sessionActivityHeaders } from "../../../src/lib/api/session";

test("defaults polling to background and marks explicit person actions", () => {
  /** Compare fixed headers; these indications never bypass server authorization. */
  expect(sessionActivityHeaders()).toEqual({ "X-Session-Activity": "background" });
  expect(sessionActivityHeaders("interactive")).toEqual({ "X-Session-Activity": "interactive" });
});

test("rejects external, encoded and unregistered return paths", () => {
  /** Only installed relative routes can receive a return after authentication. */
  for (const value of ["//evil.test", "https://evil.test", "/%2f%2fevil.test", "/\\evil.test", "/ingreso/", "/reports/"]) {
    expect(safeReturn(value)).toBe("/cuenta/");
  }
  expect(safeReturn("/administracion/usuarios/")).toBe("/administracion/usuarios/");
});
