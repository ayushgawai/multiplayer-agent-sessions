import { useEffect, useState } from "react";
import type { ApiClient } from "../lib/api";

type Health = { state: "checking" } | { state: "ok"; version: string } | { state: "down" };

const POLL_MS = 10000;

export function Header({ client }: { client: ApiClient }): JSX.Element {
  const [health, setHealth] = useState<Health>({ state: "checking" });

  useEffect(() => {
    let cancelled = false;
    const check = (): void => {
      client
        .healthz()
        .then((res) => {
          if (!cancelled) {
            setHealth({ state: "ok", version: res.version });
          }
        })
        .catch(() => {
          if (!cancelled) {
            setHealth({ state: "down" });
          }
        });
    };
    check();
    const timer = setInterval(check, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [client]);

  const healthText =
    health.state === "ok"
      ? `healthz ok (v${health.version})`
      : health.state === "down"
        ? "healthz unreachable"
        : "healthz checking";

  return (
    <header className="app-header">
      <h1>Multiplayer Agent Sessions</h1>
      <div className="header-meta">
        <span className={`badge badge-${client.mode}`}>
          {client.mode === "mock" ? "MOCK API" : "REAL API"}
        </span>
        <span className="muted">{client.label}</span>
        <span className={`badge badge-health-${health.state}`}>{healthText}</span>
      </div>
    </header>
  );
}
