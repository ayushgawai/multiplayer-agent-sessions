import { useState, type FormEvent } from "react";
import type { ApiClient, ParticipantRole } from "../lib/api";
import { ROLES, errorMessage, type Identity } from "../lib/session";

interface Props {
  client: ApiClient;
  onJoined: (identity: Identity) => void;
}

export function Lobby({ client, onJoined }: Props): JSX.Element {
  const [title, setTitle] = useState("Design review");
  const [created, setCreated] = useState<{ id: string; code: string } | null>(null);
  const [sessionId, setSessionId] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<ParticipantRole>("author");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const create = (e: FormEvent): void => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    client
      .createSession({ title: title.trim() })
      .then((res) => {
        setCreated({ id: res.session_id, code: res.join_code });
        setSessionId(res.session_id);
        setJoinCode(res.join_code);
      })
      .catch((err: unknown) => setError(errorMessage(err)))
      .finally(() => setBusy(false));
  };

  const join = (e: FormEvent): void => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const id = sessionId.trim();
    const code = joinCode.trim();
    const displayName = name.trim();
    client
      .joinSession(id, { join_code: code, display_name: displayName, role })
      .then((res) =>
        onJoined({
          sessionId: id,
          joinCode: code,
          participantId: res.participant_id,
          displayName,
          role,
        }),
      )
      .catch((err: unknown) => setError(errorMessage(err)))
      .finally(() => setBusy(false));
  };

  return (
    <div className="lobby">
      <section className="card">
        <h2>Create a session</h2>
        <form onSubmit={create}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <button type="submit" disabled={busy || title.trim() === ""}>
            Create session
          </button>
        </form>
        {created !== null && (
          <dl className="created">
            <dt>Session id</dt>
            <dd>
              <code>{created.id}</code>
            </dd>
            <dt>Join code</dt>
            <dd>
              <code className="join-code">{created.code}</code>
            </dd>
          </dl>
        )}
      </section>

      <section className="card">
        <h2>Join a session</h2>
        <form onSubmit={join}>
          <label>
            Session id
            <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} required />
          </label>
          <label>
            Join code
            <input value={joinCode} onChange={(e) => setJoinCode(e.target.value)} required />
          </label>
          <label>
            Display name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Role
            <select value={role} onChange={(e) => setRole(e.target.value as ParticipantRole)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy || name.trim() === ""}>
            Join session
          </button>
        </form>
      </section>

      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
