import { defineConfig } from "vitest/config"
import path from "path"

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    // D4: Coverage gate — v8 provider aligned with the installed Vitest major.
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
      // Batch 59 non-regression floor, set just below the measured Batch 58 baseline.
      thresholds: {
        statements: 27,
        branches: 22,
        functions: 23,
        lines: 28,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
