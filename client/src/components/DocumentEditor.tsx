import { EditorContent, useEditor } from "@tiptap/react";
import type { ApiClient } from "../lib/api";
import type { CollabDoc, CollabStatus } from "../lib/crdt";
import { buildEditorOptions } from "../lib/editorConfig";
import type { PresenceState } from "../lib/presence";
import { canWrite, type Identity } from "../lib/session";
import { useCollab } from "../lib/useCollab";
import { usePresence } from "../lib/usePresence";
import { PresenceBar } from "./PresenceBar";

const STATUS_TEXT: Record<CollabStatus, string> = {
  local: "local only (mock)",
  connecting: "connecting",
  connected: "synced",
  offline: "offline, edits kept locally",
};

interface EditorProps {
  collab: CollabDoc;
  presence: PresenceState;
  identity: Identity;
}

function Editor({ collab, presence, identity }: EditorProps): JSX.Element {
  const editor = useEditor(buildEditorOptions(collab, presence, identity.role), [
    collab,
    presence,
    identity.role,
  ]);
  return <EditorContent editor={editor} className="editor" />;
}

interface Props {
  client: ApiClient;
  identity: Identity;
}

export function DocumentEditor({ client, identity }: Props): JSX.Element {
  const { doc, presence, status, error } = useCollab(client, identity);
  const entries = usePresence(doc?.awareness ?? null);
  const editable = canWrite(identity.role);

  return (
    <section className="card">
      <h2>
        Document <span className={`badge badge-collab-${status}`}>{STATUS_TEXT[status]}</span>
      </h2>
      <PresenceBar entries={entries} />
      {!editable && <p className="muted">Observers can read the document but not edit it.</p>}
      {doc !== null && presence !== null && (
        <Editor collab={doc} presence={presence} identity={identity} />
      )}
      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
