import { describe, expect, it } from "vitest";
import { formatEventTime, parseEventTime } from "../lib/time";

describe("parseEventTime", () => {
  it("reads zone-less, offset and Z timestamps as the same instant", () => {
    const bare = parseEventTime("2026-10-08T05:36:22.972272");
    const offset = parseEventTime("2026-10-08T05:36:22.972272+00:00");
    const zulu = parseEventTime("2026-10-08T05:36:22Z");
    expect(bare).not.toBeNull();
    expect(bare?.getTime()).toBe(offset?.getTime());
    expect(Math.floor((bare?.getTime() ?? 0) / 1000)).toBe(
      Math.floor((zulu?.getTime() ?? 1) / 1000),
    );
    expect(bare?.toISOString()).toBe("2026-10-08T05:36:22.972Z");
  });

  it("leaves a non-UTC offset unchanged", () => {
    expect(parseEventTime("2026-10-08T05:36:22-07:00")?.toISOString()).toBe(
      "2026-10-08T12:36:22.000Z",
    );
  });

  it("falls back to the raw text for an invalid string", () => {
    expect(parseEventTime("not a time")).toBeNull();
    expect(formatEventTime("not a time")).toBe("not a time");
  });
});
