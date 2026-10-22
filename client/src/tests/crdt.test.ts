import { describe, expect, it } from "vitest";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";
import {
  BODY_FIELD,
  DEFAULT_CRDT_URL,
  META_FIELD,
  createCollabDoc,
  crdtRoomUrl,
  crdtServerUrl,
} from "../lib/crdt";

/** Small seeded generator so the random run is repeatable. */
function rng(seed: number): () => number {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function makePeer(): { doc: Y.Doc; outbox: Uint8Array[] } {
  const doc = new Y.Doc();
  const outbox: Uint8Array[] = [];
  doc.on("update", (update: Uint8Array, origin: unknown) => {
    if (origin !== "remote") {
      outbox.push(update);
    }
  });
  return { doc, outbox };
}

describe("Yjs convergence", () => {
  it("three docs converge after 200 random insert and delete ops", () => {
    const random = rng(42);
    const peers = [makePeer(), makePeer(), makePeer()];
    // Per-peer queues of updates not yet delivered to each other peer.
    const inbox: Uint8Array[][] = peers.map(() => []);

    const deliver = (to: number, count: number): void => {
      const queue = inbox[to];
      if (queue === undefined) {
        return;
      }
      // Deliver in shuffled order: Yjs must not depend on arrival order.
      const batch = queue.splice(0, count).sort(() => random() - 0.5);
      for (const update of batch) {
        Y.applyUpdate(peers[to]!.doc, update, "remote");
      }
    };

    for (let op = 0; op < 200; op += 1) {
      const idx = Math.floor(random() * peers.length);
      const peer = peers[idx]!;
      const body = peer.doc.getXmlFragment(BODY_FIELD);
      const before = peer.outbox.length;

      if (body.length > 0 && random() < 0.35) {
        body.delete(Math.floor(random() * body.length), 1);
      } else {
        const para = new Y.XmlElement("paragraph");
        para.insert(0, [new Y.XmlText(`op${op}`)]);
        body.insert(Math.floor(random() * (body.length + 1)), [para]);
      }
      if (random() < 0.3) {
        peer.doc.getMap(META_FIELD).set(`k${op % 5}`, op);
      }

      for (const fresh of peer.outbox.slice(before)) {
        peers.forEach((_, other) => {
          if (other !== idx) {
            inbox[other]!.push(fresh);
          }
        });
      }
      if (random() < 0.4) {
        deliver(Math.floor(random() * peers.length), 1 + Math.floor(random() * 4));
      }
    }

    peers.forEach((_, i) => deliver(i, Number.MAX_SAFE_INTEGER));

    const bodies = peers.map((p) => p.doc.getXmlFragment(BODY_FIELD).toString());
    const metas = peers.map((p) => JSON.stringify(sortKeys(p.doc.getMap(META_FIELD).toJSON())));
    expect(bodies[1]).toBe(bodies[0]);
    expect(bodies[2]).toBe(bodies[0]);
    expect(metas[1]).toBe(metas[0]);
    expect(metas[2]).toBe(metas[0]);
    expect(bodies[0]?.length).toBeGreaterThan(0);
  });
});

function sortKeys(value: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)));
}

describe("provider url", () => {
  it("defaults to the local crdt-server and trims trailing slashes", () => {
    expect(crdtServerUrl({})).toBe(DEFAULT_CRDT_URL);
    expect(crdtServerUrl({ VITE_CRDT_URL: "ws://h:1234/crdt/" })).toBe("ws://h:1234/crdt");
    expect(crdtServerUrl({ VITE_CRDT_URL: "  " })).toBe(DEFAULT_CRDT_URL);
  });

  it("builds the room url from env and session id", () => {
    expect(crdtRoomUrl({ VITE_CRDT_URL: "ws://h:9/crdt" }, "ses_1")).toBe("ws://h:9/crdt/ses_1");
  });

  it("the real provider connects to that room url", () => {
    const env = { VITE_CRDT_URL: "ws://example.test:1234/crdt" };
    const collab = createCollabDoc({ env, sessionId: "ses_abc", connect: false });
    expect(collab.provider).toBeInstanceOf(WebsocketProvider);
    expect(collab.provider?.url).toBe(crdtRoomUrl(env, "ses_abc"));
    expect(collab.meta.get("sessionId")).toBe("ses_abc");
    collab.destroy();
  });

  it("mock mode has a local-only doc with no provider", () => {
    const collab = createCollabDoc({ env: { VITE_USE_MOCK: "true" }, sessionId: "s" });
    expect(collab.provider).toBeNull();
    expect(collab.isRemote("anything")).toBe(false);
    collab.destroy();
  });
});
