import Collaboration from "@tiptap/extension-collaboration";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import type { ApiClient } from "../lib/api";
import type { CollabDoc, CollabStatus } from "../lib/crdt";
import { BODY_FIELD } from "../lib/crdt";
import { canWrite, type Identity } from "../lib/session";
import { useCollab } from "../lib/useCollab";

const STATUS_TEXT: Record<CollabStatus, string> = {
  local: "local only (mock)",
  connecting: "connecting",
  connected: "synced",
  offline: "offline, edits kept locally",
};

function Editor({ collab, editable }: { collab: CollabDoc; editable: boolean }): JSX.Element {
  const editor = useEditor(
    {
      extensions: [
        // History is off: undo/redo must come from Yjs, not the local stack.
        StarterKit.configure({ history: false }),
        Collaboration.configure({ document: collab.doc, field: BODY_FIELD }),
      ],
      editable,
    },
    [collab, editable],
  );
  return <EditorContent editor={editor} className="editor" />;
}

interface Props {
  client: ApiClient;
  identity: Identity;
}

export function DocumentEditor({ client, identity }: Props): JSX.Element {
  const { doc, status, error } = useCollab(client, identity);
  const editable = canWrite(identity.role);

  return (
    <section className="card">
      <h2>
        Document <span className={`badge badge-collab-${status}`}>{STATUS_TEXT[status]}</span>
      </h2>
      {!editable && <p className="muted">Observers can read the document but not edit it.</p>}
      {doc !== null && <Editor collab={doc} editable={editable} />}
      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
