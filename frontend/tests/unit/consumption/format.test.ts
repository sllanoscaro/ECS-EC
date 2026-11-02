/** Exact textual quantities/timestamps must agree across all representations, independent of geometry. */
import { describe, expect, it } from "vitest";
import { energyLabel, instantLabel, projectRatio } from "../../../src/components/consumption/format";

describe("consumption presentation", () => {
  it("preserves q, M, six M, zero and textual microseconds", () => {
    /** Expected literals are independent of implementation arithmetic and native Number precision. */
    for (const value of ["0", "0.000000000000001", "999999999999999999999999999999.999999999999999", "5999999999999999999999999999999.999999999999994"]) {
      expect(energyLabel(value)).toBe(`${value} kWh`);
    }
    expect(instantLabel("2026-01-01T00:00:00.000001-03:00", "America/Santiago"))
      .toBe("2026-01-01T00:00:00.000001-03:00 (America/Santiago)");
  });
  it("projects only bounded coordinate ratios with a private precision50 context", () => {
    /** Number is allowed for geometry alone; a tiny ratio cannot alter the original business string. */
    expect(projectRatio("1", "2")).toBe(0.5);
    expect(projectRatio("0", "0")).toBe(0);
    expect(projectRatio("2", "1")).toBe(1);
    expect(projectRatio("0.000000000000001", "999999999999999999999999999999.999999999999999"))
      .toBeGreaterThan(0);
  });
});
