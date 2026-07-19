# Five Production Themes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the production test platform's legacy four-theme picker with the approved Crystal, X-Lab, Column, Clay, and Liquid themes without changing routes, permissions, data requests, or business workflows.

**Architecture:** Introduce one framework-agnostic theme registry as the shared source of truth for types, labels, previews, legacy migration, and CSS preset mapping. Keep the current semantic-token architecture and existing shadcn components; the provider applies the selected theme at the document root, while `MainLayout` only renders the picker. Existing business pages continue consuming the same CSS variables and therefore require no per-page logic branches.

**Tech Stack:** React 18, TypeScript, Zustand, Tailwind CSS, shadcn/Radix, Vitest, Testing Library, Playwright, Vite.

---

### Task 1: Capture baseline and theme contract

**Files:**
- Create: `test-platform-v2/frontend/src/lib/__tests__/themes.test.ts`
- Create: `test-platform-v2/frontend/src/components/__tests__/theme-provider.test.tsx`

- [ ] **Step 1: Run the existing unit-test baseline**

Run:

```powershell
& 'C:\Users\26029\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\vitest.mjs run
```

Expected: the existing 19 test files pass before theme integration.

- [ ] **Step 2: Write the failing registry test**

```ts
import { describe, expect, it } from 'vitest'
import { COLOR_THEMES, normalizeColorTheme } from '../themes'

describe('production theme registry', () => {
  it('exposes the five approved themes in comparison order', () => {
    expect(COLOR_THEMES.map((theme) => theme.id)).toEqual([
      'crystal', 'xlab', 'column', 'clay', 'liquid',
    ])
  })

  it('migrates legacy saved themes without losing project preferences', () => {
    expect(normalizeColorTheme('blue')).toBe('crystal')
    expect(normalizeColorTheme('dark-minimal')).toBe('xlab')
    expect(normalizeColorTheme('warm')).toBe('column')
    expect(normalizeColorTheme('nature')).toBe('clay')
    expect(normalizeColorTheme('unknown')).toBe('crystal')
  })
})
```

- [ ] **Step 3: Write the failing provider test**

Render a small `useTheme()` harness inside `ThemeProvider`, select `liquid`, and assert that the root receives `data-theme-id="liquid"`, the persistent key stores `liquid`, and a stored legacy `blue` preference restores as `crystal`.

- [ ] **Step 4: Run the focused tests and verify failure**

Run Vitest for both new files. Expected: failure because the shared registry and five-theme provider contract do not exist.

### Task 2: Create the shared theme registry and persistence migration

**Files:**
- Create: `test-platform-v2/frontend/src/lib/themes.ts`
- Modify: `test-platform-v2/frontend/src/components/theme-provider.tsx`
- Modify: `test-platform-v2/frontend/src/stores/auth.ts`

- [ ] **Step 1: Create the approved theme registry**

Define `COLOR_THEMES` with these IDs and CSS preset mappings:

```ts
export const COLOR_THEMES = [
  { id: 'crystal', number: '01', label: '晶穹', name: 'Crystal Command', cssPreset: 'blue' },
  { id: 'xlab', number: '02', label: '黑域', name: 'X-Lab', cssPreset: 'dark-minimal' },
  { id: 'column', number: '03', label: '列阵', name: 'Column Pulse', cssPreset: 'warm' },
  { id: 'clay', number: '04', label: '软体', name: 'Clay Studio', cssPreset: 'nature' },
  { id: 'liquid', number: '05', label: '液境', name: 'Liquid Spectrum', cssPreset: 'liquid' },
] as const
```

Include descriptions, three preview colors per theme, `ColorTheme`, `getThemeDefinition`, `getThemeCssPreset`, and `normalizeColorTheme`. Normalize the four legacy identifiers to the corresponding approved theme and default unknown values to `crystal`.

- [ ] **Step 2: Update the provider**

