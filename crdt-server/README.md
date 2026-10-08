# crdt-server

y-websocket authority for the collaborative document. Node 20 LTS, TypeScript
strict. Documents are held in memory only; a restart clears them (the session
event log in the session service is the durable record).

- WebSocket: `ws://localhost:1234/crdt/{session_id}` (y-websocket protocol)
- HTTP: `GET /healthz` returns `{"ok": true, "version": "..."}`
- `session_id` must match `[A-Za-z0-9_.-]{1,200}`; other paths get a 404

## Run

```bash
cd crdt-server
npm ci
npm run dev        # tsx watch, port 1234
npm run build && npm start
```

Environment: `PORT` (default 1234), `HOST` (default 0.0.0.0).

## Scripts

| Script | What it does |
|--------|--------------|
| `npm run dev` | run `src/main.ts` with reload |
| `npm run build` | compile `src/` to `dist/` |
| `npm start` | run `dist/main.js` |
| `npm run typecheck` | `tsc --noEmit` over `src` and `test` |
| `npm test` | vitest: health, two clients converge, rooms stay separate |

`src/y-websocket-utils.d.ts` declares the one server helper used, because
y-websocket 2.0.4 does not expose types for it through its exports map.

## Proposed Compose entry (not applied)

`infra/docker-compose.yml` belongs to the infra owner. A service could look
like this, with a Dockerfile that runs `npm ci && npm run build` and then
`node dist/main.js`:

```yaml
  crdt-server:
    build:
      context: ../crdt-server
      dockerfile: ../infra/Dockerfile.crdt-server
    ports:
      - "1234:1234"
    environment:
      PORT: "1234"
    healthcheck:
      test: ["CMD", "node", "-e", "fetch('http://localhost:1234/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
      interval: 10s
```

## Next steps

- Presence and awareness colours (DAT-17)
- Optional persistence if lab sessions need documents to survive restarts
