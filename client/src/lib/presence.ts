import type { Awareness } from "y-protocols/awareness";
import type { ParticipantRole } from "./api";
import { ROLES } from "./session";

/**
 * Eight colours, each at least 4.5:1 against white so the cursor label text
 * stays readable. Order is fixed: a participant's colour depends on it.
 */
export const PALETTE: readonly string[] = [
  "#b3261e",
  "#1a56db",
  "#1b7a3a",
  "#7b2cbf",
  "#a14a00",
  "#00707a",
  "#a1245f",
  "#4a5568",
];

/**
 * Stable colour for a participant. The hash input is the display name, trimmed
 * and lowercased, not the participant id: rejoining a session issues a new id,
 * but the same person keeps the same colour. Two people who pick the same name
 * share a colour; the id still tells them apart everywhere else.
 */
export function colourFor(displayName: string): string {
  const key = displayName.trim().toLowerCase();
  let hash = 0x811c9dc5;
  for (let i = 0; i < key.length; i += 1) {
    hash ^= key.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return PALETTE[hash % PALETTE.length] ?? PALETTE[0] ?? "#4a5568";
}

export interface PresenceInfo {
  participantId: string;
  displayName: string;
  role: ParticipantRole;
}

/** What each tab publishes through awareness. `user` is what the cursor extension reads. */
export interface PresenceState {
  participant_id: string;
  display_name: string;
  role: ParticipantRole;
  colour: string;
  user: { name: string; color: string };
}

export interface PresenceEntry {
  participantId: string;
  displayName: string;
  role: ParticipantRole;
  colour: string;
  isSelf: boolean;
}

export function buildPresenceState(info: PresenceInfo): PresenceState {
  const colour = colourFor(info.displayName);
  return {
    participant_id: info.participantId,
    display_name: info.displayName,
    role: info.role,
    colour,
    user: { name: info.displayName, color: colour },
  };
}

/** Publish this tab's presence. Kept in memory by awareness; nothing is stored. */
export function announce(awareness: Awareness, info: PresenceInfo): PresenceState {
  const state = buildPresenceState(info);
  awareness.setLocalState(state);
  return state;
}

function isRole(value: unknown): value is ParticipantRole {
  return typeof value === "string" && (ROLES as readonly string[]).includes(value);
}

function asEntry(state: Record<string, unknown>, selfId: string | null): PresenceEntry | null {
  const id = state["participant_id"];
  const name = state["display_name"];
  const role = state["role"];
  const colour = state["colour"];
  if (
    typeof id !== "string" ||
    typeof name !== "string" ||
    !isRole(role) ||
    typeof colour !== "string"
  ) {
    return null;
  }
  return { participantId: id, displayName: name, role, colour, isSelf: id === selfId };
}

/** Everyone currently present, one entry per participant, sorted by name. */
export function readPresence(awareness: Awareness): PresenceEntry[] {
  const local = awareness.getLocalState();
  const selfRaw = local?.["participant_id"];
  const selfId = typeof selfRaw === "string" ? selfRaw : null;
  const byId = new Map<string, PresenceEntry>();
  for (const state of awareness.getStates().values()) {
    const entry = asEntry(state, selfId);
    if (entry !== null && !byId.has(entry.participantId)) {
      byId.set(entry.participantId, entry);
    }
  }
  return [...byId.values()].sort(
    (a, b) =>
      a.displayName.localeCompare(b.displayName) || a.participantId.localeCompare(b.participantId),
  );
}

/** Call `onChange` whenever the set of awareness states changes. */
export function subscribePresence(
  awareness: Awareness,
  onChange: (entries: PresenceEntry[]) => void,
): () => void {
  const handler = (): void => onChange(readPresence(awareness));
  awareness.on("change", handler);
  return () => awareness.off("change", handler);
}
