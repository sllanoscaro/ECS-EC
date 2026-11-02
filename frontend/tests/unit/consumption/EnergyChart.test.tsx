/** SVG intervals preserve exact accessible evidence, zero/tiny markers and genuine temporal gaps. */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { EnergyChart } from "../../../src/components/consumption/EnergyChart";
import { row } from "./fixtures";

afterEach(cleanup);

it("shows one focusable datum including its exact energy and microseconds", () => {
  /** A single interval must render without requiring a second sample to form a line. */
  render(<EnergyChart rows={[row("0.000000000000001")]} timezone="America/Santiago" />);
  expect(screen.getByRole("img", { name: "Energía eléctrica por intervalo (kWh)" })).toBeTruthy();
  const datum = screen.getByRole("graphics-symbol");
  expect(datum.getAttribute("tabindex")).toBe("0");
  expect(datum.getAttribute("aria-label")).toContain("0.000000000000001 kWh");
  expect(datum.getAttribute("aria-label")).toContain("00:00:00.000001-03:00");
});

it("distinguishes zero/subpixel positive, keeps gaps and never connects intervals", () => {
  /** Inspect interval geometry and semantic markers without computing business quantities in Number. */
  const { container } = render(<EnergyChart timezone="America/Santiago" rows={[row("0"),
    row("0.000000000000001", "2026-01-01T02:00:00-03:00", "2026-01-01T03:00:00-03:00"),
    row("999999999999999999999999999999.999999999999999", "2026-01-01T04:00:00-03:00", "2026-01-01T05:00:00-03:00")]} />);
  expect(container.querySelectorAll('[data-kind="zero"]')).toHaveLength(1);
  expect(container.querySelectorAll('[data-kind="subpixel-positive"]')).toHaveLength(1);
  expect(container.querySelectorAll("polyline,path")).toHaveLength(0);
  const symbols = screen.getAllByRole("graphics-symbol");
  expect(symbols).toHaveLength(3);
  expect(Number(symbols[1].getAttribute("data-x"))).toBeGreaterThan(Number(symbols[0].getAttribute("data-x-end")));
});

it("retains a visible scale and zero marker for an all-zero dataset", () => {
  /** No division by zero/NaN and no disappearance of a valid measured zero. */
  const { container } = render(<EnergyChart rows={[row("0")]} timezone="America/Santiago" />);
  expect(container.innerHTML).not.toMatch(/NaN|Infinity/);
  expect(container.querySelector('[data-kind="zero"]')).toBeTruthy();
  expect(screen.getByText("1 kWh")).toBeTruthy();
});
