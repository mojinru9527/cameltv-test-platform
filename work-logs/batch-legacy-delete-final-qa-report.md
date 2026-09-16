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

Pending merge and release deployment. The final evidence pack will record:

- production health HTTP status
- `sportsadmin` login
- Legacy mutation endpoints returning `410`
- no Legacy writer process in the worker container
- unchanged historical table counts/fingerprints

## Retro card

| 字段 | 内容 |
|---|---|
| 计划耗时 | 1 day planned / 1 day actual |
| 缺陷 | P0=0, P1=0, P2=2 (route ORM guard and migration bridge regression, fixed) |
| 返工次数 | 1 |
| 根因分类 | 技术债 / 工具链 |
| 下次避免 | 删除旧模块后先跑 route-layer/ORM guard，再跑全量回归 |
