# Batch 51 UI Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every verified UI regression left by Batch 50, including component fallback styling, duplicate page shells, responsive/a11y defects, visual anti-patterns, and browser-visible warnings.

**Architecture:** Keep the existing shadcn/Radix component layer as the behavior and accessibility foundation. Make `@/ui` a compatible semantic adapter, use one responsive `PageShell` per routed page, and express visual states through tokens/tone props rather than hard-coded light-theme colors. Verification combines unit tests, static scans, production build diagnostics, and mocked-browser journeys at desktop, tablet, and mobile widths.

**Tech Stack:** React 18, TypeScript, Vite 7, Tailwind CSS, Radix UI, Vitest, Testing Library, Playwright, axe-core.

---

## Scope and acceptance baseline

- Batch 50 explicit carry-over: Badge variant/tone compatibility, PageShell coverage, missing Card/Textarea/Label/Select/Skeleton adapters, non-standard button sizes, TypeScript/build quality, and five-page Obsidian Flow visual acceptance.
- Verified Batch 50 regressions: `@/ui` controls losing styles outside Obsidian Flow, duplicate headers on pages that combine `useObsidianPage` with `PageHeader`, circular chunk warnings, ambiguous motion utility warnings, `NaN` metric output, low-contrast semantic badges, and unlabelled icon actions.
- Historical issues unrelated to Batch 50 remain out of scope unless the same defect is visible in a Batch 50-touched component or one of the seven migrated pages.

### Task 1: Harden semantic primitive adapters

**Files:**
- Modify: `test-platform-v2/frontend/src/ui/primitives/Button.tsx`
- Modify: `test-platform-v2/frontend/src/ui/primitives/Input.tsx`
- Modify: `test-platform-v2/frontend/src/ui/primitives/Badge.tsx`
- Modify: `test-platform-v2/frontend/src/ui/primitives/Progress.tsx`
- Modify: `test-platform-v2/frontend/src/ui/primitives/Card.tsx`
- Modify: `test-platform-v2/frontend/src/ui/primitives/Textarea.tsx`
- Modify: `test-platform-v2/frontend/src/ui/primitives/Label.tsx`
- Modify: `test-platform-v2/frontend/src/ui/primitives/Select.tsx`
- Modify: `test-platform-v2/frontend/src/ui/primitives/Skeleton.tsx`
- Modify: `test-platform-v2/frontend/src/ui/index.ts`
- Create: `test-platform-v2/frontend/src/ui/primitives/__tests__/Primitives.test.tsx`

- [ ] **Step 1: Add tests that render every primitive in default and Obsidian Flow contexts**

```tsx
it('keeps semantic controls styled and labelled in the default UI', () => {
  render(
    <>
      <Button>保存</Button>
      <Input aria-label="名称" />
      <Badge tone="danger">失败</Badge>
      <Progress value={50} />
    </>,
  )
  expect(screen.getByRole('button', { name: '保存' })).toHaveClass('inline-flex')
  expect(screen.getByLabelText('名称')).toHaveClass('border-input')
  expect(screen.getByText('失败')).toHaveClass('ui-badge-danger')
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50')
})
```

- [ ] **Step 2: Run the primitive test and confirm it fails before fallback classes are added**

Run: `npx vitest run src/ui/primitives/__tests__/Primitives.test.tsx`

Expected: FAIL because the Batch 50 adapters expose only `ui-*` classes whose CSS is scoped to `[data-ui-theme="obsidian-flow"]`.

- [ ] **Step 3: Add token-based fallback classes while retaining Obsidian selectors**

```tsx
const variantClassMap: Record<ButtonVariant, string> = {
  primary: 'ui-btn-primary bg-primary text-primary-foreground hover:bg-primary/90',
  secondary: 'ui-btn-secondary border border-input bg-background text-foreground hover:bg-accent',
  ghost: 'ui-btn-ghost text-foreground hover:bg-accent',
  danger: 'ui-btn-danger bg-destructive text-destructive-foreground hover:bg-destructive/90',
}
```

The base control class must include keyboard focus, disabled, loading, and minimum target states. `Progress` must animate `transform: scaleX()` through a CSS custom property instead of `width`.

- [ ] **Step 4: Preserve the established shadcn/Radix APIs for the five new adapters**

`Card` keeps `size` and `CardAction`; `Select` re-exports the Radix compound API; `Label` keeps Radix label semantics; `Skeleton` keeps `SkeletonCircle`, `SkeletonText`, `SkeletonCard`, `SkeletonTable`, and `SkeletonPage`; `Textarea` preserves `aria-invalid` and disabled states.

- [ ] **Step 5: Run focused tests and typecheck**

Run: `npx vitest run src/ui/primitives/__tests__/Primitives.test.tsx && npm run typecheck`

