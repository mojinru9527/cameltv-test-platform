# Batch 277a — AIQE §0 P0 代码侧清零：Design Spec

> **部门**：🎨 Design
> **日期**：2026-11-09
> **对象**：`ai_client` / `ai_config` / models / Alembic / `scripts/ci/check-p0-ready.ps1`

---

## 1. `ai_client`：从「网关路由」收敛为「直连」

**Before**：

```text
chat_completions_full
  ├─ ai_gateway.remote（worker 远程委派）
  ├─ ai_gateway.router.resolve_route（cloud / local / shadow / fallback）
  ├─ exact cache（ai_gateway.cache + keys）lookup / store
  └─ shadow 调度（ai_gateway.shadow）
```

**After**：

```text
chat_completions_full
  └─ ai_config_service.resolve(db, project_id)
        └─ _call_configured_full(cfg) → POST {api_base_url}/chat/completions
```

- 失败语义：`AiClientUnavailableError`（无 provider / 重试耗尽）；不再有 fallback 到本地或第二 provider；
- 返回体保留 `route_status="primary"`、`route_origin="project"`，避免调用方读不到字段；
- `is_configured()` 改为 `resolve_config() is not None`，不再依赖路由异常类型。

---

## 2. 删除矩阵

| 对象 | 处理 | 影响面 |
|------|------|--------|
| `app/services/ai_gateway/`（cache/keys/policy/remote/router/runtime/shadow） | 删除 8 文件 | 仅 ai_client / ai_config / embedding 引用，已全部改写 |
| `GET /ai-config/runtime`、`POST /ai-config/runtime/health-check` | 删除 | 前端无调用（api.d.ts 生成类型残留，无运行影响） |
| `GET /ai-config/shadow-policy`、`GET /ai-config/shadow-runs` | 删除 | 同上 |
| `GET /ai-config/cache-stats`、`DELETE /ai-config/cache` | 删除 | 同上 |
| `app/models/ai_job.py`（`AiAgent`） | 删除文件，类迁移到 `execution_node.py::ExecutionNode`，**表名 `ai_agents` 保留** | 节点注册/派发继续可用，零数据迁移 |
| `app/models/ai_shadow_run.py`、`ai_gateway_cache.py` | 删除文件 + 迁移 DROP | 表数据随迁移销毁（downgrade 可重建空表） |
| 配置项：`ai_exact_cache_*`、`ai_gateway_*`、`ai_runtime_mode`、`ai_shadow_*`、`ai_local_*` | 删除 | 仅 config.py 与已删模块引用 |
| `scripts/ai_agent/`（cli + README） | 删除 | 其调用的 `/ai/jobs/*` 端点早已不存在 |
| `scripts/collect_ai_local_baseline.py` | 删除 | 一次性基线脚本，引用已删配置 |
| 测试 `test_ai_gateway_cache` / `test_ai_runtime_routing` / `test_ai_shadow_runtime` | 删除 | 测的是已删模块 |

---

## 3. 迁移设计（P0-2 代码侧）

- 新 revision `20261109_b277_drop_retired_tables`，`down_revision = 20261007_platform_simplification_drop_tables`；
- upgrade：inspector 判断存在 → `DROP INDEX IF EXISTS` → `DROP TABLE IF EXISTS`（幂等）；
- downgrade：按原 b235/b236 migration 的 `create_table` 定义重建两张表 + 索引（`if_not_exists=True`）；
- 同时把 `20261007` 的升级侧 `op.drop_table()` 改为 `op.execute('DROP TABLE IF EXISTS ...')`，满足"所有 DROP 带存在性守卫"；
- 验收：`alembic upgrade head → downgrade -1 → upgrade head` 全 0；downgrade 后两表存在、再 upgrade 后不存在。

---

## 4. TA-001.5 守卫契约（`scripts/ci/check-p0-ready.ps1`）

| 参数 | 默认 | 说明 |
|------|------|------|
| `-RepositoryPath` | cwd | git 仓库根定位 |
| `-EvidenceRoot` | `work-logs/p0-evidence` | P0 证据 JSON 目录 |
| `-MaxEvidenceAgeDays` | 30 | 证据新鲜度 |
| `-SelfTest` | off | 临时骨架验证绿/红两条路径 |

**证据 JSON schema**：

```json
{ "status": "pass", "checked_at": "2026-11-09T10:00:00Z", "evidence": ["..."] }
```

**判定**：

| P0 | 证据文件 | 额外静态检查 |
|----|---------|-------------|
| P0-1 | `P0-1-ai-key-rotation.json` | — |
| P0-2 | `P0-2-backup-restore.json` | upgrade() 禁 `op.drop_table`；`DROP TABLE` 必带 `IF EXISTS` |
| P0-3 | `P0-3-disk-watermark.json` | — |
| P0-4 | `P0-4-control-plane-no-browser.json` | 控制面 `Dockerfile` 不得含 `playwright install` / chromium |
| P0-5 | 无（脚本自证） | app/tests/scripts 残留 0 + Alembic 单 head（AST helper） |

- 退出码：0 = 全绿；1 = 任一失败（fail-closed）；
- SelfTest：临时仓库骨架（空 app/tests/scripts + 无浏览器 Dockerfile + 单个 revision）+ 临时证据 → 全绿必须 0、删一条证据必须 1。

---

## 5. P0-4（277b）设计预告

```text
POST /ui-tests/{id}/trigger
  → ExecutionJob(kind="ui", payload={spec/steps, env, timeout})
  → cameltv-node claim（capabilities 含 web）
  → node 执行 Playwright，上传 evidence（sha256 manifest）
  → 平台 report → 写 UiTestRun(status/result/artifacts 从 ExecutionJob 投影)
  → 控制面 Dockerfile 移除 playwright install
```

保持前端 `/ui-tests/runs/{id}` 契约不变；`UiTestRun` 变为 ExecutionJob 的投影视图（新增 `execution_job_id`）。
