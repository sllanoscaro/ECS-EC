/** Textual availability/transport states distinguish absence from a valid zero. */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { QueryState } from "../../../src/components/consumption/QueryState";
import type { DetailResult } from "../../../src/lib/api/consumption";

afterEach(cleanup);
it.each([['no_meter', 'Sin medidor'], ['no_data', 'Sin datos'], ['available', 'Datos disponibles'], ['incomplete', 'Datos incompletos']])("explains %s", (state, label) => {
  /** No state fabricates an energy row; graph/table own only actual numeric rows. */
  render(<QueryState loading={false} error={null} data={{ state, diagnostics: [], warnings: [] } as unknown as DetailResult} retry={vi.fn()} />);
  expect(screen.getByText(label, { exact: false })).toBeTruthy();
});

it("distinguishes loading, error and keyboard retry", () => {
  /** Status text and native buttons remain usable without relying on a color legend. */
  const retry = vi.fn();
  const { rerender } = render(<QueryState loading error={null} data={null} retry={retry} />);
  expect(screen.getByRole("status").textContent).toContain("Consultando");
  rerender(<QueryState loading={false} error="Error sintético" data={null} retry={retry} />);
  expect(screen.getByRole("alert")).toBeTruthy();
  screen.getByRole("button", { name: "Reintentar" }).click();
  expect(retry).toHaveBeenCalledOnce();
});

it("explains a changed calculation without fabricated missing inputs or a wait date", () => {
  /** Changed signatures are a distinct functional diagnosis, not an admission delay. */
  const data = { state: "incomplete", warnings: [], diagnostics: [{ start: "start", end: "end",
    reason_code: "calculation_configuration_changed", missing_categories: [], next_admissible_at: null,
    configuration_segments: [{ start: "start", end: "end", category_revision: 2, source_mode: "calculated", base_categories: ["CAT-03"], basis_sources: [{ category_id: "CAT-03", source_id: "synthetic" }] }] }] } as unknown as DetailResult;
  render(<QueryState loading={false} error={null} data={data} retry={vi.fn()} />);
  expect(screen.getByText("Cambió la configuración de cálculo dentro del intervalo")).toBeTruthy();
  expect(screen.queryByText(/Faltan contribuciones/)).toBeNull();
  expect(screen.queryByText(/Próxima admisible/)).toBeNull();
});

it.each(["missing_contributions", "pending_incorporation"])("explains %s independently of numeric rows", reason => {
  /** Missing inputs and temporal waiting have different explanations; neither creates an energy figure. */
  const data = { state: "incomplete", warnings: [{ code: "no_calculation_basis", count: 1, message: "Sin base de cálculo" }],
    diagnostics: [{ start: "start", end: "end", reason_code: reason, missing_categories: ["CAT-05"],
      next_admissible_at: "2026-01-01T01:00:00-03:00", configuration_segments: [] }] } as unknown as DetailResult;
  render(<QueryState loading={false} error={null} data={data} retry={vi.fn()} />);
  expect(screen.getByText("Sin base de cálculo (1)")).toBeTruthy();
  expect(screen.getByText(reason === "missing_contributions" ? /Faltan contribuciones: CAT-05/ : /Incorporación pendiente/)).toBeTruthy();
  expect(screen.queryByRole("row")).toBeNull();
});
