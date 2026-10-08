# client

React 18 + TypeScript (strict) + Vite 5. Owned by the client lead. This is the
DAT-15 scaffold: typed API client, in-memory mock backend, and the first
session screens. Node 20 LTS (see `.nvmrc`).

## Layout

- `src/lib/api-types.ts` generated from `../session-service/openapi.json`; never edit by hand
- `src/lib/api.ts` one typed client for every route; picks mock or real from env
- `src/lib/events.ts`, `useSessionEvents.ts` event merge rules and the live feed hook
- `src/mocks/` in-memory implementation of every route (module variables only)
- `src/components/` lobby, header, event list, instruction box, rollback panel
- `src/tests/` vitest tests

## Run with the mock (no backend)

```bash
cd client
npm ci
VITE_USE_MOCK=true npm run dev
```

The mock lives in the page, so two tabs do not share a session. Use the real
service for the two-tab demo.

## Run against the real session service

```bash
# terminal 1: session service (see the root README)
cd session-service && uvicorn app.main:app --reload --port 8000

# terminal 2: client
cd client
VITE_API_BASE=http://localhost:8000 npm run dev
```

The service sends no CORS headers, so a browser on the Vite origin cannot call
it directly. Two options:

- Leave `VITE_API_BASE` unset: the dev server proxies `/v1` (including the
  WebSocket) and `/healthz` to `http://localhost:8000`. Use
  `DEV_PROXY_TARGET=http://host:port npm run dev` to point it elsewhere.
- Set `VITE_API_BASE` to the service origin only when that origin allows CORS.

The header shows MOCK or REAL, the API base, and the `/healthz` result.

## Scripts

| Script | What it does |
|--------|--------------|
| `npm run dev` | Vite dev server |
| `npm run build` | typecheck, then production build to `dist/` |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | vitest |
| `npm run gen:types` | regenerate `src/lib/api-types.ts` from `openapi.json` |

Regenerate types whenever `openapi.json` changes (an ADR is required first).

## How the live feed works

The service streams appended events over a WebSocket, but it does not publish
rollbacks. The feed therefore also re-reads the full log every 3 s (every
1.5 s while the stream is down) and replaces the list when it differs. That is
how a second tab notices a rollback. Join needs both the session id and the
join code, so the lobby shows both after create.

No browser storage is used: reloading a tab means joining again.

## Next steps

1. Yjs editor and `crdt-server/` provider (DAT-16)
2. Presence and awareness cursors (DAT-17)
3. Agent console (direct, interrupt, hand off)
4. Conflict tray driven by arbitration events
5. Replay viewer using rollback in read-only mode

CI does not build `client/` yet.
