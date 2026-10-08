import { useEffect, useState } from "react";
import type { ApiClient } from "./api";
import { attachBridge } from "./bridge";
import { createCollabDoc, type CollabDoc, type CollabStatus } from "./crdt";
import { announce, type PresenceState } from "./presence";
import { canWrite, type Identity } from "./session";

export interface Collab {
  doc: CollabDoc | null;
  /** This tab's published presence (name, role, colour). */
  presence: PresenceState | null;
  status: CollabStatus;
  error: string | null;
}

/** Create the session's Y.Doc and provider, and bridge edits to the event log. */
export function useCollab(client: ApiClient, identity: Identity): Collab {
  const [doc, setDoc] = useState<CollabDoc | null>(null);
  const [status, setStatus] = useState<CollabStatus>("connecting");
  const [error, setError] = useState<string | null>(null);
  const [presence, setPresence] = useState<PresenceState | null>(null);

  useEffect(() => {
    const collab = createCollabDoc({
      env: { ...import.meta.env, VITE_USE_MOCK: client.mode === "mock" ? "true" : undefined },
      sessionId: identity.sessionId,
    });
    const bridge = canWrite(identity.role)
      ? attachBridge({
          doc: collab.doc,
          client,
          sessionId: identity.sessionId,
          actor: {
            kind: "human",
            id: identity.participantId,
            display_name: identity.displayName,
            role: identity.role,
          },
          isRemote: collab.isRemote,
          onError: (err) => setError(err instanceof Error ? err.message : String(err)),
        })
      : null;
    const offStatus = collab.onStatus(setStatus);
    setPresence(
      announce(collab.awareness, {
        participantId: identity.participantId,
        displayName: identity.displayName,
        role: identity.role,
      }),
    );
    setDoc(collab);
    return () => {
      offStatus();
      bridge?.destroy();
      collab.destroy();
      setDoc(null);
      setPresence(null);
    };
  }, [client, identity]);

  return { doc, presence, status, error };
}
