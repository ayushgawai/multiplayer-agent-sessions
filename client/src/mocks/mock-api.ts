import type {
  ApiClient,
  SessionEvent,
  SessionEventCreate,
  StreamHandlers,
} from "../lib/api";
import { ApiError } from "../lib/errors";

interface MockParticipant {
  id: string;
  displayName: string;
  role: "author" | "reviewer" | "observer";
}

interface MockSession {
  id: string;
  title: string;
  joinCode: string;
  nextSeq: number;
  events: SessionEvent[];
  participants: MockParticipant[];
}

type Listener = (event: SessionEvent) => void;

// Module variables only: no browser storage. State lives for the page session.
const sessions = new Map<string, MockSession>();
const listeners = new Map<string, Set<Listener>>();
let sessionCounter = 0;
let eventCounter = 0;

const JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

/** Clear every mock session. Used by tests. */
export function resetMock(): void {
  sessions.clear();
  listeners.clear();
  sessionCounter = 0;
  eventCounter = 0;
}

function makeJoinCode(): string {
  let code = "";
  for (let i = 0; i < 6; i += 1) {
    const idx = Math.floor(Math.random() * JOIN_CODE_ALPHABET.length);
    code += JOIN_CODE_ALPHABET.charAt(idx);
  }
  return code;
}

function nextEventId(): string {
  eventCounter += 1;
  return `evt_mock_${eventCounter}`;
}

function requireSession(sessionId: string): MockSession {
  const session = sessions.get(sessionId);
  if (session === undefined) {
    throw new ApiError(404, "session not found");
  }
  return session;
}

function publish(session: MockSession, event: SessionEvent): void {
  session.events.push(event);
  const subs = listeners.get(session.id);
  if (subs !== undefined) {
    for (const fn of [...subs]) {
      fn(event);
    }
  }
}

/** Allocate the next seq and store the event, as the real service does. */
function record(
  session: MockSession,
  body: SessionEventCreate,
  type: SessionEvent["type"],
  payload: SessionEvent["payload"],
): SessionEvent {
  const event: SessionEvent = {
    event_id: body.event_id ?? nextEventId(),
    session_id: session.id,
    seq: session.nextSeq,
    ts: new Date().toISOString(),
    actor: body.actor,
    type,
    payload,
    causality: body.causality ?? {},
    labels: null,
  };
  session.nextSeq += 1;
  publish(session, event);
  return event;
}

export function createMockClient(): ApiClient {
  return {
    mode: "mock",
    label: "mock (in memory, this tab only)",

    createSession: async (req) => {
      sessionCounter += 1;
      const session: MockSession = {
        id: `ses_mock_${sessionCounter}`,
        title: req.title,
        joinCode: makeJoinCode(),
        nextSeq: 1,
        events: [],
        participants: [],
      };
      sessions.set(session.id, session);
      return { session_id: session.id, join_code: session.joinCode };
    },

    joinSession: async (sessionId, req) => {
      const session = requireSession(sessionId);
      if (req.join_code !== session.joinCode) {
        throw new ApiError(403, "invalid join_code");
      }
      const participant: MockParticipant = {
        id: `p_${session.participants.length + 1}`,
        displayName: req.display_name,
        role: req.role,
      };
      session.participants.push(participant);
      record(
        session,
        {
          actor: {
            kind: "human",
            id: participant.id,
            display_name: participant.displayName,
            role: participant.role,
          },
          type: "join",
          payload: {},
        },
        "join",
        { display_name: participant.displayName, role: participant.role },
      );
      return {
        participant_id: participant.id,
        snapshot: snapshotOf(session, session.nextSeq - 1),
        catchup_summary: null,
      };
    },

    listEvents: async (sessionId, since = 0, limit = 100) => {
      const session = requireSession(sessionId);
      const events = session.events
        .filter((e) => (e.seq ?? 0) > since)
        .slice(0, limit);
      const last = events[events.length - 1];
      const nextSeq = last?.seq != null ? last.seq + 1 : session.nextSeq;
      return { events, next_seq: nextSeq };
    },

    appendEvent: async (sessionId, body) => {
      const session = requireSession(sessionId);
      let type = body.type;
      let payload = body.payload;
      if (body.actor.kind === "human") {
        const known = session.participants.find((p) => p.id === body.actor.id);
        let reason: string | null = null;
        if (known === undefined) {
          reason = "unknown participant";
        } else if (known.role === "observer") {
          reason = `role ${known.role} cannot append ${body.type}`;
        }
        if (reason !== null) {
          type = "rejected";
          payload = {
            attempted_type: body.type,
            reason,
            attempted_payload: body.payload,
          };
        }
      }
      const event = record(session, body, type, payload);
      return { event_id: event.event_id, seq: event.seq ?? 0 };
    },

    rollback: async (sessionId, toSeq) => {
      const session = requireSession(sessionId);
      if (toSeq < 0) {
        throw new ApiError(400, "to_seq must be >= 0");
      }
      const rolled = session.events.filter((e) => (e.seq ?? 0) > toSeq);
      session.events = session.events.filter((e) => (e.seq ?? 0) <= toSeq);
      session.nextSeq = toSeq + 1;
      // Like the real service, rollback is not published on the stream.
      return {
        snapshot: snapshotOf(session, toSeq),
        rolled_back_events: rolled,
      };
    },

    healthz: async () => ({ ok: true, version: "mock" }),

    openStream: (sessionId, handlers: StreamHandlers) => {
      let open = true;
      const session = sessions.get(sessionId);
      if (session === undefined) {
        queueMicrotask(() => handlers.onClose("stream closed (4404)"));
        return { close: () => undefined };
      }
      const fn: Listener = (event) => {
        if (open) {
          handlers.onEvent(event);
        }
      };
      let subs = listeners.get(sessionId);
      if (subs === undefined) {
        subs = new Set();
        listeners.set(sessionId, subs);
      }
      subs.add(fn);
      queueMicrotask(() => {
        if (open) {
          handlers.onOpen();
        }
      });
      return {
        close: () => {
          open = false;
          listeners.get(sessionId)?.delete(fn);
        },
      };
    },
  };
}

function snapshotOf(
  session: MockSession,
  toSeq: number,
): Record<string, unknown> {
  return {
    session_id: session.id,
    title: session.title,
    to_seq: toSeq,
    event_count: session.events.filter((e) => (e.seq ?? 0) <= toSeq).length,
  };
}
