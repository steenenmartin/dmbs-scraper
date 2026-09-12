import { loadEnv, defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const env = loadEnv("development", new URL("../../", import.meta.url).pathname, "");

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${process.env.PORT || env.PORT || 3001}`,
        changeOrigin: true,
      },
    },
  },
});