Expected: PASS, exit code 0.

### Task 2: Finish Badge tone migration without invalid DOM props

**Files:**
- Modify: every Batch 51 file reported by `rg -l '<Badge[^>]*variant=' test-platform-v2/frontend/src -g '*.tsx'`
- Modify: `test-platform-v2/frontend/src/ui/primitives/Badge.tsx`

- [ ] **Step 1: Convert static mappings**

```tsx
variant="default"     -> tone="neutral"
variant="destructive" -> tone="danger"
variant="outline"     -> tone="neutral"
variant="secondary"   -> tone="neutral"
```

- [ ] **Step 2: Convert conditional mappings semantically**

```tsx
variant={failed ? 'destructive' : 'default'}
```

becomes:

```tsx
tone={failed ? 'danger' : 'neutral'}
```

- [ ] **Step 3: Keep `variant` only as a deprecated compatibility alias inside `BadgeProps`**

The implementation destructures `variant` so it is never forwarded to the DOM. New and migrated consumers use `tone`.

- [ ] **Step 4: Verify migration coverage**

Run: `rg -n '<Badge[^>]*variant=' test-platform-v2/frontend/src -g '*.tsx'`

Expected: no consumer matches.

### Task 3: Replace duplicate headers with one responsive PageShell

**Files:**
- Modify: `test-platform-v2/frontend/src/ui/components/PageShell.tsx`
- Modify: `test-platform-v2/frontend/src/ui/hooks/useObsidianPage.tsx`
- Modify: `test-platform-v2/frontend/src/pages/environment/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/defect/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/testcase/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/testplan/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/report/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/trace/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/requirement/index.tsx`
- Create: `test-platform-v2/frontend/src/ui/components/__tests__/PageShell.test.tsx`

- [ ] **Step 1: Write PageShell structure tests**

```tsx
it('renders one accessible page heading and wraps actions on narrow screens', () => {
  render(
    <PageShell title="缺陷管理" description="追踪质量缺陷" actions={<button>新建</button>}>
      <div>列表</div>
    </PageShell>,
  )
  expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
  expect(screen.getByTestId('page-shell-actions')).toHaveClass('flex-wrap')
})
```

- [ ] **Step 2: Implement a single semantic shell**

The header uses `text-foreground`, `text-muted-hc`, `bg-card`, and `border-border`; actions use `flex-wrap`; mobile layout stacks title and actions; no hard-coded hex values, fluid product headings, decorative eyebrow, spotlight, or nested surface wrapper are allowed.

- [ ] **Step 3: Migrate the seven pages**

Each route renders exactly one `<PageShell>` and removes both `useObsidianPage` and `PageHeader`. Existing page actions move into the `actions` prop; existing data/loading/error containers remain unchanged.

- [ ] **Step 4: Remove the circular index import from `useObsidianPage`**

```tsx
import { useUiTheme } from '../themes/UiThemeProvider'
import { ObsidianListPage, type ObsidianListPageProps } from '../patterns/ObsidianListPage'
```

- [ ] **Step 5: Verify one heading per route**

Run the PageShell test plus the browser matrix in Task 6. Expected: one `h1` on every audited route.

### Task 4: Remove verified visual and motion defects

**Files:**
- Modify: `test-platform-v2/frontend/src/globals.css`
- Modify: `test-platform-v2/frontend/src/ui/tokens/primitives.css`
- Modify: `test-platform-v2/frontend/src/ui/themes/obsidian-flow.css`
- Modify: `test-platform-v2/frontend/src/ui/components/SpatialChain.tsx`
- Modify: `test-platform-v2/frontend/src/ui/patterns/Inspector.tsx`
- Modify: `test-platform-v2/frontend/src/ui/patterns/ObsidianWorkbench.tsx`
- Modify: `test-platform-v2/frontend/src/ui/patterns/ObsidianListPage.tsx`
- Modify: `test-platform-v2/frontend/src/components/TriagePanel.tsx`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/DebugTab.tsx`
- Modify: `test-platform-v2/frontend/src/pages/release-bundles/components/DiffReviewPanel.tsx`
- Modify: `test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx`
- Modify: `test-platform-v2/frontend/src/pages/requirement/ExtractionModal.tsx`

- [ ] **Step 1: Replace gradient text with a solid semantic foreground**

`.sidebar-brand` uses `color: var(--sidebar-primary)` and `.gradient-text` uses `color: var(--primary)` without `background-clip` or transparent text fill.

- [ ] **Step 2: Replace spring/bounce transitions**

`cubic-bezier(0.34, 1.56, 0.64, 1)` becomes `var(--ease-out-expo)` or `cubic-bezier(0.19, 1, 0.22, 1)`. `transition: all` becomes a list of the properties that actually change.

- [ ] **Step 3: Remove decorative side-stripe cards**

Triage, diff review, requirement issue, and extraction issue surfaces use a full semantic border or tone badge. Tree and real timeline connectors remain because their line communicates hierarchy/sequence.

- [ ] **Step 4: Replace the response-code badge's hard-coded gray-on-color classes**

```tsx
<Badge tone={isSuccess ? 'success' : hasResponse ? 'danger' : 'neutral'}>
  {result.status_code || '无响应'}
