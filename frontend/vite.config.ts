import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.MOMENTO_API_PROXY_TARGET ?? "http://127.0.0.1:8020";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api": apiTarget,
    },
  },
});
