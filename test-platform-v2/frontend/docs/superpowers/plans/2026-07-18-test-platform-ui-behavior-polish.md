# Test Platform UI Behavior Polish Implementation Plan

> **For Codex:** Execute each task in order and keep all changes inside the existing frontend behavior layer.

**Goal:** Implement the five requested interaction and layout refinements without changing API contracts or existing business workflows.

**Architecture:** Extend the current React/shadcn components in place. Keep data loading and mutations unchanged, add a controlled horizontal service-tab viewport, render single-case responses in a Radix dialog, constrain requirement source cells with a fixed table layout, derive the case-list reserved height from the selected page size, and reuse the existing step formatter for edit-form display.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Radix/shadcn UI, Vitest, Testing Library, Playwright.

---

### Task 1: Horizontally sliding service tabs

**Files:**
- Modify: `src/pages/apitest/components/AssetTab.tsx`
- Modify: `src/pages/apitest/components/AssetTab.test.tsx`

1. Add a horizontal viewport ref and left/right overflow state.
2. Add accessible previous/next controls that call smooth `scrollBy` and disable at each edge.
3. Keep touchpad/touch horizontal scrolling and automatically center the selected service tab.
4. Add component tests for the controls and scrolling behavior.

### Task 2: Show API-case response only after execution

**Files:**
- Modify: `src/pages/apitest/components/ApiCaseTab.tsx`
- Modify: `src/pages/apitest/components/ApiCaseTab.test.tsx`

1. Remove the persistent response column so the case list uses the full width.
2. Track the executed case and controlled response-dialog state.
3. Open the response dialog only after the single-case request resolves or returns an execution error.
4. Preserve environment selection and batch-execution behavior.
5. Test that no response area exists initially and that the correct modal opens after execution.

### Task 3: Keep requirement records within one screen width

**Files:**
- Modify: `src/pages/requirement/index.tsx`

1. Switch the document table to a fixed layout with screen-relative column widths.
2. Truncate source values in their cell while preserving the full value through the link target and native title tooltip.
3. Prevent non-link source values from expanding the table.

### Task 4: Reserve list height for selected page size

**Files:**
- Modify: `src/pages/testcase/index.tsx`

1. Derive a minimum table viewport height from the current 20/50/100 page-size selection.
2. Apply the minimum height only to the data-list container so pagination remains below it.
3. Expose a test-friendly label/value for browser verification.

### Task 5: Numbered multiline steps in the edit dialog

**Files:**
- Modify: `src/pages/testcase/caseListFormatters.ts`
- Modify: `src/pages/testcase/CaseDrawer.tsx`
- Modify: `src/pages/testcase/__tests__/caseListFormatters.test.ts`
- Modify: `src/pages/testcase/__tests__/CaseDrawer.test.tsx`

1. Add a formatter that converts JSON, legacy JSON-like, or plain step values to newline-separated Chinese-numbered actions.
2. Apply it only when hydrating an existing case into the edit form.
3. Update the textarea hint to match the visible numbered-line format.
4. Test formatting and edit-mode field hydration.

### Task 6: Verify the complete change

**Files:**
- Verify all modified files above.

1. Run focused Vitest suites for API assets, API cases, step formatters, and case drawer.
2. Run frontend type checking and production build.
3. Use Playwright against `http://localhost:5173` with backend `http://localhost:8000` to inspect the changed pages, console errors, and key click flows without bypassing authentication.
4. Review the final diff to ensure unrelated user changes remain untouched.
