import { VERSION, startCrdtServer } from "./server.js";

const port = Number.parseInt(process.env["PORT"] ?? "1234", 10);
const host = process.env["HOST"] ?? "0.0.0.0";

const server = await startCrdtServer(port, host);
console.log(`crdt-server ${VERSION} listening on ws://${host}:${server.port}/crdt/{session_id}`);

const stop = (): void => {
  void server.close().then(() => process.exit(0));
};
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
