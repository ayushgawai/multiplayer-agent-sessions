import { describe, expect, it } from "vitest";
import type { SessionEvent } from "../lib/api";
import {
  appendLive,
  describeEvent,
  eventsSignature,
  mergeServerWithLive,
} from "../lib/events";

function ev(seq: number, id: string, type: SessionEvent["type"] = "instruction", payload: Record<string, unknown> = {}): SessionEvent {
  return {
    event_id: id,
    session_id: "s",
    seq,
    ts: "2026-10-08T00:00:00Z",
    actor: { kind: "human", id: "p_1", display_name: "Ada", role: "author" },
    type,
    payload,
  };
}

describe("appendLive", () => {
  it("ignores a duplicate and appends a new seq", () => {
    const base = [ev(1, "a"), ev(2, "b")];
    expect(appendLive(base, ev(2, "b"))).toHaveLength(2);
    expect(appendLive(base, ev(3, "c")).map((e) => e.seq)).toEqual([1, 2, 3]);
  });

  it("drops the stale tail when a seq is rewritten after rollback", () => {
    const base = [ev(1, "a"), ev(2, "b"), ev(3, "c")];
    const next = appendLive(base, ev(2, "b2"));
    expect(next.map((e) => e.event_id)).toEqual(["a", "b2"]);
  });
});

describe("mergeServerWithLive", () => {
  it("lets the server win and keeps only live events past it", () => {
    const server = [ev(1, "a"), ev(2, "b")];
    const live = [ev(2, "stale"), ev(3, "c")];
    expect(mergeServerWithLive(server, live).map((e) => e.event_id)).toEqual(["a", "b", "c"]);
  });

  it("removes events rolled back on the server", () => {
    expect(mergeServerWithLive([ev(1, "a")], []).map((e) => e.seq)).toEqual([1]);
  });
});

describe("eventsSignature and describeEvent", () => {
  it("differs when an id differs at the same seq", () => {
    expect(eventsSignature([ev(1, "a")])).not.toBe(eventsSignature([ev(1, "b")]));
  });

  it("describes instruction, join and rejected events", () => {
    expect(describeEvent(ev(1, "a", "instruction", { text: "hello" }))).toBe("hello");
    expect(describeEvent(ev(2, "b", "join", { role: "reviewer" }))).toBe("joined as reviewer");
    expect(
      describeEvent(ev(3, "c", "rejected", { attempted_type: "instruction", reason: "role observer cannot append instruction" })),
    ).toBe("instruction rejected: role observer cannot append instruction");
  });
});
