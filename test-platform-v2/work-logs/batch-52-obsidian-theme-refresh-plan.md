# Batch 52 Obsidian Theme Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use the repository Agent Team workflow. Steps use checkbox (`- [ ]`) syntax for tracking; worker agents edit only assigned files and the primary Codex agent reviews, tests, and commits each slice.

**Goal:** Make Obsidian Flow a stable sixth first-class theme, remove the conflicting dual-theme state, and close its release-blocking accessibility and live-switching gaps without prematurely redesigning the other five themes.

**Architecture:** `ThemeProvider` and `lib/themes.ts` become the single theme contract. Obsidian is selected through the same `colorTheme` state as Cyberpunk, Apple, Clay, xLab, and Liquid Glass; the old UI provider remains only as a temporary derived compatibility hook and no longer owns storage or DOM attributes. Semantic CSS tokens drive Obsidian components, while representative browser tests verify computed styles, preferences, keyboard behavior, and three viewport sizes.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind 3, Radix/shadcn components, Vitest, Playwright, Axe.

**Status:** ✅ Implemented and locally verified on 2026-07-28. The task checkboxes below preserve the original execution sequence; exact final evidence is recorded in the Batch 52 QA report.

---

## File Structure

- Modify `frontend/src/lib/themes.ts` — register Obsidian as theme 06 and expose mode support.
- Modify `frontend/src/components/theme-provider.tsx` — own all root theme attributes and safe transition cleanup.
- Modify `frontend/src/ui/themes/UiThemeProvider.tsx` — compatibility adapter derived from `ThemeProvider`; no independent state.
- Modify `frontend/src/main.tsx` — remove the redundant provider and global Theme Lab stylesheet.
- Modify `frontend/src/layouts/MainLayout.tsx` — present one six-theme selector and enforce dark-only Obsidian mode.
- Modify `frontend/src/ui/themes/registry.ts` — mark the unified Obsidian contract stable.
- Modify `frontend/src/ui/themes/obsidian-flow.css` and `frontend/src/globals.css` — use one selector/token source and correct preference fallbacks.
- Modify `frontend/src/ui/components/SpatialChain.tsx` and `frontend/src/ui/patterns/Inspector.tsx` — replace hard-coded Obsidian colors, add responsive/focus behavior.
- Modify `frontend/src/hooks/use-chart-colors.ts` and `frontend/src/components/ui/sonner.tsx` — respond to live theme changes.
- Modify four production pages identified by the audit — add accessible names to icon-only actions.
- Modify existing theme/component tests and create `frontend/e2e/batch52-theme-regression.spec.ts`.
- Create `work-logs/batch-52-obsidian-theme-refresh-{design-spec,qa-report,leader-verdict}.md`.

### Task 1: Lock the unified theme contract with failing tests

**Files:**
- Modify: `test-platform-v2/frontend/src/lib/__tests__/themes.test.ts`
- Modify: `test-platform-v2/frontend/src/components/__tests__/theme-provider.test.tsx`
- Modify: `test-platform-v2/frontend/src/components/__tests__/theme-provider.test.tsx`
- Modify: `test-platform-v2/frontend/src/lib/themes.ts`

- [ ] **Step 1: Add the registry contract test**

```ts
expect(COLOR_THEMES.map((theme) => theme.id)).toEqual([
  'cyberpunk',
  'apple',
  'clay',
  'xlab',
  'liquid-glass',
  'obsidian-flow',
])
expect(getThemeDefinition('obsidian-flow').supportedModes).toEqual(['dark'])
```

- [ ] **Step 2: Add the provider attribute test**

```tsx
fireEvent.click(screen.getByRole('button', { name: '切换到黑曜流界' }))
expect(document.documentElement).toHaveAttribute('data-theme', 'obsidian-flow')
expect(document.documentElement).toHaveAttribute('data-theme-id', 'obsidian-flow')
expect(document.documentElement).toHaveAttribute('data-ui-theme', 'obsidian-flow')
expect(document.documentElement).toHaveClass('dark')
```

- [ ] **Step 3: Run the focused tests and verify they fail**

