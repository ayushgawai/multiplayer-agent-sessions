import { describe, expect, it } from "vitest";
import {
  Awareness,
  applyAwarenessUpdate,
  encodeAwarenessUpdate,
  removeAwarenessStates,
} from "y-protocols/awareness";
import * as Y from "yjs";
import { announce, readPresence, subscribePresence, type PresenceEntry } from "../lib/presence";

type Role = "author" | "reviewer" | "observer";

/** Two awareness peers wired together, like two tabs on one provider. */
function pair(): { a: Awareness; b: Awareness } {
  const a = new Awareness(new Y.Doc());
  const b = new Awareness(new Y.Doc());
  const link = (from: Awareness, to: Awareness): void => {
    from.on(
      "update",
      (
        change: { added: number[]; updated: number[]; removed: number[] },
        origin: unknown,
      ) => {
        if (origin === "remote") {
          return;
        }
        const ids = [...change.added, ...change.updated, ...change.removed];
        applyAwarenessUpdate(to, encodeAwarenessUpdate(from, ids), "remote");
      },
    );
  };
  link(a, b);
  link(b, a);
  return { a, b };
}

function info(id: string, name: string, role: Role): { participantId: string; displayName: string; role: Role } {
  return { participantId: id, displayName: name, role };
}

describe("presence list", () => {
  it("updates when a peer joins and when its state is removed", () => {
    const { a, b } = pair();
    const seen: PresenceEntry[][] = [];
    const stop = subscribePresence(a, (entries) => seen.push(entries));

    announce(a, info("p_1", "Ada", "author"));
    announce(b, info("p_2", "Ben", "observer"));
    const names = readPresence(a).map((e) => `${e.displayName}:${e.role}`);
    expect(names).toEqual(["Ada:author", "Ben:observer"]);
    expect(readPresence(a).find((e) => e.participantId === "p_1")?.isSelf).toBe(true);
    expect(seen.length).toBeGreaterThan(0);

    removeAwarenessStates(a, [b.clientID], "tab closed");
    expect(readPresence(a).map((e) => e.displayName)).toEqual(["Ada"]);
    expect(seen[seen.length - 1]?.map((e) => e.displayName)).toEqual(["Ada"]);

    stop();
    a.destroy();
    b.destroy();
  });

  it("shows a participant once even with two tabs and ignores incomplete states", () => {
    const { a, b } = pair();
    const c = new Awareness(new Y.Doc());
    announce(a, info("p_1", "Ada", "author"));
    announce(b, info("p_1", "Ada", "author"));
    applyAwarenessUpdate(a, encodeAwarenessUpdate(c, [c.clientID]), "remote");
    expect(readPresence(a)).toHaveLength(1);
    a.destroy();
    b.destroy();
    c.destroy();
  });

  it("mock mode: only the local user", () => {
    const local = new Awareness(new Y.Doc());
    announce(local, info("p_1", "Ada", "author"));
    expect(readPresence(local)).toHaveLength(1);
    local.destroy();
  });
});
