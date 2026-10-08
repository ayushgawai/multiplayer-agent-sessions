import { createMockClient } from "../mocks/mock-api";
import type { components } from "./api-types";
import { ApiError } from "./errors";

type Schemas = components["schemas"];

export type SessionEvent = Schemas["SessionEvent"];
export type SessionEventCreate = Schemas["SessionEventCreate"];
export type CreateSessionRequest = Schemas["CreateSessionRequest"];
export type CreateSessionResponse = Schemas["CreateSessionResponse"];
export type JoinSessionRequest = Schemas["JoinSessionRequest"];
export type JoinSessionResponse = Schemas["JoinSessionResponse"];
export type EventsPage = Schemas["EventsPage"];
export type AppendEventResponse = Schemas["AppendEventResponse"];
export type RollbackResponse = Schemas["RollbackResponse"];
export type HealthResponse = Schemas["HealthResponse"];
export type ParticipantRole = Schemas["ParticipantRole"];
export type EventType = Schemas["EventType"];

export { ApiError };

export interface StreamHandlers {
  onOpen: () => void;
  onEvent: (event: SessionEvent) => void;
  /** Called once when the stream ends or cannot be opened. */
  onClose: (reason: string) => void;
}

export interface StreamHandle {
  close: () => void;
}

/** One typed surface for every route in session-service/openapi.json. */
export interface ApiClient {
  readonly mode: "mock" | "real";
  /** Human readable base shown in the header. */
  readonly label: string;
  createSession: (req: CreateSessionRequest) => Promise<CreateSessionResponse>;
  joinSession: (
    sessionId: string,
    req: JoinSessionRequest,
  ) => Promise<JoinSessionResponse>;
  listEvents: (
    sessionId: string,
    since?: number,
    limit?: number,
  ) => Promise<EventsPage>;
  appendEvent: (
    sessionId: string,
    body: SessionEventCreate,
  ) => Promise<AppendEventResponse>;
  rollback: (sessionId: string, toSeq: number) => Promise<RollbackResponse>;
  healthz: () => Promise<HealthResponse>;
  openStream: (sessionId: string, handlers: StreamHandlers) => StreamHandle;
}

export interface ClientEnv {
  VITE_API_BASE?: string | undefined;
  VITE_USE_MOCK?: string | undefined;
}

function trimBase(base: string): string {
  return base.replace(/\/+$/, "");
}

async function request<T>(
  base: string,
  method: "GET" | "POST",
  path: string,
  body?: unknown,
): Promise<T> {
  const init: RequestInit = { method };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  const res = await fetch(`${base}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = (await res.json()) as { detail?: unknown };
      if (typeof data.detail === "string") {
        detail = data.detail;
      } else if (data.detail !== undefined) {
        detail = JSON.stringify(data.detail);
      }
    } catch {
      // Keep the status text when the body is not JSON.
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

/** Build the WebSocket URL for the stream route. */
export function streamUrl(
  base: string,
  sessionId: string,
  page: { protocol: string; host: string },
): string {
  const path = `/v1/sessions/${encodeURIComponent(sessionId)}/stream`;
  if (base === "") {
    const scheme = page.protocol === "https:" ? "wss" : "ws";
    return `${scheme}://${page.host}${path}`;
  }
  return `${base.replace(/^http/, "ws")}${path}`;
}

export function createRealClient(rawBase: string): ApiClient {
  const base = trimBase(rawBase);
  const sid = (id: string): string => encodeURIComponent(id);
  return {
    mode: "real",
    label: base === "" ? "real API via dev proxy" : base,
    createSession: (req) =>
      request<CreateSessionResponse>(base, "POST", "/v1/sessions", req),
    joinSession: (sessionId, req) =>
      request<JoinSessionResponse>(
        base,
        "POST",
        `/v1/sessions/${sid(sessionId)}/join`,
        req,
      ),
    listEvents: (sessionId, since = 0, limit = 100) =>
      request<EventsPage>(
        base,
        "GET",
        `/v1/sessions/${sid(sessionId)}/events?since=${since}&limit=${limit}`,
      ),
    appendEvent: (sessionId, body) =>
      request<AppendEventResponse>(
        base,
        "POST",
        `/v1/sessions/${sid(sessionId)}/events`,
        body,
      ),
    rollback: (sessionId, toSeq) =>
      request<RollbackResponse>(
        base,
        "POST",
        `/v1/sessions/${sid(sessionId)}/rollback`,
        { to_seq: toSeq },
      ),
    healthz: () => request<HealthResponse>(base, "GET", "/healthz"),
    openStream: (sessionId, handlers) => {
      let finished = false;
      const finish = (reason: string): void => {
        if (!finished) {
          finished = true;
          handlers.onClose(reason);
        }
      };
      let socket: WebSocket;
      try {
        socket = new WebSocket(streamUrl(base, sessionId, window.location));
      } catch (err) {
        queueMicrotask(() => finish(String(err)));
        return { close: () => undefined };
      }
      socket.onopen = () => handlers.onOpen();
      socket.onmessage = (msg: MessageEvent<unknown>) => {
        if (typeof msg.data !== "string") {
          return;
        }
        try {
          handlers.onEvent(JSON.parse(msg.data) as SessionEvent);
        } catch {
          // Ignore frames that are not a SessionEvent.
        }
      };
      socket.onerror = () => finish("stream error");
      socket.onclose = (ev) => finish(`stream closed (${ev.code})`);
      return {
        close: () => {
          finished = true;
          socket.close();
        },
      };
    },
  };
}

/** Pick the mock or the real client from build-time env values. */
export function createApiClient(env: ClientEnv): ApiClient {
  if (env.VITE_USE_MOCK === "true") {
    return createMockClient();
  }
  return createRealClient(env.VITE_API_BASE ?? "");
}

let shared: ApiClient | undefined;

/** Client for the running app, built once from import.meta.env. */
export function getApiClient(): ApiClient {
  shared ??= createApiClient(import.meta.env);
  return shared;
}
