/** Administrative source form tests are isolated from the pending authenticated route/storage integration. */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ConfigurationForm } from "../../../src/components/consumption/ConfigurationForm";
import type { Category, Configuration } from "../../../src/lib/api/consumption-types";
import { Problem } from "../../../src/lib/api/session";

afterEach(cleanup);
const categories = [1,2,3,4,5,6,7].map(i => ({ id: `CAT-0${i}`, name: `Categoría ${i}`, scope: "Synthetic" })) as Category[];

/** Build an administrative snapshot with one present partial and server-derived revision metadata. */
function configuration(): Configuration {
  return { id: "synthetic", building_id: "synthetic-building", revision: 4, effective_from: "2025-01-01T00:00:00Z",
    recorded_at: "2025-01-01T00:00:00Z", timezone: "America/Santiago", categories: categories.map(category => ({
      category_id: category.id, has_meter: category.id === "CAT-03", category_revision: 2,
      source_id: category.id === "CAT-03" ? "00000000-0000-0000-0000-000000000003" : null,
      source_label: category.id === "CAT-03" ? "Synthetic source" : null })) };
}

it("uses expected global revision, strips derived fields and treats labels as cosmetic", async () => {
  /** Label edits create no predicted category-source change; the server still validates actual signatures. */
  const save = vi.fn().mockResolvedValue(configuration());
  render(<ConfigurationForm configuration={configuration()} timezone="America/Santiago" categories={categories} save={save} />);
  fireEvent.change(screen.getByLabelText("Etiqueta CAT-03"), { target: { value: "Renamed" } });
  expect(screen.getByText("Sin cambios de fuente previstos.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Guardar configuración" }));
  await waitFor(() => { expect(save).toHaveBeenCalledOnce(); });
  const input = save.mock.calls[0][0];
  expect(input.expected_revision).toBe(4);
  expect(input.effective_from).toBeNull();
  expect(input.categories).toHaveLength(7);
  expect(input.categories[2].source_label).toBe("Renamed");
  expect(input.categories[2]).not.toHaveProperty("category_revision");
});

it("preserves the draft after503 and previews the partial plus calculated total source change", async () => {
  /** Missing002 bounds cannot erase the current configuration or silently assume no history. */
  const save = vi.fn().mockRejectedValue(new Problem(503, "reconfiguration_bounds_unavailable", "No se pudo comprobar la historia."));
  render(<ConfigurationForm configuration={configuration()} timezone="America/Santiago" categories={categories} save={save} />);
  fireEvent.change(screen.getByLabelText("Fuente UUID CAT-03"), { target: { value: "00000000-0000-0000-0000-000000000030" } });
  expect(screen.getByText("Cambios de fuente previstos: CAT-01, CAT-03")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Guardar configuración" }));
  await screen.findByRole("alert");
  expect((screen.getByLabelText("Fuente UUID CAT-03") as HTMLInputElement).value).toBe("00000000-0000-0000-0000-000000000030");
});

it("allows an explicitly configured empty basis during initial setup", async () => {
  /** All absent meters are valid; no logical UUID is fabricated forCAT-01. */
  const save = vi.fn().mockResolvedValue(configuration());
  render(<ConfigurationForm configuration={null} timezone="America/Santiago" categories={categories} save={save} />);
  fireEvent.change(screen.getByLabelText("Vigencia inicial (ISO 8601 con offset)"), { target: { value: "2025-01-01T00:00:00Z" } });
  fireEvent.click(screen.getByRole("button", { name: "Guardar configuración" }));
  await waitFor(() => { expect(save).toHaveBeenCalledOnce(); });
  const input = save.mock.calls[0][0];
  expect(input.expected_revision).toBe(0);
  expect(input.categories.every((entry: { source_id: string | null }) => entry.source_id === null)).toBe(true);
});
