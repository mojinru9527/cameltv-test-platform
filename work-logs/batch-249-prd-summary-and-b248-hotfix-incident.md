# Batch 249 — 发布控制面强制迁移（PRD 草案）+ Batch 248 runner 热修事故记录

> Date: 2026-09-17 | 执行器：Codex（用户确认）| 分支：`feature/batch-249-release-console-migration` | base：`origin/main` @ 156adea2

## 0. 本批次范围（用户已选 B）

1. **S1**：把仅本地存在的 `feature/release-console`（1 个提交，落后 main 148）合并进主干（worktree `F:\CamelTv-safe-backup\wt-release-console`，`709d9ccc`）。
2. **S2**：在控制面实现 ADR-0015 §4 的**独占数据库迁移作业**（manifest 用真实 `target_revision`，publish 前置校验单头并执行迁移，失败即中止）。
3. **S3**：修复 Batch 248 交付缺陷 —— 本地 Agent CLI 缺登录（register/health/import 需用户 JWT）。

## 1. 事故记录：Batch 248 runner 热修（H1）

### 1.1 触发

Batch 248 发布（`release-20260917-0003`）时，我判断"runner 代码路径未变"而**沿用 0001 已验证 runner 镜像**。实际：

```
app/core/execution_dispatch.py
  RUNNER_ENDPOINTS = { 'app.api.v1.requirement_ai_generate': {'generate_test_cases'}, ... }
  ExecutionRoute → 当 WORKER_EXECUTION_ENABLED=false 时把该请求代理到 http://runner:8000
```

→ `POST /requirements/{id}/generate` 由 runner 执行；runner 是旧代码（无派发分支）→ 仍调云端 LLM → `code=400 "AI 调用失败（提供方…）"`。
（`extract` 不在转发面内，因此在 api 本地执行正常 —— 这解释了"一半正常一半报错"的现象。）

### 1.2 第一次热修失败（导致生产 502）

补丁镜像只 `COPY app/`，但 **runner 容器的入口脚本会先执行 `alembic upgrade head`**：

```
Running database migrations...
FAILED: Can't locate revision identified by '20260922_ai_agent_token'
```

→ runner 不健康 → `dependency runner failed to start` → backend/frontend/worker 未启动 → 外部 502。

**恢复**：控制面 `POST /api/deployments/{id}/rollback {image_tag:"release-20260917-0003"}` →
`PROD_ROLLED_BACK`，6 容器全部 Healthy，外部 `/api/v1/open/health` = ok。

### 1.3 正确热修（release-20260917-0005，PRODUCTION_VERIFIED）

补丁 Dockerfile 改为与 batch-247 同口径（含 alembic）：

```dockerfile
FROM cameltv-tp-runner:release-20260917-0003
USER root
COPY --chown=cameltv:cameltv test-platform-v2/backend/app /app/app
COPY --chown=cameltv:cameltv test-platform-v2/backend/alembic /app/alembic
COPY --chown=cameltv:cameltv test-platform-v2/backend/alembic.ini /app/alembic.ini
USER cameltv:cameltv
```

**发布前预检（新增、必须保留）**：

```bash
docker run --rm --entrypoint python <img> -m alembic heads          # 必须单头
docker run --rm --entrypoint sh <img> -c "grep -c local_agent_mode /app/app/api/v1/requirement_ai_generate.py"
docker run --rm --entrypoint sh <img> -c "ls /app/alembic/versions | grep -c <新 revision>"
```

结果：`release-20260917-0005` → `PRODUCTION_VERIFIED`；`generate` 与 `extract` 均返回 `mode=local_agent`。

### 1.4 生产验收（0005 实测）

| 检查 | 结果 |
|---|---|
| `POST /requirements/20/generate` | `code=0, mode=local_agent, job_id=3` |
| `POST /requirements/20/extract` | `code=0, mode=local_agent, job_id=4` |
| CLI `next --out job.json` | claimed job 3（generate / document_id=20） |
| CLI `report --file result.json --model local-chatgpt-5` | completed |
| CLI `import --job 3` | **imported 2, skipped 0** |
| 用例库 | total 8（含本地模型产出的 2 条） |
| 外部 | `/api/v1/open/health` = ok / v2.3.0 |

## 2. S3 已完成的修复（Batch 248 交付缺陷）

CLI 原先只发 `X-AI-Agent-Token`，而 register/agents/health/import 需要**用户 JWT** → 必然 401。
现新增 `login` 子命令（账号+密码 → JWT 存 `~/.cameltv-ai-agent.json`），并在请求头带上 `Authorization`；
`doctor` 明确报告 `jwt_configured`，缺失时给出可执行提示。生产已验证：`login → register → doctor → next → report → import` 全通。

## 3. 待办（本批次后续切片）

- S1：`feature/release-console` 合入主干（含与 main 的 148 提交差异消解）。
- S2：控制面独占迁移作业 + `database.target_revision` 用真实 revision + publish 前置校验。
- 新增条件（待 Leader 入库）：**沿用旧镜像前必须核对转发面（RUNNER_ENDPOINTS）**、**补丁镜像必须包含 alembic/versions**。
