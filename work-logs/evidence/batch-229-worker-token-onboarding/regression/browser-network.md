# Batch 229 Browser And Network Evidence

> Playwright CLI against `http://127.0.0.1:5199` -> Vite proxy -> FastAPI `127.0.0.1:8029`; no API route mocks.

## Runtime Discovery

- Logged in through the frontend login form and selected the seeded sports project.
- Opened `Durable Runtime` from the visible navigation, then clicked `生成 Worker Token`.
- Deep link resolved to `/system?tab=tokens&purpose=worker`; `API Token` was active and `Worker 执行节点` was preselected.
- Runtime first load issued exactly one GET each for workers, workflows, approvals, secret refs and policy profiles; all returned 200.
- Console errors: 0. Document horizontal overflow: 0 at 768 and 390 widths.

## One-Time Creation

The success dialog was inspected and closed inside one Playwright operation so no snapshot persisted the secret.

```json
{"status":200,"createRequests":1,"workerPurpose":true,"oneTimeSecretPresent":true,"exportsBackendUrl":true,"exportsApiToken":true,"hasLauncherCommand":true}
```

After close, only the prefix and localized `Worker 注册` scope remained in the table; the full secret was absent from the DOM.

## Revoke Lifecycle

```json
{"disableStatus":200,"disabled":true,"putRequests":1,"deleteStatus":200,"deleteRequests":1,"emptyAfterDelete":true}
```

The local QA Token was deleted before evidence capture completed.

## Responsive Findings And Fixes

- P2: System tabs originally measured 480px inside a 358px mobile content area and clipped the last entry. The first scroll attempt shrank labels; the first wrap attempt retained a 32px parent height and overlapped content. Final result uses a 94px two-row list at 390/768 and 44px touch targets.
- P2: At 768px the project selector shrank to 70px while its label rendered at 123px. Header text actions now remain icon-only below `lg`; final selector width is 200px with a 57px gap before the action group.
- Final screenshots were visually inspected. No modified-page text overlap remains.
