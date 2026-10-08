import { readFileSync } from "node:fs";
import {
  createServer,
  type IncomingMessage,
  type Server,
  type ServerResponse,
} from "node:http";
import type { AddressInfo } from "node:net";
import type { Duplex } from "node:stream";
import { WebSocketServer } from "ws";
import { setupWSConnection } from "y-websocket/bin/utils";

const PATH_PREFIX = "/crdt/";
const DOC_NAME = /^[A-Za-z0-9_.-]{1,200}$/;

function readVersion(): string {
  const url = new URL("../package.json", import.meta.url);
  const pkg = JSON.parse(readFileSync(url, "utf8")) as { version?: string };
  return pkg.version ?? "unknown";
}

export const VERSION = readVersion();

/** Session id from a request URL like /crdt/ses_123?x=1, or null. */
export function docNameFromUrl(rawUrl: string | undefined): string | null {
  const path = (rawUrl ?? "").split("?")[0] ?? "";
  if (!path.startsWith(PATH_PREFIX)) {
    return null;
  }
  const name = decodeURIComponent(path.slice(PATH_PREFIX.length));
  return DOC_NAME.test(name) ? name : null;
}

function handleHttp(req: IncomingMessage, res: ServerResponse): void {
  const path = (req.url ?? "").split("?")[0];
  if (req.method === "GET" && path === "/healthz") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, version: VERSION }));
    return;
  }
  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("not found");
}

export interface CrdtServer {
  readonly port: number;
  close: () => Promise<void>;
}

/** Start the y-websocket authority. Documents live in memory only. */
export async function startCrdtServer(
  port: number,
  host = "0.0.0.0",
): Promise<CrdtServer> {
  const http: Server = createServer(handleHttp);
  const wss = new WebSocketServer({ noServer: true });

  http.on("upgrade", (req: IncomingMessage, socket: Duplex, head: Buffer) => {
    const docName = docNameFromUrl(req.url);
    if (docName === null) {
      socket.write("HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n");
      socket.destroy();
      return;
    }
    wss.handleUpgrade(req, socket, head, (ws) => {
      setupWSConnection(ws, req, { docName });
    });
  });

  await new Promise<void>((resolve, reject) => {
    http.once("error", reject);
    http.listen(port, host, resolve);
  });
  const address = http.address() as AddressInfo;

  return {
    port: address.port,
    close: () =>
      new Promise<void>((resolve) => {
        for (const client of wss.clients) {
          client.terminate();
        }
        wss.close(() => {
          http.close(() => resolve());
          http.closeAllConnections();
        });
      }),
  };
}