</Badge>
```

- [ ] **Step 5: Resolve ambiguous duration utilities**

Use `duration-200` for product-state transitions and property-specific transition classes. Re-run production build and require no `duration-[180ms]` warning.

- [ ] **Step 6: Re-run the impeccable detector**

Run: `node C:/Users/26029/.codex/skills/impeccable/scripts/detect.mjs --json test-platform-v2/frontend/src`

Expected: no gradient-text, bounce-easing, gray-on-color, non-hierarchical side-tab, or layout-transition findings in the changed production UI.

### Task 5: Fix browser-visible warnings and action labels

**Files:**
- Modify: `test-platform-v2/frontend/src/components/StatCard.tsx`
- Modify: icon action call sites reported by `rg -n '<Button[^>]*size="icon' test-platform-v2/frontend/src -g '*.tsx'`
- Create or modify focused tests next to the changed components.

- [ ] **Step 1: Normalize non-finite metric values**

```tsx
const displayValue =
  typeof value === 'number' && !Number.isFinite(value) ? '—' : value
```

- [ ] **Step 2: Add accessible names to icon-only actions**

Every icon-only button has `aria-label`; `title` can remain as supplemental hover help but is not the accessible-name strategy.

- [ ] **Step 3: Run Vitest and require no React `NaN` warning**

Run: `npm test -- --reporter=dot`

Expected: 0 failed tests and no `Received NaN for the children attribute` warning.

### Task 6: Add and run full UI browser regression

**Files:**
- Create: `test-platform-v2/frontend/e2e/batch51-ui-regression.spec.ts`
- Create: `test-platform-v2/work-logs/evidence/batch-51-ui-completion/README.md`
- Create: screenshots under `test-platform-v2/work-logs/evidence/batch-51-ui-completion/`

- [ ] **Step 1: Mock authentication and the page APIs in Playwright**

Persist the `cameltv-auth` store with a fixture user, project, and `*` permission. Fulfil page APIs with stable empty-state or small-list envelopes; capture console errors and duplicate GET counts.

- [ ] **Step 2: Test all seven routes at three viewports**

Routes: `/environment`, `/defect`, `/testcase`, `/testplan`, `/report`, `/trace`, `/requirement`.

Viewports: `1440x900`, `768x1024`, `390x844`.

For each route assert:

- exactly one visible `h1`;
- no document-level horizontal overflow;
- header actions remain visible and keyboard reachable;
- zero console errors;
- axe WCAG A/AA violations equal `[]`.

- [ ] **Step 3: Capture the five Batch 50 acceptance pages**

Capture `/workbench`, `/trace`, `/testcase`, `/environment`, and `/theme-lab` in Obsidian Flow at desktop and mobile widths.

- [ ] **Step 4: Run the browser suite**

Run: `BASE_URL=http://localhost:5174 npx playwright test e2e/batch51-ui-regression.spec.ts --project=chromium`

Expected: all scenarios PASS with evidence screenshots.

### Task 7: Full gates and delivery evidence

**Files:**
- Create: `test-platform-v2/work-logs/batch-51-ui-completion-qa-report.md`
- Create: `test-platform-v2/work-logs/batch-51-ui-completion-leader-verdict.md`
- Modify: `test-platform-v2/work-logs/batch-51-component-adaptation-*.md` only where prior claims are contradicted by verified evidence.

- [ ] **Step 1: Run required frontend gates**

Run:

```powershell
npm run typecheck
npm run build
npm test -- --reporter=dot
npm run test:a11y
```

Expected: all exit code 0.

- [ ] **Step 2: Record exact commands, exits, warnings, screenshots, and issue closure**

The QA report distinguishes baseline warnings from final results and lists every P0-P3 item with evidence.

- [ ] **Step 3: Review the final diff and scan for debris**

Run:

```powershell
git diff --check origin/main...HEAD
rg -n 'console\.log|debugger|breakpoint|print\(' test-platform-v2/frontend/src
rg --files | rg '\.(bak|orig)$|~$|\.db$|\.sqlite$'
```

Expected: no task-introduced debug output, secrets, backups, databases, or unrelated files.

- [ ] **Step 4: Stop before push**

Present the repository-mandated change summary and exact push confirmation question. Do not push or create a PR until the user explicitly authorizes that one push.
