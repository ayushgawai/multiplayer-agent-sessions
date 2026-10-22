import { useState } from "react";
import { Header } from "./components/Header";
import { Lobby } from "./components/Lobby";
import { SessionView } from "./components/SessionView";
import { getApiClient } from "./lib/api";
import type { Identity } from "./lib/session";

export function App(): JSX.Element {
  const client = getApiClient();
  // Identity is kept in memory only. A reload means joining again.
  const [identity, setIdentity] = useState<Identity | null>(null);

  return (
    <>
      <Header client={client} />
      <main>
        {identity === null ? (
          <Lobby client={client} onJoined={setIdentity} />
        ) : (
          <SessionView client={client} identity={identity} onLeave={() => setIdentity(null)} />
        )}
      </main>
    </>
  );
}
