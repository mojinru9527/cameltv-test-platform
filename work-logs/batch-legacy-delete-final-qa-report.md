# QA Report — Legacy delete final (PR-09)

date: 2026-09-16
executor: codex

## Scope

Final removal of the Legacy API/Plan executors and their write entry points,
while preserving historical read-only data and mappings.

## Local evidence

| Check | Result |
|---|---|
| `ruff check app/ --select F821` | PASS |
| Focused PR-09 tests | PASS |
| `pytest tests -q --ignore=tests/test_session_credentials.py` | PASS — 2662 passed, 51 skipped, 1 xfailed |
| `pytest tests/test_session_credentials.py -q` | KNOWN BASELINE — 3 failed, 3 passed |
| `pytest tests/test_execution_architecture_guard.py -q` | PASS — 13 passed |
| `git diff --check` | PASS |

Known baseline failures are unchanged and unrelated to this batch:

```text
test_configured_fetch_returns_token_and_key
test_form_encoded_credentials_fetch
test_execute_with_session_injection
```

No new failures remain in the full suite excluding that known baseline.

## Production verification

Release `release-20260916-0003` (Git SHA
`72a3002d01b9bc45e004695d0d46368e0892200a`, deployment
`e3f4b92c95064e7db7230548c79b0c6e`) reached `PRODUCTION_VERIFIED`.

- all six production services healthy; external health HTTP 200
- `sportsadmin` login returned `user_id=4`
- Legacy task cancel/retry/delete and runner claim all returned `410`
- final code present in backend, runner and aitde-worker images; deleted
  executor files absent
- no `api-task-worker`, `plan-execution-worker`, import traceback or
  `ModuleNotFound` entries in the newly deployed worker logs
- Legacy table counts/fingerprints remained exactly at baseline and
  `drift=false`; new rows and updated rows were both zero

## Retro card

| 字段 | 内容 |
|---|---|
| 计划耗时 | 1 day planned / 1 day actual |
| 缺陷 | P0=0, P1=0, P2=2 (route ORM guard and migration bridge regression, fixed) |
| 返工次数 | 1 |
| 根因分类 | 技术债 / 工具链 |
| 下次避免 | 删除旧模块后先跑 route-layer/ORM guard，再跑全量回归 |
