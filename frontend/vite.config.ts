import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// Dev only: hand the backend session token to the page served by this dev server.
// It is read on every page load, so starting the backend after Vite just needs a refresh.
// Other websites cannot read this HTML (no CORS), so they never see the token.
// The packaged Electron app gets the token from electron/preload.cjs instead.
function jarvisDevToken(): Plugin {
  const tokenFile = process.env.JARVIS_TOKEN_FILE
    ?? resolve(__dirname, "..", "backend", "data", ".jarvis_token");
  return {
    name: "jarvis-dev-token",
    apply: "serve",
    transformIndexHtml() {
      let token = process.env.JARVIS_TOKEN ?? "";
      if (!token) {
        try { token = readFileSync(tokenFile, "utf8").trim(); } catch { /* backend not started yet */ }
      }
      return token ? [{ tag: "meta", attrs: { name: "jarvis-token", content: token }, injectTo: "head" }] : [];
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [react(), jarvisDevToken()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
