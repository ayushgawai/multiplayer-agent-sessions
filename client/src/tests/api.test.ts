import { describe, expect, it } from "vitest";
import type { components } from "../lib/api-types";
import { createApiClient, streamUrl } from "../lib/api";

describe("api client selection", () => {
  it("uses the mock when VITE_USE_MOCK is true", async () => {
    const client = createApiClient({ VITE_USE_MOCK: "true", VITE_API_BASE: "http://x" });
    expect(client.mode).toBe("mock");
    const health = await client.healthz();
    expect(health.version).toBe("mock");
  });

  it("uses the real client otherwise and keeps the base", () => {
    const client = createApiClient({ VITE_API_BASE: "http://localhost:8000/" });
    expect(client.mode).toBe("real");
    expect(client.label).toBe("http://localhost:8000");
    expect(createApiClient({}).label).toContain("dev proxy");
  });
});

describe("stream url", () => {
  it("maps http to ws and https to wss", () => {
    const page = { protocol: "http:", host: "localhost:5173" };
    expect(streamUrl("http://h:8000", "s1", page)).toBe("ws://h:8000/v1/sessions/s1/stream");
    expect(streamUrl("https://h", "s1", page)).toBe("wss://h/v1/sessions/s1/stream");
    expect(streamUrl("", "s1", page)).toBe("ws://localhost:5173/v1/sessions/s1/stream");
    expect(streamUrl("", "s1", { protocol: "https:", host: "a" })).toBe("wss://a/v1/sessions/s1/stream");
  });
});

describe("generated types", () => {
  it("compile against the schema names used by the app", () => {
    const req: components["schemas"]["JoinSessionRequest"] = {
      join_code: "ABC123",
      display_name: "Ada",
      role: "reviewer",
    };
    const kind: components["schemas"]["EventType"] = "instruction";
    expect(req.role).toBe("reviewer");
    expect(kind).toBe("instruction");
  });
});
