# Liquid Glass Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fifth, production-feasible Liquid Glass theme to the existing test-platform theme lab while preserving every business interaction and demonstrating the full requested component set with smoother, accessible motion.

**Architecture:** Extend the existing theme registry and token-driven CSS rather than branching business logic. The fifth theme reuses the same module, tab, loading, run, dialog, progress, and snackbar state; a theme-only component panorama exposes the already-supported component patterns without adding backend calls or production operations. Native View Transitions are used when available, with a no-motion fallback.

**Tech Stack:** React 18, TypeScript, CSS custom properties, Lucide icons, Vitest, Testing Library, Vite.

---

### Task 1: Lock the fifth-theme behavior with tests

**Files:**
- Modify: `test-platform-v2/frontend/src/theme-lab/__tests__/ThemeLab.test.tsx`

- [ ] **Step 1: Extend the theme-switching test**

Rename the case to `switches all five themes without losing the active tab`, click the new accessible button name `/液境主题/`, assert `data-theme="liquid"`, then return to the first theme and confirm the previously selected tab is still active.

- [ ] **Step 2: Add the component-panorama interaction test**

```tsx
it('reuses existing interactions from the liquid component panorama', () => {
  render(<ThemeLab />)
  fireEvent.click(screen.getByRole('button', { name: /液境主题/ }))

  expect(screen.getByRole('region', { name: '液态组件全景' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '演示轻提示' }))
  expect(screen.getByText('液态玻璃轻提示已就绪')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '演示背景幕布' }))
  expect(screen.getByRole('dialog', { name: '启动回归确认' })).toBeTruthy()
})
```

- [ ] **Step 3: Run the focused test and confirm it fails before implementation**

Run:

```powershell
& 'C:\Users\26029\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\vitest.mjs run src/theme-lab/__tests__/ThemeLab.test.tsx
```

Expected: failure because the `liquid` theme and panorama do not exist yet.

### Task 2: Add the Liquid Glass theme without changing platform logic

**Files:**
- Modify: `test-platform-v2/frontend/src/theme-lab/ThemeLab.tsx`

- [ ] **Step 1: Extend the existing theme registry**

Add `liquid` to `ThemeId` and append this definition:

```tsx
{
  id: 'liquid',
  number: '05',
  label: '液境',
  name: 'Liquid Spectrum',
  source: 'Liquid Glass × 全组件系统',
  scene: '跨模块连续操作与沉浸式质量协作',
  tags: ['全景玻璃', '折射层级', '丝滑衔接'],
}
```

Update the header and manifest copy from four themes to five themes. Render `DecryptedText` for `liquid` as well as `xlab` so the decode component is part of the fifth theme.

- [ ] **Step 2: Add a theme-only component panorama using existing callbacks**

Create a focused `LiquidComponentPanorama` component that receives `progress`, `loading`, `onLoading`, `onSnackbar`, and `onBackdrop`. It must show the existing progress ring, progress bar, short spinner, skeleton sample, tabs label, decoded status, and buttons that call the existing loading/snackbar/run-dialog handlers. It must not add network calls or a second business state machine.

- [ ] **Step 3: Add progressive theme transitions**

Wrap `setTheme(next)` in `document.startViewTransition` when supported and when `prefers-reduced-motion` is not enabled. Fall back to the current immediate state change in all other cases. Keep the snackbar behavior unchanged.

- [ ] **Step 4: Run the focused test and confirm it passes**

Run the Task 1 command again. Expected: all theme-lab tests pass.

### Task 3: Build the glass material and smooth interaction system

**Files:**
- Modify: `test-platform-v2/frontend/src/theme-lab/theme-lab.css`

- [ ] **Step 1: Add tokenized liquid materials**

Add a `.theme-liquid` token block with a cool blue/violet ambient background, dark readable text, translucent surfaces, semantic state colors, 18–24px glass blur, and opaque-enough inner data layers. Use `--ease-fluid: cubic-bezier(0.22, 1, 0.36, 1)` with 160–320ms state transitions.

- [ ] **Step 2: Apply glass hierarchy to the existing component vocabulary**

Style the header, sidebar, topbar, theme manifest, tabs, panels, table shell, dialogs, snackbar, buttons, progress indicators, skeletons, and the new panorama from the same tokens. Preserve denser data rows with a high-opacity clarity layer so tables, logs, and status text remain readable.

- [ ] **Step 3: Add state-driven micro-interactions**

Use only `transform`, `opacity`, color, and backdrop/filter transitions for theme switching, tab selection, dialog entry, snackbar entry, progress changes, and interactive hover/press states. Do not add continuous decorative animation; keep the spinner as the only infinite motion.

- [ ] **Step 4: Add fallbacks and responsive behavior**

Extend the existing `prefers-reduced-motion`, `prefers-reduced-transparency`, high-contrast, unsupported-backdrop, 1080px, 900px, and 680px rules to include the fifth theme and its component panorama.

### Task 4: Record the fifth blueprint and verify the deliverable

**Files:**
- Modify: `test-platform-v2/docs/ui-concepts/component-style-reference.md`

- [ ] **Step 1: Add the fifth theme blueprint and matrix column**

Document `Liquid Spectrum / 液境全景台`, its scene, material hierarchy, component mapping, interaction timing, accessibility fallback, performance risks, and intended role as a high-fidelity experience theme rather than a change to platform logic.

- [ ] **Step 2: Run unit, type, and build checks**

```powershell
& 'C:\Users\26029\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vitest\vitest.mjs run
& 'C:\Users\26029\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\typescript\bin\tsc -b
& 'C:\Users\26029\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\node_modules\vite\bin\vite.js build
```

Expected: all tests pass, TypeScript exits 0, and Vite emits `dist/theme-lab.html`.

- [ ] **Step 3: Run final design checks**

Verify keyboard-visible focus, 44px mobile controls, reduced-motion and reduced-transparency fallbacks, non-color status labels, and 4.5:1 text contrast against the liquid clarity layer. Because enterprise browser policy blocks localhost in this environment, record browser visual QA as unavailable rather than bypassing policy.

**Workspace note:** Commit steps are intentionally omitted because the shared worktree already contains unrelated user changes; do not stage or commit them without explicit authorization.
