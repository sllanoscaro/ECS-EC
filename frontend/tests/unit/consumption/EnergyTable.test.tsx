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


it('separates local days while showing only times and one decimal in the compact table', () => {
  /** UTC dates can match while building-local days differ; midnight ends belong to the starting row. */
  const first = row('123.45', '2026-01-02T02:45:00Z', '2026-01-02T03:00:00Z');
  const second = row('0', '2026-01-02T03:00:00Z', '2026-01-02T03:15:00Z');
  const { container } = render(<EnergyTable compact rows={[first, second]} timezone="America/Santiago" categoryId="CAT-05" />);
  expect(container.querySelectorAll('.consumption-day-divider')).toHaveLength(2);
  expect(screen.getAllByRole('rowheader').map(el => el.textContent)).toEqual(['jueves, 1 de enero de 2026', 'viernes, 2 de enero de 2026']);
  expect(screen.getByRole('cell', { name: '23:45' })).toBeTruthy();
  expect(screen.getAllByRole('cell', { name: '00:00' })).toHaveLength(2);
  expect(screen.getByRole('cell', { name: '123,5 kWh' }).getAttribute('title')).toBe('123.45');
  expect(screen.getByRole('cell', { name: '0,0 kWh' })).toBeTruthy();
});

it('keeps a repeated local hour in the same day group and retains distinct offsets', () => {
  /** Santiago fall-back repeats23:00 on the same local day; grouping must not invent a date change. */
  const records = [row('1', '2026-04-04T23:00:00-03:00', '2026-04-04T23:15:00-03:00'), row('2', '2026-04-04T23:00:00-04:00', '2026-04-04T23:15:00-04:00')];
  const { container } = render(<EnergyTable compact rows={records} timezone="America/Santiago" categoryId="CAT-05" />);
  expect(container.querySelectorAll('.consumption-day-divider')).toHaveLength(1);
  expect(screen.getAllByRole('cell', { name: '23:00' }).map(el => el.getAttribute('title'))).toEqual(records.map(item => item.start));
});
