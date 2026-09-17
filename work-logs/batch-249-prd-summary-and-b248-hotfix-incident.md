# Batch 249 — 发布控制面强制迁移（PRD 草案）+ Batch 248 runner 热修事故记录

> Date: 2026-09-17 | 执行器：Codex（用户确认）| 分支：`feature/batch-249-release-console-migration` | base：`origin/main` @ 156adea2

## 0. 本批次范围（用户已选 B，S1 经实证取消）

### S1 —— ❌ 取消（实证：无需合并）

原计划"把 `feature/release-console` 合入主干"。试探合并后发现：

- `deploy/release-console/*` 在两侧都是**新增文件**（add/add 冲突）→ 说明 main 上**早已存在**该控制面服务；
- 且 **main 的版本更新更完整**：`app.py` 476 行（分支 346）、`tencent_executor.py` 337 行（分支 235），另含分支没有的
  `capacity.py` / `release_artifacts.py` / `release_cleanup.py` 与 5 个测试文件；
- 今天拦下我的"磁盘容量不足"门禁即来自 main 的 `capacity.py`。

结论：`feature/release-console` 是**已被 main 取代的历史残留分支**（仅本地存在、落后 148 提交、从未推送）。
→ S1 无事可做；建议单独清理该分支与对应 worktree（属文档/清理动作，不在本批代码范围）。

### S2 —— 本批主体：控制面"独占数据库迁移作业"（ADR-0015 §4）

在 main 的 `deploy/release-console/` 上实现。现状（已核实的缺口）：

```text
deploy/release-console/README.md:112  "Every release must verify the previous image against the new schema…"
deploy/release-console/tencent_executor.py:94  "…never migrate the database down"
deploy/release-console/static/index.html:130  database:{ alembic_heads:['see-verified-head'], target_revision:'see-verified-head' }
```

即：控制面**只有文字约定，没有任何迁移执行/校验代码**，manifest 里也是占位值 `see-verified-head`——
这正是 2026-09-17 发布出现"代码已上线、schema 未迁移（`ai_jobs.model_name` 不存在 → 500）"的直接原因。

PM 任务（每项 30–60 分钟）：

| # | 任务 | 验收标准 | 涉及文件 |
|---|---|---|---|
| S2-1 | manifest 的 `database` 用真实 revision：从待发布镜像内 `alembic heads` 读取并写入 | manifest 中 `target_revision`/`alembic_heads` 为真实单头，非 `see-verified-head` | `deploy/release-console/*`（manifest 构造处）、`static/index.html` 模板 |
| S2-2 | 新增 `migrations.py`：在目标机执行 `alembic upgrade <target>` + `alembic current` 校验单头 | 失败即抛错并阻止后续 deploy 步骤 | `deploy/release-console/migrations.py`（新） |
| S2-3 | 在 deploy 序列中插入迁移步骤（迁移 → 校验 → 起 api → 起 frontend），失败中止并保持旧容器可回滚 | 顺序可测；失败路径有单测 | `deploy/release-console/tencent_executor.py` |
| S2-4 | 回滚路径**不**执行 down 迁移（沿用现有约定），并断言迁移步骤被跳过 | 与既有 `test_rollback_skips_old_image_migration_launcher` 一致 | 同上 + `tests/` |
| S2-5 | 单测：迁移成功/失败/单头校验失败/回滚跳过 四类 | 全部通过，且不依赖真实服务器（mock 远端执行器） | `deploy/release-console/tests/test_migrations.py`（新） |
| S2-6 | README 更新：迁移作业的位置、失败语义、与回滚的关系 | 文档与实现一致 | `deploy/release-console/README.md` |

### S3 —— 已完成（Batch 248 交付缺陷）

本地 Agent CLI 缺登录：register/agents:health/import 需要用户 JWT，而 CLI 只发 agent token → 必然 401。
已新增 `login` 子命令并在生产验证 `login → register → doctor → next → report → import` 全通。

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
