# Batch 229 Regression Results

> Date: 2026-09-04 | All commands ran in the isolated Codex worktree.

| Check | Result |
|-------|--------|
| Backend focused Worker/Token/security | exit 0; 67 passed |
| Backend full pytest | exit 0; 2425 passed, 49 skipped, 1 xfailed, 0 failed; 605.75s |
| Backend app import | exit 0; `APP_IMPORT_OK` |
| Ruff F821 | exit 0; all checks passed |
| Alembic single-head + revision ids | exit 0; 8 passed |
| Frontend focused after browser findings | exit 0; affected tests passed |
| Frontend full Vitest | exit 0; 140 files, 629 tests passed |
| Frontend typecheck | exit 0 |
| Frontend lint | exit 0 |
| Frontend production build | exit 0; 3667 modules transformed |
| C-condition audit | exit 0; 0 hard errors, 0 warnings |
| Common-bug scan | PASS_WITH_WARN; 0 HARD, 330 repository-wide WARN; changed files matched 0 WARN |
| Dev gate G0-G2 | PASS_WITH_WARN; F821/typecheck/lint passed; route guards 4 passed |
| Git whitespace check | exit 0 after PM artifact cleanup |

## Focused Coverage

- Worker Token without Cookie/project header succeeds and updates `last_used_at`.
- CI `trigger` Token receives 403; disabled Worker Token receives 401.
- Worker registry, capability routing, stale/offline state and security regression remain green.
- Runtime admin/read-only entry rendering, System deep link, purpose mapping, Worker setup and Token lifecycle UI are covered.

## Environment Limit

`start-worker.sh` could not be executed locally because WSL has no `/bin/bash` and Docker Desktop daemon is unavailable. The 7 launcher/heartbeat tests passed, including the assertion that the empty-Token guard precedes both child-process starts. This is not evidence of a production Worker being online.
