# Batch 235 — AI Local-First 基础（Phase 0 + Phase 1）— QA 报告
> **QA (🔍)** | Date: 2026-09-13 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 | 7 | 0 | 0 |

## 可执行门禁

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端全量 | `python -m pytest -q` | 0 | **2610 passed, 51 skipped, 1 xfailed**, 657.93s |
| 后端 F821 | `ruff check app/ --select F821` | 0 | All checks passed |
| Alembic 单头 | `python -m alembic heads` | 0 | `20260916_b235_ai_gateway_cache (batch27) (head)` |
| SQLite 升级 | `DATABASE_URL=sqlite:///... python -m alembic upgrade head` | 0 | 全链迁移成功，含 Batch 235 表 |
| 前端依赖 | `npm ci` | 0 | 561 packages installed |
| 前端类型 | `npm run typecheck` | 0 | 通过 |
| 前端 lint | `npm run lint` | 0 | 通过 |
| 前端构建 | `npm run build` | 0 | 3671 modules transformed；build 9.49s |
| Dev Gate | `pwsh scripts/git/dev-gate.ps1` | 2 | `PASS_WITH_WARN`：HARD=0，G1/G2 全绿，WARN=331 需人工归因 |
| WARN 审计 | `pwsh scripts/git/run-warn-audit.ps1 -NoTrendAppend` | 2 | Batch 235 新增文件无告警；剩余 31 个 NEW-WARN-FILE 为 main 既有基线漂移 |

## 逐条件验证

### C1: 精确缓存只调用一次上游

**验证**: `tests/test_ai_gateway_cache.py::test_exact_cache_reuses_response_and_records_hit`
**结果**: PASS。两次完全相同的请求上游调用数为 1，第二次 `cache_status=hit`，命中 usage 记 0，原始用量保留在 `cache_saved_usage`。

### C2: 跨项目隔离

**验证**: `test_exact_cache_is_project_scoped`
**结果**: PASS。项目 1 与项目 2 相同输入都未互相命中。

### C3: 截断响应不缓存

**验证**: `test_truncated_response_is_not_cached`
**结果**: PASS。`finish_reason=length` 两次均调用上游，缓存条目为 0。

### C4: 默认关闭与显式 namespace

**验证**: `test_cache_disabled_preserves_legacy_behavior`
**结果**: PASS。默认关闭时两次均正常调用上游，`cache_status=disabled`。

### C5: TTL 与清理

**验证**: `test_expired_entry_is_a_miss`、`test_clear_cache_can_target_one_namespace`
**结果**: PASS。过期条目回退 miss；按 namespace 清理只删除目标命名空间。

### C6: 路由契约与统计 API

**验证**: `test_cache_api_is_published_in_openapi`、`tests/test_route_inventory.py`
**结果**: PASS。新增 `/api/v1/ai-config/cache-stats` 与 `/api/v1/ai-config/cache` 已进入 OpenAPI、前端类型和路由基线。

### C7: Phase 0 基线可重复采集

**验证**: `python scripts/collect_ai_local_baseline.py --output work-logs/evidence/batch-235-ai-local-first/baseline.json`
**结果**: PASS。输出 Provider、Embedding、镜像运行时、前端 dist、精确缓存状态；不包含凭据。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P2 | 新增缓存接口后，`route_inventory.json` 未同步，首次全量回归失败 | 首次 `pytest -q`：1 failed；更新基线后 `test_route_inventory.py` 通过，二次全量全绿 | ✅ 已修复 |

## 基线对比

- 首次全量：`1 failed, 2609 passed, 51 skipped, 1 xfailed`
- 修复后全量：`2610 passed, 51 skipped, 1 xfailed`
- 新增失败集合：空
- 已有关联警告：`StarletteDeprecationWarning`、Pytest 收集警告、`datetime.utcnow` 弃用警告为仓库既有非阻断项。

## 发布建议

状态: **READY（本地门禁）**  
必修复: 0  
建议修复: 0  

下一步：等待用户一次总确认（推送 + Draft PR + required checks 通过后合入 main）。

## 复盘卡（Batch 75 起强制）

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 本会话完成 | 0/0/1/0 | 1 | 路由契约基线遗漏 | 新增路由时同切片更新 `route_inventory.json` 与 `api.d.ts` |

**技能使用**: `cameltv-agent-team` → 工件与门禁；`cameltv-bug-guard` → 缓存/迁移边界核查。
