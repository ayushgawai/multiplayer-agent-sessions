import { useEffect, useState } from "react";
import type { Awareness } from "y-protocols/awareness";
import { readPresence, subscribePresence, type PresenceEntry } from "./presence";

/** Live presence list. Empty until a document (and its awareness) exists. */
export function usePresence(awareness: Awareness | null): PresenceEntry[] {
  const [entries, setEntries] = useState<PresenceEntry[]>([]);

  useEffect(() => {
    if (awareness === null) {
      setEntries([]);
      return undefined;
    }
    setEntries(readPresence(awareness));
    return subscribePresence(awareness, setEntries);
  }, [awareness]);

  return entries;
}
