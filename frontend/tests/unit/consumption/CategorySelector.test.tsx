/** Every fixed category stays selectable even when it has no physical source or data. */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CategorySelector } from "../../../src/components/consumption/CategorySelector";
import type { CategoryStatus } from "../../../src/lib/api/consumption-types";

afterEach(cleanup);

it("renders seven ordered selectable categories and emits only the chosen id", () => {
  /** Availability never disables an option or sends a category inferred from a previous response. */
  const ids = ["CAT-07","CAT-06","CAT-05","CAT-04","CAT-03","CAT-02","CAT-01"] as const;
  const categories: CategoryStatus[] = ids.map(id => ({ id, name: `Categoría ${id}`, scope: "Synthetic",
    has_meter: false, source_mode: "unavailable", base_categories: [], category_revision: 1 }));
  const choose = vi.fn();
  render(<CategorySelector categories={categories} value="CAT-01" onChange={choose} />);
  const options = screen.getAllByRole("option") as HTMLOptionElement[];
  expect(options.map(option => option.value)).toEqual(["CAT-01","CAT-02","CAT-03","CAT-04","CAT-05","CAT-06","CAT-07"]);
  expect(options.every(option => !option.disabled)).toBe(true);
  expect(options[4].textContent).toContain("Sin medidor");
  fireEvent.change(screen.getByLabelText("Categoría"), { target: { value: "CAT-05" } });
  expect(choose).toHaveBeenCalledExactlyOnceWith("CAT-05");
});
