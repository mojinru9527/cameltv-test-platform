# Test Platform Theme Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone, non-production-connected theme lab that compares four visually distinct test-platform themes while demonstrating the requested loading, feedback, tab, backdrop, easing, and text-decode interactions.

**Architecture:** Keep the existing `/ui-concepts.html` prototype unchanged. Add a second Vite HTML entry at `/theme-lab.html` backed by a focused React component and one stylesheet; reuse the existing React Bits-style `FadeContent` component and the centralized Lucide icon exports. Store the research and theme decision matrix beside the existing UI concept documentation.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, Lucide icons, CSS custom properties.

---

### Task 1: Preserve the research and design decisions

**Files:**
- Create: `test-platform-v2/docs/ui-concepts/component-style-reference.md`

- [ ] **Step 1: Record every requested component and style**

The document must include these exact inventory groups:

```text
NameThatUI list: Progress Ring / Spinner / Progress Bar, Text Scramble,
Skeleton / Spinner, Backdrop, Easing, Liquid Glass.
LearnUI list: Snackbar, Tabs, Liquid Glass, Cyberpunk, Claymorphism,
Apple, xAI, ClickHouse.
```

- [ ] **Step 2: Add test-platform usage rules and anti-rules**

For every component, document: suitable duration/scope, test-platform placement, accessibility fallback, and misuse to avoid. Explicitly restrict glass to navigation/overlay layers, text scramble to short non-critical labels, and spinner to short indeterminate actions.

- [ ] **Step 3: Add four theme blueprints and a gap inventory**

Document the four themes `Crystal Command`, `X-Lab`, `Column Pulse`, and `Clay Studio`, followed by missing enterprise patterns such as data grid, command palette, inspector, tree view, log stream, diff viewer, saved filters, empty/error/offline/permission states, and reduced-motion/high-contrast modes.

### Task 2: Create the standalone page entry

**Files:**
- Create: `test-platform-v2/frontend/theme-lab.html`
- Create: `test-platform-v2/frontend/src/theme-lab/main.tsx`

- [ ] **Step 1: Add the Vite HTML entry**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="color-scheme" content="light dark" />
    <link rel="icon" href="data:," />
    <title>CamelTv 测试平台 · 四主题实验室</title>
  </head>
  <body>
    <div id="theme-lab-root"></div>
    <script type="module" src="/src/theme-lab/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Mount the theme lab**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeLab } from './ThemeLab'
import './theme-lab.css'

ReactDOM.createRoot(document.getElementById('theme-lab-root')!).render(
  <React.StrictMode>
    <ThemeLab />
  </React.StrictMode>,
)
```

### Task 3: Implement the requested interactions

**Files:**
- Create: `test-platform-v2/frontend/src/theme-lab/DecryptedText.tsx`
- Create: `test-platform-v2/frontend/src/theme-lab/ThemeLab.tsx`
- Reuse: `test-platform-v2/frontend/src/ui-concepts/FadeContent.tsx`

- [ ] **Step 1: Implement accessible decoded text**

`DecryptedText` accepts `{ text: string; activeKey: string }`, exposes the final text through `aria-label`, marks scrambled glyphs `aria-hidden`, completes in under 500 ms, cancels timers on unmount, and returns the final string immediately when `prefers-reduced-motion: reduce` matches.

- [ ] **Step 2: Implement four persistent theme choices**

Use the exact theme ids and labels below so visual switching never resets the active work tab:

```ts
type ThemeId = 'crystal' | 'xlab' | 'column' | 'clay'

const themes = [
  { id: 'crystal', label: '晶穹', source: 'Apple × Liquid Glass' },
  { id: 'xlab', label: '黑域', source: 'xAI × 轻赛博' },
  { id: 'column', label: '列阵', source: 'ClickHouse 工业数据' },
  { id: 'clay', label: '软体', source: 'Clay Studio' },
] as const
```

- [ ] **Step 3: Implement the component demonstrations**

The page must include:

```text
- Determinate progress ring for suite completion.
- Determinate progress bars per run.
- Local spinner only for a short indeterminate queue action.
- Skeleton placeholders after “模拟加载”.
- One-at-a-time Snackbar with one text action.
- Tabs with tablist/tab/tabpanel roles and arrow-key navigation.
- Backdrop modal before starting a regression run.
- Ctrl/Cmd+K command palette.
- Text decode only for the X-Lab status line.
```

- [ ] **Step 4: Keep all actions demonstrative and reversible**

No network requests or production mutations. “启动回归” opens a confirmation dialog, confirmation advances only local progress state, and environment changes remain local to the page.

### Task 4: Build the four visual systems

**Files:**
- Create: `test-platform-v2/frontend/src/theme-lab/theme-lab.css`

- [ ] **Step 1: Define shared semantic tokens**

Define background, solid content surface, floating surface, ink, muted, line, primary, success, warning, danger, focus, radius, and 140/200/280 ms motion tokens. Interactive targets are at least 40 px desktop and 44 px on touch breakpoints.

- [ ] **Step 2: Define the four theme overrides**

```text
Crystal: cool light canvas, solid white data surfaces, translucent floating nav,
         blue-violet focus, 14-16 px radius.
X-Lab: near-black canvas, sharp 4-8 px geometry, white/cyan signals,
       monospace only for data and status.
Column: neutral white/gray, ClickHouse yellow + black, dense rows, 4-8 px radius,
        terminal/code evidence and strong separators.
Clay: cool lavender canvas, restrained pastel accents, 14-16 px soft forms,
      tactile press and shallow inner/outer depth without childish copy.
```

- [ ] **Step 3: Add responsive and accessibility fallbacks**

At 1080 px collapse the secondary rail; at 820 px convert the sidebar to a horizontal module strip; at 640 px stack actions and metrics. Add visible focus, `prefers-reduced-motion`, `prefers-contrast`, and reduced-transparency-compatible solid fallbacks.

### Task 5: Verify behavior and presentation

**Files:**
- Create: `test-platform-v2/frontend/src/theme-lab/__tests__/ThemeLab.test.tsx`

- [ ] **Step 1: Write behavior tests**

```tsx
it('switches all four themes without losing the active tab', () => {})
it('shows skeleton feedback and a single snackbar', () => {})
it('confirms a regression run through a modal backdrop', () => {})
it('opens the command palette with Ctrl+K', () => {})
```

- [ ] **Step 2: Run focused tests**

Run: `npm test -- --run src/theme-lab/__tests__/ThemeLab.test.tsx`

Expected: all four tests pass.

- [ ] **Step 3: Run project checks**

Run: `npm run typecheck`, then `npm run build`.

Expected: both commands exit with code 0 and Vite emits `theme-lab.html`.

- [ ] **Step 4: Inspect the live page**

Open `http://localhost:5173/theme-lab.html`, exercise all theme switches, Tabs, loading simulation, modal confirmation, Snackbar, and Ctrl/Cmd+K. Check 1440 px, 1024 px, and 390 px widths for overflow and verify there are no console errors.

