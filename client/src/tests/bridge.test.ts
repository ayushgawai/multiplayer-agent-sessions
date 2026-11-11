import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as Y from "yjs";
import type { Actor, ApiClient, SessionEventCreate } from "../lib/api";
import { BRIDGE_ORIGIN, attachBridge, fromBase64 } from "../lib/bridge";
import { BODY_FIELD } from "../lib/crdt";

const ACTOR: Actor = { kind: "human", id: "p_1", display_name: "Ada", role: "author" };
const REMOTE = Symbol("remote-peer");

function setup(debounceMs = 100): {
  doc: Y.Doc;
  posted: SessionEventCreate[];
  bridge: ReturnType<typeof attachBridge>;
} {
  const doc = new Y.Doc();
  const posted: SessionEventCreate[] = [];
  const client: Pick<ApiClient, "appendEvent"> = {
    appendEvent: (_sid, body) => {
      posted.push(body);
      return Promise.resolve({ event_id: "e", seq: posted.length });
    },
  };
  const bridge = attachBridge({
    doc,
    client,
    sessionId: "ses_1",
    actor: ACTOR,
    debounceMs,
    isRemote: (origin) => origin === REMOTE,
  });
  return { doc, posted, bridge };
}

function typeInto(doc: Y.Doc, text: string, origin: unknown = "local"): void {
  doc.transact(() => {
    const para = new Y.XmlElement("paragraph");
    para.insert(0, [new Y.XmlText(text)]);
    doc.getXmlFragment(BODY_FIELD).insert(0, [para]);
  }, origin);
}

describe("bridge", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("posts one doc_update for a local edit after the debounce", async () => {
    const { doc, posted, bridge } = setup();
    typeInto(doc, "hello");
    expect(posted).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(100);
    expect(posted).toHaveLength(1);
    const event = posted[0];
    expect(event?.type).toBe("doc_update");
    expect(event?.actor).toEqual(ACTOR);
    const update = fromBase64(String(event?.payload["update"]));
    const replay = new Y.Doc();
    Y.applyUpdate(replay, update);
    expect(replay.getXmlFragment(BODY_FIELD).toString()).toContain("hello");
    expect(event?.payload["bytes"]).toBe(update.length);
    bridge.destroy();
  });

  it("merges several quick edits into a single event", async () => {
    const { doc, posted, bridge } = setup();
    typeInto(doc, "a");
    await vi.advanceTimersByTimeAsync(50);
    typeInto(doc, "b");
    await vi.advanceTimersByTimeAsync(100);
    expect(posted).toHaveLength(1);
    const replay = new Y.Doc();
    Y.applyUpdate(replay, fromBase64(String(posted[0]?.payload["update"])));
    const text = replay.getXmlFragment(BODY_FIELD).toString();
    expect(text).toContain("a");
    expect(text).toContain("b");
    bridge.destroy();
  });

  it("does not post for remote-origin or bridge-origin updates", async () => {
    const { doc, posted, bridge } = setup();
    typeInto(doc, "from peer", REMOTE);
    typeInto(doc, "from bridge", BRIDGE_ORIGIN);
    await vi.advanceTimersByTimeAsync(500);
    expect(posted).toHaveLength(0);
    bridge.destroy();
  });

  it("an update applied from a peer is not logged, a following local edit is", async () => {
    const { doc, posted, bridge } = setup();
    const peer = new Y.Doc();
    typeInto(peer, "remote text");
    Y.applyUpdate(doc, Y.encodeStateAsUpdate(peer), REMOTE);
    await vi.advanceTimersByTimeAsync(500);
    expect(posted).toHaveLength(0);
    typeInto(doc, "mine");
    await vi.advanceTimersByTimeAsync(100);
    expect(posted).toHaveLength(1);
    bridge.destroy();
  });

  it("flush posts pending edits immediately and destroy stops logging", async () => {
    const { doc, posted, bridge } = setup(10_000);
    typeInto(doc, "now");
    await bridge.flush();
    expect(posted).toHaveLength(1);
    bridge.destroy();
    typeInto(doc, "after");
    await vi.advanceTimersByTimeAsync(20_000);
    expect(posted).toHaveLength(1);
  });
});
