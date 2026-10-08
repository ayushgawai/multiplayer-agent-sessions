import { useState } from "react";
import type { ApiClient, SessionEvent } from "../lib/api";
import { canWrite, errorMessage, type Identity } from "../lib/session";

interface Props {
  client: ApiClient;
  identity: Identity;
  events: SessionEvent[];
  onRolledBack: () => void;
}

export function RollbackPanel({ client, identity, events, onRolledBack }: Props): JSX.Element {
  const [target, setTarget] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const toSeq = Number.parseInt(target, 10);
  const valid = Number.isInteger(toSeq) && toSeq >= 0;
  const removed = valid ? events.filter((e) => (e.seq ?? 0) > toSeq).length : 0;
  const writable = canWrite(identity.role);

  const run = (): void => {
    setBusy(true);
    setError(null);
    client
      .rollback(identity.sessionId, toSeq)
      .then((res) => {
        setNotice(`Rolled back to seq ${toSeq}; removed ${res.rolled_back_events.length} events.`);
        setConfirming(false);
        setTarget("");
        onRolledBack();
      })
      .catch((err: unknown) => setError(errorMessage(err)))
      .finally(() => setBusy(false));
  };

  return (
    <section className="card">
      <h2>Rollback</h2>
      <label>
        Roll back to seq (keeps events up to and including it)
        <input
          type="number"
          min={0}
          value={target}
          onChange={(e) => {
            setTarget(e.target.value);
            setConfirming(false);
            setNotice(null);
          }}
          disabled={!writable}
        />
      </label>
      {!confirming ? (
        <button
          type="button"
          disabled={!writable || !valid || busy}
          onClick={() => setConfirming(true)}
        >
          Roll back
        </button>
      ) : (
        <div className="confirm" role="alertdialog" aria-label="Confirm rollback">
          <p>
            Remove {removed} event{removed === 1 ? "" : "s"} after seq {toSeq}? This cannot be
            undone.
          </p>
          <button type="button" className="danger" disabled={busy} onClick={run}>
            Confirm rollback
          </button>
          <button type="button" className="secondary" disabled={busy} onClick={() => setConfirming(false)}>
            Cancel
          </button>
        </div>
      )}
      {notice !== null && <p className="notice">{notice}</p>}
      {error !== null && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
