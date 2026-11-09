# Batch 277a — AIQE §0 P0 代码侧清零：Dev 执行记录

> **部门**：🟩 Dev
> **日期**：2026-11-09
> **基线**：`origin/main @ 9cf83ee2e`

---

## 1. 改动清单（33 文件，+108 / −2602）

| 类别 | 文件 | 改动 |
|------|------|------|
| AI 调用 | `app/services/ai_client.py` | 删除 cache/shadow/route 分支（774→484 行），直连 provider |
| API | `app/api/v1/ai_config.py` | 删除 6 个 gateway 端点（323→317 operations） |
| 配置 | `app/core/config.py` | 删除 10 个 gateway/local/shadow/cache 配置项与 `ai_gateway_delegated` |
| 模型 | 删除 `ai_job.py` / `ai_shadow_run.py` / `ai_gateway_cache.py`；新增 `execution_node.py` | `AiAgent`→`ExecutionNode`，表 `ai_agents` 保留 |
| 服务 | `ai_agent_service.py`、`execution_job_service.py` | 引用改 `ExecutionNode`（表/接口不变） |
| 嵌入 | `knowledge/embedding_service.py` | 删除 remote 分支，仅 worker 进程本地计算 |
| 迁移 | 新增 `20261109_b277_drop_retired_tables.py`；改 `20261007` | `DROP TABLE IF EXISTS` + downgrade 重建 |
| 测试 | 删 3 个 gateway 测试；改 1 个 docstring | — |
| 脚本 | 删 `scripts/ai_agent/`、`backend/scripts/collect_ai_local_baseline.py` | 死代码 |
| 守卫 | 新增 `scripts/ci/check-p0-ready.ps1`、`scripts/ci/alembic_heads.py` | TA-001.5 |
| 文档 | ADR-0027/0028/0029 → superseded；`docs/ai/local-ai-agent.md` 重写；13 号 §0 状态 | — |

---

## 2. 关键实现

### 2.1 ai_client 直连

```python
cfg = resolve_config(db, project_id)
if cfg is None:
    raise AiClientUnavailableError("AI service is not configured")
summary = _call_configured_full(cfg, ...)
summary["route_status"] = "primary"
summary["route_origin"] = "project"
```

同步/异步两版一致；`is_configured()` 改为 `resolve_config(...) is not None`。

### 2.2 节点注册表改名不迁表

`execution_node.py` 里 `__tablename__ = "ai_agents"`，仅类名/模块名改为 `ExecutionNode`；约束名、索引名不动。理由：生产 `ai_agents` 已有节点数据，改名收益 < 迁移风险（记录在模块 docstring，后续单独批次再改名）。

### 2.3 迁移与守卫

```python
op.execute("DROP INDEX IF EXISTS ix_ai_response_cache_cache_key")
op.execute("DROP TABLE IF EXISTS ai_response_cache")
```

downgrade 按 b235/b236 原定义重建（`if_not_exists=True`）。

### 2.4 TA-001.5

- `check-p0-ready.ps1`：证据 + 静态双轨；`-SelfTest` 用临时骨架验证绿/红；
- `alembic_heads.py`：AST 解析 revision/down_revision（含 tuple/list），替代正则；
- 当前真实结果：P0-5 ✅（0 残留 + 单 head），P0-1/2/3/4 ❌（证据缺失；P0-4 Dockerfile 仍装浏览器）。

---

## 3. 验证记录

| 检查 | 命令 | 结果 |
|------|------|------|
| app 导入 | `python -c "from app.main import app; ..."` | ✅ paths **259**（删 6 端点后） |
| 残留扫描 | `Select-String app,tests,scripts -Pattern 'ai_gateway\|AiJob\|AiShadowRun\|AiGatewayCache'` | ✅ **0** |
| 迁移链 | `alembic upgrade head → downgrade -1 → upgrade head` | ✅ 三次退出码 0 |
| 表存在性 | sqlite 查询 | ✅ head=[] → downgrade=[cache,shadow] → re-upgrade=[] |
| 相关单测 | ai_client / ai_config API / config service / batch258 / batch259 | ✅ **58 passed** |
| 关联回归 | knowledge_ai / ai_guard / extraction / generate / version_task_ai / module_extractor / api_generalization | ✅ **45 passed** |
| 守卫 self-test | `check-p0-ready.ps1 -SelfTest` | ✅ `SELFTEST=PASS` |
| 守卫真实 | `check-p0-ready.ps1` | ✅ fail-closed：`FAIL (4/5: P0-1,P0-2,P0-3,P0-4)` |
| 全量后端 | `pytest -q` | ⏳ 运行中（结果补 QA） |
| ruff F821 | `ruff check app --select F821` | ✅ All checks passed |

---

## 4. 偏差

| 计划 | 实际 | 说明 |
|------|------|------|
| `ai_job.py` 删除 + `ai_agents` 表迁移 | 只删文件、保留表名 | 生产节点数据风险；改名留后续 |
| P0-4 `/uitest` 剥离 | 未做（277b） | 改动跨 4 模块 + 前端验收；本批不删 Dockerfile playwright，避免打断现行 `/uitest` |
| `api.d.ts` 同步 | 未重新生成 | 删除的 6 个端点在生成类型里残留；无调用方、无运行影响；记入 QA 遗留 |

---

## 5. DoD 自检

- [x] P0-5 清零 + 迁移可逆 + 守卫失败关闭；
- [x] ADR/文档同步；
- [ ] 全量 pytest 0 新增失败；
- [ ] 前端 typecheck（无前端改动，PR CI 兜底）。
