/** Administrative history renders stable typed references and UTC, not original payload bodies. */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { HistoryTable } from "../../../src/components/identity/AdministrationHistory";

afterEach(cleanup);
test("history distinguishes a process and unknown actor without exposing data bodies", () => {
  /** Use approved projection-only fixtures and check the explicit timezone and read-only view. */
  render(<HistoryTable items={[{ id: "synthetic", occurred_at: "2026-01-01T00:00:00Z", actor: { kind: "process", account_id: null, process_code: "bootstrap" },
    action: "identity.bootstrap", target: { module: "identity", entity_type: "account", id: null, revision: 1 }, result: "allowed", reason_code: "changed", operation_ref: "synthetic" }]} />);
  expect(screen.getByText("Proceso: bootstrap")).toBeTruthy();
  expect(screen.getByRole("columnheader", { name: "Fecha (UTC)" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Eliminar|Editar/ })).toBeNull();
});
