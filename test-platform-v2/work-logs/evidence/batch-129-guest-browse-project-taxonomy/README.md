# Batch 129 QA Evidence

## Environment

- Branch: `feature/batch-129-guest-browse-project-taxonomy`
- Worktree: `F:/CamelTv-worktrees/codex-batch-129-guest-browse-project-taxonomy`
- Frontend: `http://127.0.0.1:5192`
- Backend: `http://127.0.0.1:8022`
- Browser: visible Chromium driven by Playwright
- Backend data: batch-isolated SQLite (`platform-batch-129-guest-browse-project-taxonomy.db`)

## Browser evidence

| File | Evidence |
|------|----------|
| `guest-platform-home.png` | Public platform catalog is visible before login |
| `guest-testcase-preview.png` | Desktop guest can enter the Test Case Service capability page |
| `guest-login-gate.png` | Login dialog opens only after the explicit “登录后使用” action |
| `registered-empty-projects.png` | Public registration succeeds and redirects to the empty project page |
| `no-project-guidance.png` | Logged-in user without a project sees the create-project guide |
| `guest-testcase-tablet.png` | Tablet guest preview, no horizontal overflow |
| `guest-testcase-mobile.png` | Mobile guest preview, no horizontal overflow |
| `no-project-guidance-mobile.png` | Mobile no-project guide, no horizontal overflow |
| `browser-result.json` | Desktop assertions, request failures and console errors |
| `responsive-result.json` | Tablet/mobile overflow, API and console assertions |

The browser assertions recorded zero protected business API requests for guest previews and zero business API requests after a no-project user navigated to `/testcase`. Both runs recorded zero console errors and zero failed requests.

## Taxonomy evidence

`taxonomy-audit.json` applies the production classifier to the Batch 110 audit source. All 476 legacy functional cases across 31 domains are classified: 227 user-facing and 249 operations-admin cases; `other_domains` is empty.

The classifier mapping is additionally locked by 31 parameterized backend tests and a list/taxonomy consistency test.