Run: `npm test -- src/lib/__tests__/themes.test.ts src/components/__tests__/theme-provider.test.tsx`

Expected: FAIL because `obsidian-flow` is not a `ColorTheme` and the current UI provider owns `data-ui-theme`.

- [ ] **Step 4: Register the sixth theme**

```ts
{
  id: 'obsidian-flow',
  number: '06',
  label: '黑曜',
  name: 'Obsidian Flow',
  description: '黑曜空间玻璃 × 质量链路工作台',
  preview: ['#35e68a', '#0b100d', '#eef6f0'],
  cssPreset: 'obsidian-flow',
  preferredMode: 'dark',
  supportedModes: ['dark'],
}
```

Every existing theme receives an explicit `supportedModes` array matching its real light/dark CSS support.

- [ ] **Step 5: Re-run the focused tests**

Run: `npm test -- src/lib/__tests__/themes.test.ts src/components/__tests__/theme-provider.test.tsx`

Expected: registry test PASS; provider test remains FAIL until Task 2.

### Task 2: Remove dual theme ownership

**Files:**
- Modify: `test-platform-v2/frontend/src/components/theme-provider.tsx`
- Modify: `test-platform-v2/frontend/src/ui/themes/UiThemeProvider.tsx`
- Modify: `test-platform-v2/frontend/src/main.tsx`
- Modify: `test-platform-v2/frontend/src/layouts/MainLayout.tsx`
- Modify: `test-platform-v2/frontend/src/ui/themes/registry.ts`

- [ ] **Step 1: Make `ThemeProvider` apply the complete root contract**

```ts
const isObsidian = colorTheme === 'obsidian-flow'
root.dataset.theme = getThemeCssPreset(colorTheme)
root.dataset.themeId = colorTheme
if (isObsidian) root.dataset.uiTheme = 'obsidian-flow'
else delete root.dataset.uiTheme
```

Resolve an unsupported saved mode to the theme's preferred mode before applying classes. Track the transition timer in an effect cleanup so rapid changes cannot remove a newer transition.

- [ ] **Step 2: Convert `UiThemeProvider` to a derived compatibility adapter**

```tsx
export function UiThemeProvider({ children }: { children: ReactNode }) {
  return <>{children}</>
}

export function useUiTheme() {
  const { colorTheme, setColorTheme } = useTheme()
  return {
    uiTheme: colorTheme === 'obsidian-flow' ? 'obsidian-flow' : 'default',
    setUiTheme: (theme: UiThemeId) =>
      setColorTheme(theme === 'obsidian-flow' ? 'obsidian-flow' : DEFAULT_COLOR_THEME),
  }
}
```

This API is retained only for existing workbench and `useObsidianPage` consumers.

- [ ] **Step 3: Remove the redundant provider**

```tsx
<ThemeProvider>
  <TooltipProvider delayDuration={300}>
    <RouterProvider router={router} />
    <Toaster richColors closeButton />
  </TooltipProvider>
</ThemeProvider>
```

- [ ] **Step 4: Replace the separate Obsidian toggle with theme 06**

`MainLayout` derives `isObsidian` from `colorTheme`. Remove `useUiTheme()` and its standalone switch. The existing theme grid renders all six entries; when Obsidian is selected it calls `setMode('dark')`. The mode control displays only its supported options and explains “黑曜流界为深色专属”.

- [ ] **Step 5: Mark the unified registry stable**

```ts
status: 'stable',
version: '1.1.0',
```

- [ ] **Step 6: Run focused tests**

Run: `npm test -- src/lib/__tests__/themes.test.ts src/components/__tests__/theme-provider.test.tsx src/pages/workbench`

Expected: PASS with one theme state and no independent `cameltv-ui-theme` writes.

### Task 3: Establish one Obsidian token and selector source

**Files:**
- Modify: `test-platform-v2/frontend/src/ui/themes/obsidian-flow.css`
- Modify: `test-platform-v2/frontend/src/ui/tokens/semantics.css`
- Modify: `test-platform-v2/frontend/src/globals.css`
- Modify: `test-platform-v2/frontend/src/ui/components/SpatialChain.tsx`
- Modify: `test-platform-v2/frontend/src/ui/patterns/Inspector.tsx`

