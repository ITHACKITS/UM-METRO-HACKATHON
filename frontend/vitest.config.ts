import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "html"],
      reportsDirectory: "./coverage",
      include: ["src/sigap/**/*.{ts,tsx}", "src/lib/pwa.ts"],
      exclude: ["**/*.test.{ts,tsx}"],
    },
  },
});
