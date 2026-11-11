import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiClient, SessionEvent, StreamHandle } from "./api";
import {
  appendLive,
  eventsSignature,
  fetchAllEvents,
  mergeServerWithLive,
} from "./events";

export type FeedStatus = "connecting" | "stream" | "polling";

const RECONCILE_MS_STREAM = 3000;
const RECONCILE_MS_POLLING = 1500;
const RECONNECT_MS = 5000;

export interface SessionFeed {
  events: SessionEvent[];
  status: FeedStatus;
  error: string | null;
  /** Re-read the whole log now (used after a local rollback). */
  refresh: () => Promise<void>;
}

/**
 * Live event list. The stream gives low latency. A periodic full read keeps
 * the list correct when the stream is down and when another tab rolls the log
 * back, because the service does not publish rollbacks on the stream.
 */
export function useSessionEvents(
  client: ApiClient,
  sessionId: string,
): SessionFeed {
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [status, setStatus] = useState<FeedStatus>("connecting");
  const [error, setError] = useState<string | null>(null);
  const liveRef = useRef<SessionEvent[]>([]);
  const generationRef = useRef(0);

  const refresh = useCallback(async (): Promise<void> => {
    generationRef.current += 1;
    const generation = generationRef.current;
    liveRef.current = [];
    try {
      const server = await fetchAllEvents(client, sessionId);
      if (generation !== generationRef.current) {
        return;
      }
      const merged = mergeServerWithLive(server, liveRef.current);
      setEvents((prev) =>
        eventsSignature(prev) === eventsSignature(merged) ? prev : merged,
      );
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [client, sessionId]);

  useEffect(() => {
    let cancelled = false;
    let handle: StreamHandle | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;

    const connect = (): void => {
      if (cancelled) {
        return;
      }
      handle = client.openStream(sessionId, {
        onOpen: () => setStatus("stream"),
        onEvent: (event) => {
          liveRef.current.push(event);
          setEvents((prev) => appendLive(prev, event));
        },
        onClose: () => {
          if (cancelled) {
            return;
          }
          setStatus("polling");
          retry = setTimeout(connect, RECONNECT_MS);
        },
      });
    };

    setStatus("connecting");
    void refresh();
    connect();
    return () => {
      cancelled = true;
      if (retry !== null) {
        clearTimeout(retry);
      }
      handle?.close();
    };
  }, [client, sessionId, refresh]);

  useEffect(() => {
    const ms = status === "stream" ? RECONCILE_MS_STREAM : RECONCILE_MS_POLLING;
    const timer = setInterval(() => void refresh(), ms);
    return () => clearInterval(timer);
  }, [status, refresh]);

  return { events, status, error, refresh };
}
