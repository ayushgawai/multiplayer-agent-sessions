import type { SessionEvent } from "../lib/api";
import { describeEvent } from "../lib/events";

function formatTime(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString();
}

export function EventList({ events }: { events: SessionEvent[] }): JSX.Element {
  if (events.length === 0) {
    return <p className="muted">No events yet.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="events">
        <thead>
          <tr>
            <th>seq</th>
            <th>time</th>
            <th>actor</th>
            <th>type</th>
            <th>text</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={`${e.seq ?? 0}:${e.event_id}`} className={`type-${e.type}`}>
              <td>{e.seq}</td>
              <td>{formatTime(e.ts)}</td>
              <td>
                {e.actor.display_name} <span className="muted">({e.actor.role})</span>
              </td>
              <td>
                <span className="tag">{e.type}</span>
              </td>
              <td>{describeEvent(e)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