- [ ] **Step 1: Move Obsidian CSS to the first-class selector**

Replace every `[data-ui-theme="obsidian-flow"]` selector with `[data-theme="obsidian-flow"]`. The temporary `data-ui-theme` attribute remains an observable compatibility signal, not a second cascade.

- [ ] **Step 2: Keep a single semantic alias layer**

Inside `[data-theme="obsidian-flow"]`, map product semantics to the existing shadcn variables:

```css
--color-canvas: var(--background);
--color-surface: var(--card);
--color-text: var(--foreground);
--color-text-secondary: var(--muted-foreground);
--color-action-primary: var(--primary);
--color-border-default: var(--border);
--color-focus-ring: var(--ring);
```

Raise muted text to a verified AA value and remove duplicate private color literals where a semantic token exists.

- [ ] **Step 3: Remove the light-mode contradiction**

Delete `.light[data-ui-theme="obsidian-flow"]`. The provider enforces dark mode for the dark-only theme.

- [ ] **Step 4: Tokenize `SpatialChain`**

Use semantic classes/variables for all surface, border, text, focus, status, and progress colors:

```ts
neutral: {
  bg: 'bg-[var(--color-surface-elevated)]',
  border: 'border-[var(--color-border-default)]',
  text: 'text-[var(--color-text-secondary)]',
}
```

The component must render legibly in every first-class theme and may use Obsidian material only when the active tokens request it.

- [ ] **Step 5: Harden `Inspector`**

Use `w-[min(100vw,380px)] max-w-full`, semantic colors, a 44px close target, focus trapping, Escape handling, and focus restoration to the opener.

- [ ] **Step 6: Fix preference fallbacks**

Correct Liquid Glass to the same-element selector:

```css
[data-reduced-transparency="true"][data-theme="liquid-glass"] .glass-card
```

Add solid-fill fallbacks under `@supports not (backdrop-filter: blur(1px))` and preserve existing reduced-motion behavior.

- [ ] **Step 7: Run component tests**

Run: `npm test -- src/ui/primitives/__tests__/Primitives.test.tsx src/ui/components/__tests__/PageShell.test.tsx`

Expected: PASS; new Inspector keyboard assertions also PASS.

### Task 4: Make charts, toasts, and initial paint follow the active theme

**Files:**
- Modify: `test-platform-v2/frontend/src/hooks/use-chart-colors.ts`
- Modify: `test-platform-v2/frontend/src/components/ui/sonner.tsx`
- Modify: `test-platform-v2/frontend/index.html`
- Modify: `test-platform-v2/frontend/src/main.tsx`
- Modify: `test-platform-v2/frontend/src/components/__tests__/theme-provider.test.tsx`

- [ ] **Step 1: Re-read chart CSS variables after theme changes**

```ts
const { colorTheme, mode } = useTheme()
const [colors, setColors] = useState(readChartColors)

useEffect(() => {
  const frame = requestAnimationFrame(() => setColors(readChartColors()))
  return () => cancelAnimationFrame(frame)
}, [colorTheme, mode])
```

- [ ] **Step 2: Bind Sonner to the custom theme context**

Replace `next-themes` usage with the repository `useTheme()`. Resolve `system` through `matchMedia` and pass only `light | dark` to Sonner.

- [ ] **Step 3: Prevent first-paint theme flash**

Add an inline pre-paint script in `index.html` that reads the two existing storage keys, normalizes only known theme IDs, and applies `class`, `data-theme`, `data-theme-id`, and the Obsidian compatibility attribute before React loads. The script contains no credentials and mirrors `ThemeProvider`.

- [ ] **Step 4: Lazy-load Theme Lab CSS**

Remove `theme-lab.css` from `main.tsx`; import it only from `theme-lab/main.tsx`.

- [ ] **Step 5: Test live switching**

Run: `npm test -- src/components/__tests__/theme-provider.test.tsx src/lib/__tests__/themes.test.ts`

Expected: the root contract and chart re-read test PASS without reload.

### Task 5: Close audited accessibility blockers

