import { useState, type FormEvent } from "react";
import type { ApiClient } from "../lib/api";
import { canWrite, errorMessage, type Identity } from "../lib/session";

interface Props {
  client: ApiClient;
  identity: Identity;
  onSent: () => void;
}

export function InstructionBox({ client, identity, onSent }: Props): JSX.Element {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const writable = canWrite(identity.role);

  const send = (e: FormEvent): void => {
    e.preventDefault();
    const body = text.trim();
    if (body === "") {
      return;
    }
    setBusy(true);
    setError(null);
    client
      .appendEvent(identity.sessionId, {
        actor: {
          kind: "human",
          id: identity.participantId,
          display_name: identity.displayName,
          role: identity.role,
        },
        type: "instruction",
        payload: { text: body },
      })
      .then(() => {
        setText("");
        onSent();
      })
      .catch((err: unknown) => setError(errorMessage(err)))
      .finally(() => setBusy(false));
  };

  return (
    <form className="card" onSubmit={send}>
      <h2>Send an instruction</h2>
      {!writable && (
        <p className="muted">Observers cannot send instructions; the service rejects them.</p>
      )}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        placeholder="Tell the team or the agent what to do"
        disabled={!writable}
      />
      <button type="submit" disabled={!writable || busy || text.trim() === ""}>
        Send instruction
      </button>
      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
