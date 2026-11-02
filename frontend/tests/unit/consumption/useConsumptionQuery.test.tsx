/** Race regression: even a transport that resolves after abort cannot publish an old selection. */
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useConsumptionQuery } from "../../../src/components/consumption/useConsumptionQuery";
import { clearPrivateData } from "../../../src/lib/api/session";
import type { DetailResult, Period } from "../../../src/lib/api/consumption";

afterEach(cleanup);
const period: Period = { start: "2026-01-01T00:00:00-03:00", end: "2026-01-02T00:00:00-03:00", timezone: "America/Santiago" };

it("discards A after B, retries B and clears all private results", async () => {
  /** Deferred promises deliberately ignore AbortSignal, modeling a response already buffered by the browser. */
  const callbacks: ((value: DetailResult) => void)[] = [];
  const fetch = vi.fn((_category: string) => new Promise<DetailResult>(resolve => { callbacks.push(resolve); }));
  const { result, rerender } = renderHook(({ category }) => useConsumptionQuery(category, period, fetch), { initialProps: { category: "CAT-01" as "CAT-01" | "CAT-05" } });
  rerender({ category: "CAT-05" });
  await act(async () => { callbacks[0]({ state: "no_data" } as DetailResult); });
  expect(result.current.data).toBeNull();
  await act(async () => { callbacks[1]({ state: "available" } as DetailResult); });
  expect(result.current.data?.state).toBe("available");
  act(() => { result.current.retry(); });
  await waitFor(() => { expect(fetch).toHaveBeenCalledTimes(3); });
  expect(result.current.data).toBeNull();
  act(clearPrivateData);
  await act(async () => { callbacks[2]({ state: "available" } as DetailResult); });
  expect(result.current.data).toBeNull();
});

it("keeps B's failure after late A and retries the current category", async () => {
  /** A rejection and a later completion belong to their own generations, never to another category. */
  const queue: { resolve: (value: DetailResult) => void; reject: (error: Error) => void }[] = [];
  const fetch = vi.fn((_category: string) => new Promise<DetailResult>((resolve, reject) => { queue.push({ resolve, reject }); }));
  const { result, rerender } = renderHook(({ category }) => useConsumptionQuery(category, period, fetch), { initialProps: { category: "CAT-01" as "CAT-01" | "CAT-05" } });
  rerender({ category: "CAT-05" });
  await act(async () => { queue[1].reject(new Error("synthetic")); });
  expect(result.current.error).toBeTruthy();
  await act(async () => { queue[0].resolve({ state: "available" } as DetailResult); });
  expect(result.current.data).toBeNull();
  act(() => { result.current.retry(); });
  await waitFor(() => { expect(fetch).toHaveBeenCalledTimes(3); });
  expect(fetch.mock.calls[2][0]).toBe("CAT-05");
  await act(async () => { queue[2].resolve({ state: "available" } as DetailResult); });
  expect(result.current.data?.state).toBe("available");
});
