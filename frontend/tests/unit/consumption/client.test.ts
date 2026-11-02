/** Isolated client contract checks; HTTP/server integration waits for the002 provider. */
import { afterEach, expect, it, vi } from "vitest";
import { consumptionApi } from "../../../src/lib/api/consumption";
import { clearPrivateData, sessionApi } from "../../../src/lib/api/session";
import type { ConfigurationInput } from "../../../src/lib/api/consumption-types";

afterEach(() => { clearPrivateData(); vi.unstubAllGlobals(); });

it("uses authenticated no-store fetch and retains textual offsets/microseconds", async () => {
  /** The normal shared006 adapter supplies credentials; no consumption-specific session mechanism exists. */
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ rows: [] }), { status: 200 }));
  vi.stubGlobal("fetch", fetcher);
  const signal = new AbortController().signal;
  const period = { start: "2026-01-01T00:00:00.000001-03:00", end: "2026-01-02T00:00:00-03:00", timezone: "America/Santiago" };
  await consumptionApi.detail("CAT-05", period, signal);
  const [url, options] = fetcher.mock.calls[0];
  const parsed = new URL(url, "https://synthetic.test");
  expect(parsed.pathname).toBe("/api/v1/consumption/categories/CAT-05/detail");
  expect(parsed.searchParams.get("start")).toBe(period.start);
  expect(parsed.searchParams.get("timezone")).toBe(period.timezone);
  expect(options.credentials).toBe("same-origin");
  expect(options.cache).toBe("no-store");
  expect(options.signal).toBe(signal);
});

it("sends current CSRF and only writable source fields even when passed a wider object", async () => {
  /** Runtime projection prevents server-derived revisions from being echoed into a PUT. */
  const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: "synthetic-csrf" })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ revision: 2 })));
  vi.stubGlobal("fetch", fetcher);
  await sessionApi.read();
  const extra = { expected_revision: 1, effective_from: null, timezone: "America/Santiago", revision: 2,
    categories: [{ category_id: "CAT-03", has_meter: true, source_id: "synthetic-id", source_label: "Synthetic", category_revision: 4 }] };
  await consumptionApi.configure(extra as ConfigurationInput);
  const [, options] = fetcher.mock.calls[1];
  expect(options.headers.get("X-CSRF-Token")).toBe("synthetic-csrf");
  expect(JSON.parse(options.body)).toEqual({ expected_revision: 1, effective_from: null, timezone: "America/Santiago",
    categories: [{ category_id: "CAT-03", has_meter: true, source_id: "synthetic-id", source_label: "Synthetic" }] });
});

it("preserves the shared safe Problem for an HTTP failure", async () => {
  /**503 remains an error rather than being converted to an empty successful dataset. */
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: "unavailable", detail: "Consulta no disponible." }), { status: 503 })));
  await expect(consumptionApi.catalog()).rejects.toMatchObject({ status: 503, code: "unavailable", message: "Consulta no disponible." });
});
