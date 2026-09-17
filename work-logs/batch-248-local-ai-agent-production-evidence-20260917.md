# Batch 248 — 本地 AI Agent 闭环 production evidence

> Date: 2026-09-17 | Git SHA: `b30899c826549c7cf2831531ed528945258ea8ce`（Batch 248 合入后 main）

## Deployment

- Release: `release-20260917-0003`
- Deployment id: `9635830357394a55bd91a03d7ad66b75`
- State: `PRODUCTION_VERIFIED`
- Runtime: split topology（api / runner / ai-gateway / frontend）
- Backup before deployment: 控制面 `backup captured (7 kept)`

### 制品构成

| Part | 来源 | config digest |
|---|---|---|
| backend (api) | **新构建**（`--target api`，SHA b30899c8） | `sha256:7ff64bcf7f27…` |
| frontend | **新构建**（含 `/ai-jobs` 页） | `sha256:47d2f3b79b98…` |
| runner | **沿用 `release-20260917-0001` 已验证镜像并 retag** | `sha256:ecbc42647626…` |
| ai-gateway | **沿用 `release-20260917-0001` 已验证镜像并 retag** | `sha256:3ab7ab754376…` |

沿用依据：本批代码变更全部位于 `app/`（由 api 提供）与前端；runner/ai-gateway 代码路径未变，
且 `docker buildx --target runner` 在本机构建失败（见 Findings-1）。
execution config SHA-256: `7a612e43a5a8764d18b6411d1b9a74f7448a6a8eb5a4fa123f9485ac2151c77d`。

## Schema migration（必须手工执行）

发布后 `/api/v1/ai/jobs` 返回 **HTTP 500**：`column ai_jobs.model_name does not exist`。
生产库 alembic 版本停留在 `20260921_ai_job_agent` —— **发布控制面只加载镜像并重建容器，不执行 Alembic 迁移**。

手工修复（纯新增：1 张表 + 2 列，默认值安全，发布前已备份）：

```bash
docker exec cameltv-tp-production-backend-1 python -m alembic upgrade head
```

结果：`alembic_version = 20260922_ai_agent_token (head)`（单头）；`ai_agent_token` 表已建；
`ai_jobs.model_name`、`ai_jobs.imported_at` 已加。

## Production verification（端到端）

| # | 检查 | 结果 |
|---|---|---|
| 1 | `sportsadmin` 登录 | code=0 |
| 2 | `GET /api/v1/ai/jobs` | code=0 |
| 3 | `POST /api/v1/ai/agents/register` | 签发 agent token ✅ |
| 4 | **`POST /requirements/20/extract`** | `mode=local_agent`、`job_id=1`、**无平台 LLM 结果字段** → 平台不再自己推理 |
| 5 | `POST /api/v1/ai/jobs/claim`（`X-AI-Agent-Token`） | claimed=True，job=1 |
| 6 | `POST /api/v1/ai/jobs/1/report`（`model_name=local-chatgpt-verify`） | status=completed |
| 7 | `GET /api/v1/ai/jobs/1` | `model_name` 已持久化（P1-2 修复在生产可验） |
| 8 | Legacy fail-closed：`POST /apitest/runner/claim` | **410**（canonical 仍是唯一可写执行路径） |
| 9 | `POST /api/v1/ai/jobs`（人工建任务） | code=0 |

外部探针：`/health` → ok；`/api/v1/open/health` → `version 2.3.0`；6 个容器全部 healthy；
`https://swiftbugs.cn/ai-jobs` 由前端路由提供。

验收残留已清理：占位 Job #2 已 `cancelled`，无悬空 pending 任务。

## Capacity & rollback

- 发布前服务器可用空间 7.0G < 控制面要求的 8G → 删除**上一个发布** `release-20260917-0001` 的 4 个 tar
  （镜像仍安装于服务器，回滚锚点不依赖 tar；与 batch-247 清理策略一致）→ 8.8G 通过门禁。
- 回滚锚点：`cameltv-tp-*:release-20260917-0001` / `release-20260916-0003` 镜像仍在服务器；
  数据库备份由控制面保留（7 kept）。
- 首次尝试（`release-20260917-0002`）因容量门禁失败，控制面记 `PROD_FAILED` 且不允许原记录重发，
  故以 `release-20260917-0003` 重新登记同一制品（digest 完全一致，仅 RepoTags 变更）。

## Findings（本次发布暴露）

1. **[P1] runner target 无法在本地构建**：`docker buildx --target runner` 在 PLAYWRIGHT 安装步骤 `exit 127`
   （构建阶段缺 `node`）。当前绕过方式=复用已验证 runner 镜像 + 覆盖 `app/` 源码/retag（batch-247 同法）。
   需修 Dockerfile 的 runner target 或将其移出常规发布路径。
2. **[P0] 发布控制面不执行数据库迁移**：本次发布因此上线了"代码需要新 schema、库未迁移"的组合，
   `/ai/jobs` 一度 500。ADR-0015 要求的"独占 migration job"在控制面尚未实现。
   建议：publish 前置步骤强制 `alembic upgrade --sql` 校验 + 迁移作业，或至少在发布清单中把
   `database.target_revision` 从 `see-verified-head` 变为真实 revision 并校验。
