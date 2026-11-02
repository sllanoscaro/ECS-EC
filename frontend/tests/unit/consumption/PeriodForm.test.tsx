/** Invalid period drafts must not replace the last submitted selection. */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PeriodForm } from "../../../src/components/consumption/PeriodForm";

afterEach(cleanup);
it("preserves drafts and refuses reversed or nonexistent local times", () => {
  /** The browser zone is irrelevant: the explicit building offset is validated by round-trip. */
  const onSubmit = vi.fn();
  render(<PeriodForm period={{ start: "2026-01-01T00:00:00-03:00", end: "2026-01-02T00:00:00-03:00", timezone: "America/Santiago" }} onSubmit={onSubmit} />);
  fireEvent.change(screen.getByLabelText("Inicio con offset"), { target: { value: "2026-01-03T00:00:00-03:00" } });
  fireEvent.click(screen.getByRole("button", { name: "Consultar período" }));
  expect(onSubmit).not.toHaveBeenCalled();
  expect(screen.getByRole("alert")).toBeTruthy();
  expect((screen.getByLabelText("Inicio con offset") as HTMLInputElement).value).toContain("2026-01-03");
});

it("accepts both offsets of a repeated hour and rejects Santiago's missing hour", () => {
  /** Native Date is used only for IANA wall-field validation; exact interval ordering uses microseconds. */
  const onSubmit = vi.fn();
  render(<PeriodForm period={{ start: "2026-04-04T23:30:00-03:00", end: "2026-04-04T23:30:00-04:00", timezone: "America/Santiago" }} onSubmit={onSubmit} />);
  fireEvent.click(screen.getByRole("button", { name: "Consultar período" }));
  expect(onSubmit).toHaveBeenCalledOnce();
  fireEvent.change(screen.getByLabelText("Inicio con offset"), { target: { value: "2026-09-06T00:30:00-04:00" } });
  fireEvent.change(screen.getByLabelText("Fin con offset"), { target: { value: "2026-09-06T02:30:00-03:00" } });
  fireEvent.click(screen.getByRole("button", { name: "Consultar período" }));
  expect(onSubmit).toHaveBeenCalledOnce();
  expect(screen.getByRole("alert")).toBeTruthy();
});
