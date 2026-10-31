import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // MapLibre 6 ships its worker as a sibling ESM file. Pre-bundling rewrites that
  // URL to Vite's dependency cache, where the worker can fail with HTTP 504.
  optimizeDeps: { exclude: ["maplibre-gl"] },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("/node_modules/three/")) return "three";
          if (id.includes("/node_modules/maplibre-gl/")) return "map";
          if (id.includes("/node_modules/gsap/") || id.includes("/node_modules/lenis/")) return "motion";
        },
      },
    },
  },
});
