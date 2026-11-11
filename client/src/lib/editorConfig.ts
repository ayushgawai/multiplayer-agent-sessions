import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";
import type { EditorOptions } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import type { CollabDoc } from "./crdt";
import { BODY_FIELD } from "./crdt";
import type { PresenceState } from "./presence";
import { canWrite } from "./session";
import type { ParticipantRole } from "./api";

/**
 * Editor options for one participant. History is off because undo comes from
 * Yjs. Observers get a read-only editor. In mock mode there is no provider, so
 * the cursor extension is given the local awareness directly.
 */
export function buildEditorOptions(
  collab: CollabDoc,
  presence: PresenceState,
  role: ParticipantRole,
): Partial<EditorOptions> {
  return {
    extensions: [
      StarterKit.configure({ history: false }),
      Collaboration.configure({ document: collab.doc, field: BODY_FIELD }),
      CollaborationCursor.configure({
        provider: collab.provider ?? { awareness: collab.awareness },
        user: presence.user,
      }),
    ],
    editable: canWrite(role),
  };
}
