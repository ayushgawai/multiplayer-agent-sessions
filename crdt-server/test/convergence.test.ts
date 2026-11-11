import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { WebSocket } from "ws";
import { WebsocketProvider } from "y-websocket";
import * as Y from "yjs";
import { docNameFromUrl, startCrdtServer, type CrdtServer } from "../src/server.js";

interface Peer {
  doc: Y.Doc;
  provider: WebsocketProvider;
}

type ProviderOptions = NonNullable<ConstructorParameters<typeof WebsocketProvider>[3]>;

function connect(port: number, room: string): Peer {
  const doc = new Y.Doc();
  const provider = new WebsocketProvider(`ws://127.0.0.1:${port}/crdt`, room, doc, {
    WebSocketPolyfill: WebSocket as unknown as ProviderOptions["WebSocketPolyfill"],
    disableBc: true,
  });
  return { doc, provider };
}

function whenSynced(peer: Peer): Promise<void> {
  return new Promise((resolve) => {
    if (peer.provider.synced) {
      resolve();
      return;
    }
    peer.provider.once("sync", () => resolve());
  });
}

async function until(check: () => boolean, ms = 3000): Promise<void> {
  const end = Date.now() + ms;
  while (!check()) {
    if (Date.now() > end) {
      throw new Error("timed out waiting for convergence");
    }
    await new Promise((r) => setTimeout(r, 20));
  }
}

describe("crdt-server", () => {
  let server: CrdtServer;
  const peers: Peer[] = [];

  beforeEach(async () => {
    server = await startCrdtServer(0, "127.0.0.1");
  });

  afterEach(async () => {
    for (const p of peers.splice(0)) {
      p.provider.destroy();
      p.doc.destroy();
    }
    await server.close();
  });

  it("serves /healthz", async () => {
    const res = await fetch(`http://127.0.0.1:${server.port}/healthz`);
    const body = (await res.json()) as { ok: boolean; version: string };
    expect(body.ok).toBe(true);
    expect(body.version.length).toBeGreaterThan(0);
  });

  it("two clients in one room converge", async () => {
    const a = connect(server.port, "ses_1");
    const b = connect(server.port, "ses_1");
    peers.push(a, b);
    await Promise.all([whenSynced(a), whenSynced(b)]);

    a.doc.getText("t").insert(0, "hello");
    await until(() => b.doc.getText("t").toString() === "hello");
    b.doc.getText("t").insert(5, " world");
    await until(() => a.doc.getText("t").toString() === "hello world");
    expect(a.doc.getText("t").toString()).toBe(b.doc.getText("t").toString());
  });

  it("keeps rooms separate and gives late joiners the state", async () => {
    const a = connect(server.port, "ses_a");
    const other = connect(server.port, "ses_b");
    peers.push(a, other);
    await Promise.all([whenSynced(a), whenSynced(other)]);
    a.doc.getText("t").insert(0, "only in a");
    await until(() => server.port > 0 && a.provider.synced);
    const late = connect(server.port, "ses_a");
    peers.push(late);
    await whenSynced(late);
    await until(() => late.doc.getText("t").toString() === "only in a");
    expect(other.doc.getText("t").toString()).toBe("");
  });
});

describe("docNameFromUrl", () => {
  it("accepts /crdt/{id} and rejects other paths", () => {
    expect(docNameFromUrl("/crdt/ses_1")).toBe("ses_1");
    expect(docNameFromUrl("/crdt/ses_1?x=1")).toBe("ses_1");
    expect(docNameFromUrl("/crdt/")).toBeNull();
    expect(docNameFromUrl("/other/ses_1")).toBeNull();
    expect(docNameFromUrl("/crdt/a b")).toBeNull();
    expect(docNameFromUrl(undefined)).toBeNull();
  });
});
