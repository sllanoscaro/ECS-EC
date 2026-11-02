/** Table evidence must match exactly what each SVG datum describes. */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { EnergyTable } from "../../../src/components/consumption/EnergyTable";
import { row } from "./fixtures";

afterEach(cleanup);

it("preserves complete values, original units and temporal microseconds", () => {
  /** Independent boundary strings are displayed intact, without a display-specific precision policy. */
  const value = "999999999999999999999999999999.999999999999999";
  render(<EnergyTable rows={[row(value)]} timezone="America/Santiago" categoryId="CAT-05" />);
  const table = screen.getByRole("table");
  expect(within(table).getAllByRole("columnheader").map(n => n.textContent)).toEqual(["Inicio (incluido)", "Fin (excluido)", "Energía (kWh)", "Procedencia"]);
  expect(within(table).getByText(`${value} kWh`)).toBeTruthy();
  expect(within(table).getByText(/Original:/).textContent).toContain(value);
  expect(within(table).getAllByText(/00:00:00.000001-03:00/)).not.toHaveLength(0);
});

it("shows calculated basis and individual contribution provenance without inventing rows", () => {
  /** One incorporated total remains one row; contributions are evidence rather than duplicate totals. */
  const total = { ...row("20"), origin: { kind: "calculated" as const, base_categories: ["CAT-03", "CAT-05"] as const,
    contributions: [3,5].map((c,i) => ({ measurement_id: `part-${c}`, measurement_revision: 1,
      category_id: `CAT-0${c}` as "CAT-03" | "CAT-05", source_id: `source-${c}`, start: row().start,
      end: row().end, energy_kwh: i === 0 ? "12" : "8", category_revision: 1 })) } };
  render(<EnergyTable rows={[total]} timezone="America/Santiago" categoryId="CAT-01" />);
  expect(screen.getByText("Total calculado de las categorías presentes")).toBeTruthy();
  expect(screen.getByText(/CAT-03: 12 kWh/)).toBeTruthy();
  expect(screen.getAllByRole("row")).toHaveLength(2);
  expect(screen.getByText(/no garantiza cubrir todas las cargas/)).toBeTruthy();
});
