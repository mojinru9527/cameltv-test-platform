import { defineConfig } from "vitest/config"
import path from "path"

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    // D4: Coverage gate — v8 provider (bundled with vitest 2.x)
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      reportsDirectory: "./coverage",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/types/**",
        "src/**/*.d.ts",
        "src/main.tsx",
        "src/router/**",
      ],
      // Thresholds enforced in CI; local dev just reports
      thresholds: {
        lines: 70,
        branches: 50,
        functions: 60,
        statements: 70,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
