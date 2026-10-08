import { describe, expect, it } from "vitest";
import { Awareness } from "y-protocols/awareness";
import * as Y from "yjs";
import { PALETTE, announce, buildPresenceState, colourFor } from "../lib/presence";

function luminance(hex: string): number {
  const channel = (i: number): number => {
    const v = Number.parseInt(hex.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}

describe("colours", () => {
  it("the same id always gives the same colour", () => {
    for (const id of ["p_1", "p_2", "ses-user-77"]) {
      const first = colourFor(id);
      for (let i = 0; i < 20; i += 1) {
        expect(colourFor(id)).toBe(first);
      }
    }
  });

  it("50 ids use every one of the 8 colours", () => {
    const used = new Set<string>();
    for (let i = 1; i <= 50; i += 1) {
      used.add(colourFor(`p_${i}`));
    }
    expect(PALETTE).toHaveLength(8);
    expect(used.size).toBe(8);
    for (const colour of used) {
      expect(PALETTE).toContain(colour);
    }
  });

  it("the palette is distinct and readable under white label text", () => {
    expect(new Set(PALETTE).size).toBe(8);
    for (const colour of PALETTE) {
      expect(1.05 / (luminance(colour) + 0.05)).toBeGreaterThanOrEqual(4.5);
    }
  });
});

describe("awareness state", () => {
  it("carries participant id, name, role and colour", () => {
    const awareness = new Awareness(new Y.Doc());
    const state = announce(awareness, {
      participantId: "p_3",
      displayName: "Cy",
      role: "reviewer",
    });
    const local = awareness.getLocalState();
    expect(local).toMatchObject({
      participant_id: "p_3",
      display_name: "Cy",
      role: "reviewer",
      colour: colourFor("p_3"),
    });
    expect(state.user).toEqual({ name: "Cy", color: colourFor("p_3") });
    awareness.destroy();
  });

  it("gives the same colour after a reconnect", () => {
    const info = { participantId: "p_9", displayName: "Di", role: "author" as const };
    expect(buildPresenceState(info).colour).toBe(buildPresenceState(info).colour);
  });
});
