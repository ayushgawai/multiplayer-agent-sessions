import type { ParticipantRole } from "./api";

/** Who this tab is acting as after a successful join. */
export interface Identity {
  sessionId: string;
  joinCode: string;
  participantId: string;
  displayName: string;
  role: ParticipantRole;
}

export const ROLES: readonly ParticipantRole[] = [
  "author",
  "reviewer",
  "observer",
];

/** Roles the service lets append events; observers are rejected. */
export function canWrite(role: ParticipantRole): boolean {
  return role !== "observer";
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
