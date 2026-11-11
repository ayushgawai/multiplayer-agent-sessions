// A timestamp has a zone if it ends in Z or a +HH:MM / -HH:MM offset.
const HAS_ZONE = /(?:Z|[+-]\d{2}:?\d{2})$/i;

/**
 * Parse an event timestamp. Stored events come back without an offset while
 * streamed events carry one, so a value with no zone is read as UTC.
 * Returns null when the text is not a valid date.
 */
export function parseEventTime(ts: string): Date | null {
  const trimmed = ts.trim();
  const iso = HAS_ZONE.test(trimmed) ? trimmed : `${trimmed}Z`;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Local time of day for the event list; falls back to the raw text. */
export function formatEventTime(ts: string): string {
  const date = parseEventTime(ts);
  return date === null ? ts : date.toLocaleTimeString();
}
