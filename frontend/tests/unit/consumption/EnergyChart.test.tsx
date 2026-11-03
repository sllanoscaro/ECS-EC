/** SVG intervals preserve exact accessible evidence, zero/tiny markers and genuine temporal gaps. */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { EnergyChart } from "../../../src/components/consumption/EnergyChart";
import { row } from "./fixtures";

afterEach(cleanup);

it("splits a smooth line at null readings and missing intervals", () => {
  /** Interpolation must never connect across unavailable readings or remove exact evidence. */
  const point = (hour: number, energy_kwh: string | null) => ({ start: `2026-01-01T0${hour}:00:00-03:00`, end: `2026-01-01T0${hour + 1}:00:00-03:00`, energy_kwh });
  const { container } = render(<EnergyChart smooth rows={[]} timezone="America/Santiago" points={[point(0, '1'), point(1, '2'), point(2, null), point(3, '0'), point(5, '3')]} />);
  const paths = container.querySelectorAll('[data-series="smooth"]');
  expect(paths).toHaveLength(3);
  expect(paths[0].getAttribute('d')).toContain(' C ');
  expect(paths[1].getAttribute('d')).not.toContain(' C ');
  expect(container.querySelectorAll('rect')).toHaveLength(0);
  expect(screen.getAllByRole('graphics-symbol')).toHaveLength(5);
  expect(container.innerHTML).not.toMatch(/NaN|Infinity/);
});

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


it('shows dashboard evidence over the plot with rounded energy and local end time', () => {
  /** Compact evidence must not append a reading below the legend; exact accessible evidence remains. */
  const { container } = render(<EnergyChart presentation="dashboard" smooth rows={[
    row('12.35', '2026-01-01T02:00:00-03:00', '2026-01-01T02:15:12-03:00'),
  ]} timezone="America/Santiago" />);
  const point = screen.getByRole('graphics-symbol');
  expect(point.getAttribute('aria-label')).toContain('12.35 kWh');
  fireEvent.mouseEnter(point);
  expect(screen.getByRole('tooltip').textContent).toBe('12,4 kWh · 02:15:12');
  expect(screen.getByRole('tooltip').closest('.chart-plot')).toBeTruthy();
  expect(container.querySelector('p.chart-tooltip')).toBeNull();
  expect(container.querySelectorAll('svg title')).toHaveLength(0);
  expect(screen.getByText('12,4')).toBeTruthy();
  fireEvent.mouseLeave(point);
  expect(screen.queryByRole('tooltip')).toBeNull();
  fireEvent.focus(point);
  expect(screen.getByRole('tooltip').textContent).toBe('12,4 kWh · 02:15:12');
  fireEvent.blur(point);
  expect(screen.queryByRole('tooltip')).toBeNull();
});

it('keeps dashboard zero and missing energy distinct in compact tooltips', () => {
  /** A gap has no fabricated zero; rounding a genuine zero retains its zero marker. */
  render(<EnergyChart presentation="dashboard" smooth rows={[]} points={[
    { start: '2026-01-01T02:00:00-03:00', end: '2026-01-01T02:15:00-03:00', energy_kwh: '0' },
    { start: '2026-01-01T02:15:00-03:00', end: '2026-01-01T02:30:00-03:00', energy_kwh: null },
  ]} timezone="America/Santiago" />);
  const points = screen.getAllByRole('graphics-symbol');
  fireEvent.focus(points[0]);
  expect(screen.getByRole('tooltip').textContent).toBe('0,0 kWh · 02:15:00');
  fireEvent.focus(points[1]);
  expect(screen.getByRole('tooltip').textContent).toBe('Sin datos · 02:30:00');
});
