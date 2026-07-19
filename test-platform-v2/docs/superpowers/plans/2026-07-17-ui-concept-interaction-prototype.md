# UI Concept Interaction Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an isolated, clickable comparison prototype for the approved bright enterprise and dark operations UI concepts without changing existing routes, APIs, or business behavior.

**Architecture:** Add a second Vite HTML entry that mounts a self-contained React prototype from `src/ui-concepts/`. Both concepts share the same mock information model but implement different interaction priorities: concept A emphasizes everyday management and contextual drawers, while concept B emphasizes live execution, multi-pane inspection, and operational controls. The production application entry and router remain untouched.

**Tech Stack:** React 18, TypeScript, Vite 5, CSS custom properties, Lucide React, Vitest, Testing Library, Playwright

---

### Task 1: Add the isolated prototype entry

**Files:**
- Create: `test-platform-v2/frontend/ui-concepts.html`
- Create: `test-platform-v2/frontend/src/ui-concepts/main.tsx`

- [ ] **Step 1: Create the HTML entry**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CamelTv UI 交互方案</title>
  </head>
  <body>
    <div id="ui-concepts-root"></div>
    <script type="module" src="/src/ui-concepts/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Mount the prototype without importing the production router**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { InteractionPrototype } from './InteractionPrototype'
import './ui-concepts.css'

ReactDOM.createRoot(document.getElementById('ui-concepts-root')!).render(
  <React.StrictMode><InteractionPrototype /></React.StrictMode>,
)
```

- [ ] **Step 3: Verify the existing app remains the default entry**

Run: `npm run typecheck`
Expected: TypeScript exits with code 0 and `src/main.tsx` remains unchanged.

### Task 2: Implement the shared interaction model

**Files:**
- Create: `test-platform-v2/frontend/src/ui-concepts/InteractionPrototype.tsx`
- Create: `test-platform-v2/frontend/src/ui-concepts/FadeContent.tsx`

- [ ] **Step 1: Define explicit prototype state**

```tsx
type Concept = 'bright' | 'ops'
type Surface = 'overview' | 'cases' | 'execution' | 'api'

const [concept, setConcept] = useState<Concept>('bright')
const [surface, setSurface] = useState<Surface>('overview')
const [selectedRunId, setSelectedRunId] = useState('RUN-5128')
const [drawerMode, setDrawerMode] = useState<'detail' | 'create' | null>('detail')
const [commandOpen, setCommandOpen] = useState(false)
```

- [ ] **Step 2: Add a restrained React Bits-style content transition**

```tsx
export function FadeContent({ transitionKey, children }: PropsWithChildren<{ transitionKey: string }>) {
  return <div key={transitionKey} className="fade-content">{children}</div>
}
```

- [ ] **Step 3: Make all interaction controls semantic**

Use native `button`, `select`, `input`, `table`, `dialog`, `aria-current`, `aria-expanded`, and visible focus styles. Keep every icon-only target at least 40px visually and 44px by hit area.

- [ ] **Step 4: Add the comparison controller**

The controller provides labeled buttons `方案一 · 明亮企业` and `方案二 · 深色运维`. Changing concept preserves the current surface so users compare the same task in both visual systems.

### Task 3: Implement concept A interactions

**Files:**
- Modify: `test-platform-v2/frontend/src/ui-concepts/InteractionPrototype.tsx`
- Create: `test-platform-v2/frontend/src/ui-concepts/ui-concepts.css`

- [ ] **Step 1: Add stable navigation and project context**

Clicking a navigation item changes only the workspace; project switching displays a confirmation toast and preserves filters.

- [ ] **Step 2: Add management-first table interaction**

```tsx
<tr onClick={() => { setSelectedRunId(row.id); setDrawerMode('detail') }}>
  <td>{row.id}</td><td>{row.title}</td><td>{row.status}</td>
</tr>
```

Selected rows open a non-modal right inspector. Search and status filters update the visible rows; the user never loses the list scroll position.

- [ ] **Step 3: Add creation and command flows**

`新建用例` opens a right drawer with visible labels. `Ctrl/Cmd + K` opens a command palette that navigates between mock surfaces.

### Task 4: Implement concept B interactions

**Files:**
- Modify: `test-platform-v2/frontend/src/ui-concepts/InteractionPrototype.tsx`
- Modify: `test-platform-v2/frontend/src/ui-concepts/ui-concepts.css`

- [ ] **Step 1: Add operations-first layout**

Use a dense execution table, bottom API/log workspace, and persistent right inspector. The selected run is shared across all panes.

- [ ] **Step 2: Add run controls and live feedback**

`暂停` changes the selected run to paused, `继续` restores running, and `重试` resets progress. Actions announce feedback in an `aria-live="polite"` region.

- [ ] **Step 3: Guard production environment switching**

Selecting `生产环境` opens a confirmation dialog before the context changes; test and staging switch immediately.

- [ ] **Step 4: Add log and response interaction**

Log level filters update visible lines. `发送` enters a short loading state, disables itself, then displays a successful JSON response and latency.

### Task 5: Test and visually verify

**Files:**
- Create: `test-platform-v2/frontend/src/ui-concepts/__tests__/InteractionPrototype.test.tsx`

- [ ] **Step 1: Test the critical comparison flow**

```tsx
render(<InteractionPrototype />)
fireEvent.click(screen.getByRole('button', { name: /方案二/ }))
expect(screen.getByText('实时日志')).toBeInTheDocument()
fireEvent.click(screen.getByRole('button', { name: '暂停' }))
expect(screen.getByRole('button', { name: '继续' })).toBeInTheDocument()
```

- [ ] **Step 2: Run checks**

Run: `npm run typecheck`
Expected: PASS.

Run: `npm run test -- src/ui-concepts/__tests__/InteractionPrototype.test.tsx`
Expected: PASS.

- [ ] **Step 3: Run the prototype and inspect it in a real browser**

Run: `npm run dev -- --host 127.0.0.1`
Expected: Vite serves `http://127.0.0.1:5173/ui-concepts.html`.

Use Playwright to verify concept switching, navigation, project/environment controls, row inspection, drawer behavior, run controls, command palette, and API send feedback at 1440×900 and 1280×800. Capture final screenshots for both concepts.

- [ ] **Step 4: Self-review**

Confirm the prototype contains no production API calls, the production router is unchanged, all content remains usable with reduced motion, and both visual systems preserve the same information and actions.
