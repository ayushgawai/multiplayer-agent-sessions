import * as Y from "yjs";
import type { Actor, ApiClient } from "./api";

/** Origin for transactions the bridge itself applies; never logged. */
export const BRIDGE_ORIGIN: unique symbol = Symbol("session-bridge");

const DEFAULT_DEBOUNCE_MS = 800;

export interface BridgeOptions {
  doc: Y.Doc;
  client: Pick<ApiClient, "appendEvent">;
  sessionId: string;
  actor: Actor;
  debounceMs?: number;
  /** True when an update came from the server rather than this tab. */
  isRemote?: (origin: unknown) => boolean;
  onError?: (error: unknown) => void;
}

export interface Bridge {
  /** Post any pending local edits now. */
  flush: () => Promise<void>;
  destroy: () => void;
}

export function toBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

export function fromBase64(text: string): Uint8Array {
  const binary = atob(text);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    out[i] = binary.charCodeAt(i);
  }
  return out;
}

/**
 * Turn debounced local Yjs changes into one doc_update SessionEvent. Updates
 * whose origin is the bridge or a remote peer are skipped, so a change is
 * logged only by the tab that made it.
 */
export function attachBridge(options: BridgeOptions): Bridge {
  const { doc, client, sessionId, actor } = options;
  const debounceMs = options.debounceMs ?? DEFAULT_DEBOUNCE_MS;
  const isRemote = options.isRemote ?? (() => false);
  let pending: Uint8Array[] = [];
  let timer: ReturnType<typeof setTimeout> | null = null;
  let destroyed = false;

  const onUpdate = (update: Uint8Array, origin: unknown): void => {
    if (destroyed || origin === BRIDGE_ORIGIN || isRemote(origin)) {
      return;
    }
    pending.push(update);
    if (timer !== null) {
      clearTimeout(timer);
    }
    timer = setTimeout(() => void flush(), debounceMs);
  };

  const flush = async (): Promise<void> => {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
    if (pending.length === 0) {
      return;
    }
    const merged = Y.mergeUpdates(pending);
    pending = [];
    try {
      await client.appendEvent(sessionId, {
        actor,
        type: "doc_update",
        payload: {
          encoding: "yjs-update-v1",
          update: toBase64(merged),
          bytes: merged.length,
        },
      });
    } catch (err) {
      options.onError?.(err);
    }
  };

  doc.on("update", onUpdate);
  return {
    flush,
    destroy: () => {
      doc.off("update", onUpdate);
      const last = flush();
      destroyed = true;
      void last;
    },
  };
}
