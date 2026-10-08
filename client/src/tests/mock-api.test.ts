import { beforeEach, describe, expect, it } from "vitest";
import type { ApiClient, SessionEventCreate } from "../lib/api";
import { createMockClient, resetMock } from "../mocks/mock-api";

function instruction(id: string, text: string, role: "author" | "observer" = "author"): SessionEventCreate {
  return {
    actor: { kind: "human", id, display_name: id, role },
    type: "instruction",
    payload: { text },
  };
}

async function setup(client: ApiClient): Promise<{ sid: string; pid: string }> {
  const { session_id, join_code } = await client.createSession({ title: "t" });
  const joined = await client.joinSession(session_id, {
    join_code,
    display_name: "Ada",
    role: "author",
  });
  return { sid: session_id, pid: joined.participant_id };
}

describe("mock backend", () => {
  let client: ApiClient;

  beforeEach(() => {
    resetMock();
    client = createMockClient();
  });

  it("assigns a monotonic gapless seq starting at 1", async () => {
    const { sid, pid } = await setup(client);
    for (let i = 0; i < 5; i += 1) {
      await client.appendEvent(sid, instruction(pid, `m${i}`));
    }
    const page = await client.listEvents(sid);
    const seqs = page.events.map((e) => e.seq);
    expect(seqs).toEqual([1, 2, 3, 4, 5, 6]);
    expect(page.next_seq).toBe(7);
  });

  it("rollback removes later events and returns them", async () => {
    const { sid, pid } = await setup(client);
    for (let i = 0; i < 4; i += 1) {
      await client.appendEvent(sid, instruction(pid, `m${i}`));
    }
    const res = await client.rollback(sid, 2);
    expect(res.rolled_back_events.map((e) => e.seq)).toEqual([3, 4, 5]);
    const page = await client.listEvents(sid);
    expect(page.events.map((e) => e.seq)).toEqual([1, 2]);
    const next = await client.appendEvent(sid, instruction(pid, "again"));
    expect(next.seq).toBe(3);
  });

  it("filters list_events by since", async () => {
    const { sid, pid } = await setup(client);
    await client.appendEvent(sid, instruction(pid, "a"));
    const page = await client.listEvents(sid, 1);
    expect(page.events.map((e) => e.seq)).toEqual([2]);
  });

  it("rejects a wrong join code and an unknown session", async () => {
    const { session_id } = await client.createSession({ title: "t" });
    await expect(
      client.joinSession(session_id, { join_code: "WRONG1", display_name: "x", role: "author" }),
    ).rejects.toMatchObject({ status: 403 });
    await expect(client.listEvents("missing")).rejects.toMatchObject({ status: 404 });
  });

  it("records observer writes as rejected events", async () => {
    const { session_id, join_code } = await client.createSession({ title: "t" });
    const obs = await client.joinSession(session_id, {
      join_code,
      display_name: "Obs",
      role: "observer",
    });
    await client.appendEvent(session_id, instruction(obs.participant_id, "hi", "observer"));
    const page = await client.listEvents(session_id);
    expect(page.events[1]?.type).toBe("rejected");
  });

  it("publishes appended events on the stream but not rollbacks", async () => {
    const { sid, pid } = await setup(client);
    const seen: number[] = [];
    const handle = client.openStream(sid, {
      onOpen: () => undefined,
      onEvent: (e) => seen.push(e.seq ?? 0),
      onClose: () => undefined,
    });
    await client.appendEvent(sid, instruction(pid, "a"));
    await client.rollback(sid, 1);
    handle.close();
    await client.appendEvent(sid, instruction(pid, "after close"));
    expect(seen).toEqual([2]);
  });
});
