import type { ApiClient, SessionEvent } from "./api";

const PAGE_LIMIT = 1000;

function seqOf(event: SessionEvent): number {
  return event.seq ?? 0;
}

/** Stable fingerprint of an event list; equal lists give equal strings. */
export function eventsSignature(events: readonly SessionEvent[]): string {
  return events.map((e) => `${seqOf(e)}:${e.event_id}`).join("|");
}

/**
 * Add one streamed event. A seq that already exists with the same id is a
 * duplicate. A seq that exists with a different id means the log was rolled
 * back and re-written, so the stale tail is dropped first.
 */
export function appendLive(
  events: readonly SessionEvent[],
  incoming: SessionEvent,
): SessionEvent[] {
  const seq = seqOf(incoming);
  const clash = events.find((e) => seqOf(e) === seq);
  if (clash !== undefined && clash.event_id === incoming.event_id) {
    return [...events];
  }
  const kept = events.filter((e) => seqOf(e) < seq);
  return [...kept, incoming];
}

/**
 * Combine a full server read with events that arrived on the stream while
 * that read was in flight. The server read wins for every seq it contains;
 * live events are kept only if they extend past it.
 */
export function mergeServerWithLive(
  server: readonly SessionEvent[],
  live: readonly SessionEvent[],
): SessionEvent[] {
  const maxServer = server.reduce((m, e) => Math.max(m, seqOf(e)), 0);
  const ahead = live
    .filter((e) => seqOf(e) > maxServer)
    .sort((a, b) => seqOf(a) - seqOf(b));
  const result = [...server];
  for (const event of ahead) {
    const last = result[result.length - 1];
    if (last === undefined || seqOf(event) > seqOf(last)) {
      result.push(event);
    }
  }
  return result;
}

/** Read the whole log, following next_seq across pages. */
export async function fetchAllEvents(
  client: ApiClient,
  sessionId: string,
): Promise<SessionEvent[]> {
  const all: SessionEvent[] = [];
  let since = 0;
  for (;;) {
    const page = await client.listEvents(sessionId, since, PAGE_LIMIT);
    all.push(...page.events);
    if (page.events.length < PAGE_LIMIT) {
      return all;
    }
    since = page.next_seq - 1;
  }
}

function asText(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

/** One line of text for the event list. */
export function describeEvent(event: SessionEvent): string {
  const payload = event.payload;
  switch (event.type) {
    case "instruction":
      return asText(payload["text"]) ?? "(no text)";
    case "join":
      return `joined as ${asText(payload["role"]) ?? event.actor.role}`;
    case "doc_update": {
      const bytes = payload["bytes"];
      return typeof bytes === "number" ? `document edit (${bytes} bytes)` : "document edit";
    }
    case "rejected": {
      const attempted = asText(payload["attempted_type"]) ?? "event";
      const reason = asText(payload["reason"]) ?? "rejected";
      return `${attempted} rejected: ${reason}`;
    }
    default:
      return JSON.stringify(payload);
  }
}
