# P0-4 本地端到端验证（2026-11-09 22:24 +08:00）

> 目标：证明 `/uitest` 在 `UITEST_EXECUTION_MODE=node` 下，由 `cameltv-node` 真实执行 Playwright spec，
> 并由控制面把结果投影回 `UiTestRun`（**不是** mock、**不是** 伪造通过）。

## 环境

| 项 | 值 |
|----|-----|
| 控制面 | 本机 `uvicorn app.main:app --host 127.0.0.1 --port 8025` |
| DB | SQLite `data/e2e-p04.db`（fresh，seed admin + project 1） |
| 模式 | `UITEST_EXECUTION_MODE=node` |
| 节点 | `scripts/node/cameltv_node/cli.py up --once --capabilities api web ui` |
| 浏览器 | Playwright Chromium（本地 `ms-playwright`，`--project chromium`） |
| 用例 | `test-platform-v2/backend/tests/playwright/specs/p0-4-node-e2e.spec.ts`（data URL，自包含，无需外网） |

## 链路

```text
POST /api/v1/ui-tests/{id}/trigger          (mode=node)
  → ui_job_dispatch.build_payload            (读 spec + spec_guard + env)
  → ExecutionJob(kind="ui")  #1
节点 CLI up --once
  → POST /execution-jobs/claim               → running
  → run_spec_files（npx playwright test --project chromium）
  → POST /execution-jobs/{id}/evidence       （manifest + report + results）
  → POST /execution-jobs/{id}/report         → completed
控制面 report 钩子
  → sync_run_from_job → UiTestRun.status=done
```

## 结果

| 项 | 结果 |
|----|------|
| ExecutionJob | `kind=ui`，节点 `local-e2e` 认领，attempt=1 |
| 节点执行 | `1/1 pass`，耗时 ≈3.95s |
| UiTestRun | `status=done`，`result={"total":1,"passed":1,"failed":0,"evidence_files":3}` |
| 证据目录 | `storage/execution-evidence/job-1/attempt-1` |
| 产物 API | `GET /ui-tests/runs/1/artifacts` 返回 4 个文件（manifest.json / report.json / results.json / .last-run.json） |
| 安全 | spec 在控制面过 `spec_guard`；节点只收相对路径；env 剔除 SECRET/TOKEN/PASSWORD |

## 复现命令

```powershell
# 1) 控制面
$env:ENVIRONMENT='development'; $env:DATABASE_URL='sqlite:///./data/e2e-p04.db'
$env:SECRET_KEY=('<64 chars>'); $env:AUTO_CREATE_TABLES='true'
$env:UITEST_EXECUTION_MODE='node'; $env:AI_ENABLED='false'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8025

# 2) 注册节点（admin cookie + X-Project-Id）→ 拿到一次性 token
# 3) 创建/触发 UI 任务（test_spec=specs/p0-4-node-e2e.spec.ts）
# 4) 节点执行
python scripts/node/cameltv_node/cli.py up --once \
  --node-id local-e2e --capabilities api web ui \
  --work-dir $env:TEMP\p04-node-e2e-work
```

## 未完成（P0-4 不能因此标 pass）

- 控制面 Dockerfile 仍安装 Chromium；
- 蓝湖证据截图 / XHR 采集 / Playground 仍依赖控制面浏览器；
- 真实生产节点（非本机）未验收。

→ 只有以上三项处理完，才写 `P0-4-control-plane-no-browser.json`。
