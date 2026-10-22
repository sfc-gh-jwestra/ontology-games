import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy /api and /oauth to the local FastAPI backend (uvicorn on :8080).
// Same origin for both keeps the session cookie simple; the OAuth redirect URI is :5173/oauth/callback.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://localhost:8080",
      "/oauth": "http://localhost:8080",
    },
  },
});
