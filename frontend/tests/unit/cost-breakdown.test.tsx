/**004 view checks compare exact response values, never a duplicated browser-side cost formula. */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { CostBreakdown } from "../../src/components/costs/CostBreakdown";
import type { CalculationDetail } from "../../src/lib/api/costs";

afterEach(cleanup);
it("keeps a partial subtotal distinct from a complete total and presents identical component strings", () => {
  /** A missing complete total must stay absent while the available energy remains inspectable in both views. */
  const data = { id: "synthetic", revision: 1, temporal_state: "en_curso", sufficiency: "parcial", execution_state: "completado",
    currency: "CLP", available_subtotal: "100000", complete_total: null, reason_codes: ["billing_month_unresolved"],
    monthly_maxima: [], components: [{ code: "energy", kind: "energia", basis_value: "1000", unit: "kWh", rule_id: "exact_intervals", unit_price: "100",
      tax_basis: "neto", presented_amount: "100000", state: "available", limitation_codes: [], applied_prices: [] }],
    snapshot: { cutoff_at: "2026-01-01T00:00:00Z", request: { start: "2026-01-01T00:00:00Z", end: "2026-02-01T00:00:00Z", timezone: "Etc/UTC" },
      supply: { general_board_ref: "Synthetic board", document_refs: [], measurement_point_differences: [] }, supply_revision: 1, profile_revision: 1,
      billing_month_ref: null, general_reason: null } } as unknown as CalculationDetail;
  render(<CostBreakdown calculation={data} />);
  expect(screen.getByText("Costo completo: no disponible")).toBeTruthy();
  expect(screen.getByRole("cell", { name: "100000 CLP" })).toBeTruthy();
  expect(screen.getByRole("graphics-symbol").getAttribute("aria-label")).toContain("100000 CLP");
});

it("preserves calculation inputs and reuses the operation key after a lost response", async () => {
  /** Same-body retries are idempotent; confirmation after an input change must have a distinct operation identity. */
  const { fireEvent, waitFor } = await import("@testing-library/react");
  const { vi } = await import("vitest");
  const { CalculationForm } = await import("../../src/components/costs/CalculationForm");
  const save = vi.fn().mockRejectedValueOnce(new Error("synthetic loss")).mockResolvedValue({ id: "saved" });
  render(<CalculationForm supply={{ id: "synthetic", revision: 1 } as never} previous={null} onSaved={vi.fn()} save={save} />);
  fireEvent.change(screen.getByLabelText("Inicio del ciclo con offset"), { target: { value: "2026-01-01T00:00:00Z" } });
  fireEvent.change(screen.getByLabelText("Fin del ciclo con offset"), { target: { value: "2026-01-01T01:00:00Z" } });
  fireEvent.click(screen.getByRole("button", { name: "Confirmar cálculo" }));
  await screen.findByRole("alert");
  expect((screen.getByLabelText("Inicio del ciclo con offset") as HTMLInputElement).value).toContain("2026-01-01");
  fireEvent.click(screen.getByRole("button", { name: "Confirmar cálculo" }));
  await waitFor(() => { expect(save).toHaveBeenCalledTimes(2); });
  expect(save.mock.calls[0][1]).toBe(save.mock.calls[1][1]);
});

it("charts exactly the persisted comparable values and omits pending contrasts", async () => {
  /** Same-pair calculated/billed/delta strings drive history geometry; missing comparisons are absent, never zero. */
  const { CostChart } = await import("../../src/components/costs/CostChart");
  const cycle = { start_at: "2026-01-01", end_at: "2026-02-01", calculation: { complete_total: "105", available_subtotal: "105" },
    comparison_status: "available", comparison: { comparable_calculated: "105", comparable_billed: "100", delta_amount: "5" } };
  const view = render(<CostChart series={[cycle] as never} />);
  expect(screen.getByRole("graphics-symbol", { name: /Facturado comparable: 100 CLP/ })).toBeTruthy();
  expect(screen.getByRole("graphics-symbol", { name: /Diferencia comparable: 5 CLP/ })).toBeTruthy();
  view.rerender(<CostChart series={[{ ...cycle, comparison_status: "missing_for_selected_revisions", comparison: null }] as never} />);
  expect(screen.queryByRole("graphics-symbol", { name: /comparable:/ })).toBeNull();
});
