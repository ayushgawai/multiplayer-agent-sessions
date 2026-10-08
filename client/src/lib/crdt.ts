import { WebsocketProvider } from "y-websocket";
import * as Y from "yjs";

export const DEFAULT_CRDT_URL = "ws://localhost:1234/crdt";
export const BODY_FIELD = "body";
export const META_FIELD = "meta";

export interface CrdtEnv {
  VITE_CRDT_URL?: string | undefined;
  VITE_USE_MOCK?: string | undefined;
}

export type CollabStatus = "local" | "connecting" | "connected" | "offline";

/** Base URL of the CRDT server, without a trailing slash. */
export function crdtServerUrl(env: CrdtEnv): string {
  const raw = env.VITE_CRDT_URL;
  const base = raw === undefined || raw.trim() === "" ? DEFAULT_CRDT_URL : raw.trim();
  return base.replace(/\/+$/, "");
}

/** Full room URL the provider connects to for one session. */
export function crdtRoomUrl(env: CrdtEnv, sessionId: string): string {
  return `${crdtServerUrl(env)}/${encodeURIComponent(sessionId)}`;
}

export interface CollabDoc {
  doc: Y.Doc;
  body: Y.XmlFragment;
  meta: Y.Map<unknown>;
  /** Null in mock mode: the document is local only. */
  provider: WebsocketProvider | null;
  /** True for updates that came from the server rather than this tab. */
  isRemote: (origin: unknown) => boolean;
  onStatus: (listener: (status: CollabStatus) => void) => () => void;
  destroy: () => void;
}

export interface CollabOptions {
  env: CrdtEnv;
  sessionId: string;
  /** Set false in tests to build the provider without opening a socket. */
  connect?: boolean;
}

/**
 * One Y.Doc per session: a Y.XmlFragment "body" and a Y.Map "meta". In mock
 * mode there is no provider and nothing leaves the tab. The broadcast channel
 * is off so the CRDT server is the only path between tabs.
 */
export function createCollabDoc(options: CollabOptions): CollabDoc {
  const { env, sessionId, connect = true } = options;
  const doc = new Y.Doc();
  const body = doc.getXmlFragment(BODY_FIELD);
  const meta = doc.getMap<unknown>(META_FIELD);
  meta.set("sessionId", sessionId);

  if (env.VITE_USE_MOCK === "true") {
    return {
      doc,
      body,
      meta,
      provider: null,
      isRemote: () => false,
      onStatus: (listener) => {
        listener("local");
        return () => undefined;
      },
      destroy: () => doc.destroy(),
    };
  }

  const provider = new WebsocketProvider(crdtServerUrl(env), sessionId, doc, {
    connect,
    disableBc: true,
  });
  return {
    doc,
    body,
    meta,
    provider,
    isRemote: (origin) => origin === provider,
    onStatus: (listener) => {
      const handler = ({ status }: { status: string }): void => {
        listener(status === "connected" ? "connected" : status === "connecting" ? "connecting" : "offline");
      };
      provider.on("status", handler);
      listener(provider.wsconnected ? "connected" : provider.shouldConnect ? "connecting" : "offline");
      return () => provider.off("status", handler);
    },
    destroy: () => {
      provider.destroy();
      doc.destroy();
    },
  };
}