Import the shared type and normalization helpers, default to `crystal`, persist only approved IDs, apply both `data-theme-id` and the internal CSS preset, and use native View Transitions when available. Preserve `light / dark / system` behavior and provide an immediate reduced-motion fallback.

- [ ] **Step 3: Update project-theme typing**

Remove the duplicated union from the auth store and import `ColorTheme` from the registry. Keep the existing project map and setters unchanged so project switching behavior remains intact.

- [ ] **Step 4: Run the focused tests**

Expected: registry and provider tests pass.

### Task 3: Replace the production theme picker

**Files:**
- Modify: `test-platform-v2/frontend/src/layouts/MainLayout.tsx`

- [ ] **Step 1: Consume the registry**

Remove the local legacy theme config, import `COLOR_THEMES`, and map theme IDs to existing Lucide icons. Do not add emoji or page-specific theme logic.

- [ ] **Step 2: Render five accessible options**

Render the five themes as compact rows with number, name, description, preview swatches, `aria-pressed`, and a visible selected indicator. Keep the current project-scoped save callback and the separate light/dark/system mode control.

- [ ] **Step 3: Improve the mode control semantics**

Give all icon-only mode buttons an `aria-label`, `title`, and at least 32px control size. Keep the same setter and no new modal or route.

### Task 4: Map the five visual systems onto production tokens

**Files:**
- Modify: `test-platform-v2/frontend/src/globals.css`

- [ ] **Step 1: Add canonical theme variables**

Append root-level overrides keyed by `data-theme-id` for Crystal, X-Lab, Column, Clay, and Liquid. Each theme must define background, foreground, cards, popovers, primary/secondary/accent, borders, chart colors, sidebar tokens, radius, density, motion, and glass variables.

- [ ] **Step 2: Add production component signatures**

Use the existing internal preset mapping for the first four themes, then add Liquid-specific treatment for the app header, sidebar, cards, popovers, dialogs, sheets, tabs, tables, progress, skeleton, and toast surfaces. Keep dense data surfaces opaque enough for readability.

- [ ] **Step 3: Add motion and accessibility fallbacks**

Use 150–320ms state transitions based on `transform`, `opacity`, colors, and filters; avoid page-load choreography. Extend `prefers-reduced-motion`, `prefers-reduced-transparency`, high contrast, and unsupported-backdrop fallbacks to the Liquid theme.

- [ ] **Step 4: Verify contrast**

Calculate key foreground/surface, muted/surface, primary/primary-foreground, and semantic-state pairs. Expected: normal text pairs meet at least 4.5:1.

### Task 5: Verify platform behavior end to end

**Files:**
- Modify: `test-platform-v2/frontend/e2e/smoke.spec.ts` only if a stable theme assertion belongs in the reusable suite

- [ ] **Step 1: Run complete automated checks**

Run all Vitest tests, TypeScript build, and Vite production build. Expected: zero failures and `dist/index.html` emitted.

- [ ] **Step 2: Run deterministic design checks**

Run the local design detector against `MainLayout.tsx`, `theme-provider.tsx`, and `globals.css`; review accessibility, interaction, and performance rules. Treat retained project-font warnings separately from regressions.

- [ ] **Step 3: Run visible Playwright regression against port 5173**

Use the project-local Playwright skill and a temporary script under the system temp directory. Verify the login page renders, authenticated app shell can be exercised if authorized credentials/session exist, all five theme buttons switch `data-theme-id`, current route and content remain unchanged, persistence survives reload, and desktop/mobile views have no horizontal overflow. Capture screenshots for visual QA when browser policy allows.

- [ ] **Step 4: Report backend-dependent coverage honestly**

If no authorized E2E credentials are supplied, run public/login and unit-level theme checks, mark authenticated live-route coverage as skipped, and rely on the existing guarded E2E suite rather than inventing credentials or bypassing authentication.

**Workspace note:** The shared worktree contains unrelated user changes, including active API-test and testcase work. Do not stage, commit, reformat, or modify those files. Commit steps are intentionally omitted until the user explicitly authorizes staging in this dirty worktree.