**Files:**
- Modify: `test-platform-v2/frontend/src/ui/primitives/Button.tsx`
- Modify: `test-platform-v2/frontend/src/ui/themes/obsidian-flow.css`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/DebugTab.tsx`
- Modify: `test-platform-v2/frontend/src/pages/perftest/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/release-bundles/BundleDetail.tsx`
- Modify: `test-platform-v2/frontend/src/layouts/MainLayout.tsx`

- [ ] **Step 1: Enforce coarse-pointer targets**

```css
@media (pointer: coarse) {
  [data-theme="obsidian-flow"] .ui-btn,
  [data-theme="obsidian-flow"] .ui-btn-xs,
  [data-theme="obsidian-flow"] .ui-btn-sm,
  [data-theme="obsidian-flow"] .ui-btn-icon,
  [data-theme="obsidian-flow"] .ui-btn-icon-sm,
  [data-theme="obsidian-flow"] .ui-btn-icon-xs {
    min-width: 44px;
    min-height: 44px;
  }
}
```

- [ ] **Step 2: Name audited icon actions**

Add concise Chinese `aria-label` values to the four icon-only action sites from the technical audit. Decorative icons remain `aria-hidden="true"`.

- [ ] **Step 3: Move focus on route changes**

On `location.pathname` changes, call `document.getElementById('main-content')?.focus()` in an effect with no asynchronous work.

- [ ] **Step 4: Verify focused accessibility tests**

Run: `npm test -- src/components/__tests__/DataTable.a11y.test.tsx src/ui/components src/layouts`

Expected: PASS with no unnamed buttons in the covered states.

### Task 6: Add release evidence and run the full gate

**Files:**
- Create: `test-platform-v2/frontend/e2e/batch52-theme-regression.spec.ts`
- Create: `test-platform-v2/work-logs/batch-52-obsidian-theme-refresh-design-spec.md`
- Create: `test-platform-v2/work-logs/batch-52-obsidian-theme-refresh-qa-report.md`
- Create: `test-platform-v2/work-logs/batch-52-obsidian-theme-refresh-leader-verdict.md`

- [ ] **Step 1: Add computed-style theme assertions**

For all six theme IDs, authenticate through mocked storage, visit one representative page, select the theme, and assert:

```ts
expect(await page.locator('html').getAttribute('data-theme')).toBe(theme.id)
expect(await page.evaluate(() => getComputedStyle(document.documentElement)
  .getPropertyValue('--background').trim())).toBe(theme.expectedBackground)
```

Obsidian additionally asserts dark mode, `data-ui-theme`, readable muted text, and no duplicate `h1`.

- [ ] **Step 2: Add preference and responsive coverage**

Run representative dashboard/list/form/overlay states at 390×844, 768×1024, and 1440×900. Cover keyboard traversal, Escape/focus restoration, reduced motion, reduced transparency, horizontal overflow, Axe, and live chart/toast switching.

- [ ] **Step 3: Run hard gates**

Run:

```text
npm run typecheck
npm run build
npm test
npx playwright test e2e/batch52-theme-regression.spec.ts --project=chromium
```

Expected: all exit 0; record file/test counts and durations.

- [ ] **Step 4: Run repository policy scans**

Confirm no new `console.log`, `debugger`, credentials, untracked databases, backup files, direct legacy Badge imports, or changed-file async effects without cleanup.

- [ ] **Step 5: Write QA and leader evidence**

The QA report records exact commands, exit codes, baseline debt, new failure set, theme matrix, browser screenshots/evidence, and CI classification. The leader verdict may be `APPROVED` only when P0/P1 findings in this plan are closed.

## Self-Review

- Spec coverage: the plan implements the audit’s P0 dual-state fix and P1 theme response/accessibility gaps. It intentionally does not perform the five-theme visual refresh because the user conditioned that work on Obsidian already being complete.
- Placeholder scan: no TBD/TODO/“implement later” steps remain.
- Type consistency: `ColorTheme`, `supportedModes`, storage keys, and root attributes use the existing repository names.
- Scope: all tracked changes remain under `test-platform-v2`, matching the Agent Team worktree metadata.
