import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The session service sends no CORS headers, so the dev server proxies the
// API paths to it. Set VITE_API_BASE to the service origin to bypass the proxy.
const target = process.env.DEV_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/v1": { target, changeOrigin: true, ws: true },
      "/healthz": { target, changeOrigin: true },
    },
  },
  test: {
    environment: "node",
  },
});
