/** Compare each exact source interval/value in both representations, including the derived maximum. */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { EnergyChart } from "../../../src/components/consumption/EnergyChart";
import { EnergyTable } from "../../../src/components/consumption/EnergyTable";
import type { DetailRow } from "../../../src/lib/api/consumption-types";
import { row } from "./fixtures";

afterEach(cleanup);

it.each(["0", "0.000000000000001", "999999999999999999999999999999.999999999999999", "5999999999999999999999999999999.999999999999994"])("matches table and focused SVG evidence for %s", value => {
  /** Expected6*M is a literal; six separately referenced physicalM inputs establish its valid provenance. */
  const data: DetailRow = row(value);
  const total: DetailRow = value.startsWith("5999") ? { ...data, origin: { kind: "calculated",
    base_categories: ["CAT-02","CAT-03","CAT-04","CAT-05","CAT-06","CAT-07"],
    contributions: (["CAT-02","CAT-03","CAT-04","CAT-05","CAT-06","CAT-07"] as const).map((category,i) => ({
      measurement_id: `00000000-0000-0000-0000-00000000010${i}`, measurement_revision: 1,
      category_id: category, source_id: `00000000-0000-0000-0000-00000000000${i+2}`, category_revision: 1,
      start: data.start, end: data.end, energy_kwh: "999999999999999999999999999999.999999999999999" })) } } : data;
  render(<><EnergyChart rows={[total]} timezone="America/Santiago" />
    <EnergyTable rows={[total]} timezone="America/Santiago" categoryId="CAT-01" /></>);
  const cell = screen.getByRole("cell", { name: `${value} kWh` });
  const symbol = screen.getByRole("graphics-symbol");
  expect(symbol.getAttribute("aria-label")).toContain(cell.textContent);
  expect(symbol.getAttribute("aria-label")).toContain(data.start);
  expect(symbol.getAttribute("aria-label")).toContain(data.end);
  fireEvent.focus(symbol);
  expect(screen.getByRole("tooltip").textContent).toContain(`${value} kWh`);
});
