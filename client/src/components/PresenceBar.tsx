import type { PresenceEntry } from "../lib/presence";

export function PresenceBar({ entries }: { entries: PresenceEntry[] }): JSX.Element {
  if (entries.length === 0) {
    return <p className="muted presence-empty">No one else is here yet.</p>;
  }
  return (
    <ul className="presence" aria-label="Participants present">
      {entries.map((p) => (
        <li key={p.participantId} className={p.isSelf ? "presence-self" : undefined}>
          <span className="presence-dot" style={{ backgroundColor: p.colour }} aria-hidden="true" />
          <span className="presence-name">
            {p.displayName}
            {p.isSelf ? " (you)" : ""}
          </span>
          <span className="tag">{p.role}</span>
        </li>
      ))}
    </ul>
  );
}
