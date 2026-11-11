import type { ApiClient } from "../lib/api";
import type { Identity } from "../lib/session";
import { useSessionEvents } from "../lib/useSessionEvents";
import { DocumentEditor } from "./DocumentEditor";
import { EventList } from "./EventList";
import { InstructionBox } from "./InstructionBox";
import { RollbackPanel } from "./RollbackPanel";

interface Props {
  client: ApiClient;
  identity: Identity;
  onLeave: () => void;
}

const STATUS_TEXT = {
  connecting: "connecting",
  stream: "live (stream)",
  polling: "polling (stream unavailable)",
} as const;

export function SessionView({ client, identity, onLeave }: Props): JSX.Element {
  const feed = useSessionEvents(client, identity.sessionId);

  return (
    <div className="session">
      <section className="card session-info">
        <div>
          <strong>{identity.displayName}</strong>{" "}
          <span className="muted">
            ({identity.role}, {identity.participantId})
          </span>
        </div>
        <div>
          Session <code>{identity.sessionId}</code> join code{" "}
          <code className="join-code">{identity.joinCode}</code>
        </div>
        <div>
          Feed: <span className={`badge badge-feed-${feed.status}`}>{STATUS_TEXT[feed.status]}</span>
        </div>
        <button type="button" className="secondary" onClick={onLeave}>
          Leave
        </button>
      </section>

      {feed.error !== null && (
        <p className="error" role="alert">
          {feed.error}
        </p>
      )}

      <DocumentEditor client={client} identity={identity} />

      <section className="card">
        <h2>Events</h2>
        <EventList events={feed.events} />
      </section>

      <div className="actions">
        <InstructionBox client={client} identity={identity} onSent={() => void feed.refresh()} />
        <RollbackPanel
          client={client}
          identity={identity}
          events={feed.events}
          onRolledBack={() => void feed.refresh()}
        />
      </div>
    </div>
  );
}
