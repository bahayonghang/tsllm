import { describe, expect, it } from "vitest";
import {
  durationMs,
  EMPTY,
  formatDataTime,
  formatNumber,
  formatPercent,
  shiftDataTime,
} from "../../src/utils/format";

describe("format", () => {
  it("shows data times unchanged", () => {
    expect(formatDataTime("2024-03-10T02:30:00")).toBe("2024-03-10 02:30:00");
    expect(formatDataTime(null)).toBe(EMPTY);
  });

  it("shows missing numbers as —", () => {
    expect(formatNumber(null)).toBe(EMPTY);
    expect(formatNumber(Number.NaN)).toBe(EMPTY);
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber(0.123456)).toBe("0.1235");
    expect(formatPercent(0.25)).toBe("25.0%");
  });

  it("parses duration strings", () => {
    expect(durationMs("10s")).toBe(10_000);
    expect(durationMs("5min")).toBe(300_000);
    expect(durationMs("1h")).toBe(3_600_000);
    expect(durationMs("bad")).toBeNull();
  });

  it("shifts data times without a time zone conversion", () => {
    expect(shiftDataTime("2024-01-01T00:00:00", "10s", -2)).toBe("2023-12-31T23:59:40");
    expect(shiftDataTime("2024-03-10T01:00:00", "1h", 2)).toBe("2024-03-10T03:00:00");
    expect(shiftDataTime("2024-01-01T00:00:00", "bad", 1)).toBeNull();
  });
});
