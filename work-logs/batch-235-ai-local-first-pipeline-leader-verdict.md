# Batch 235 — AI Local-First 基础（Phase 0 + Phase 1）— Leader Verdict
> **Leader (🎯)** | Date: 2026-09-13 | Decision: APPROVED（已合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | A | 缓存默认关闭、项目隔离、失败不阻断主链 |
| 风险 | 低 | 新表 + 新路由；未接本地模型运行时 |
| 覆盖 | A- | 缓存核心、TTL、截断、清理、路由基线均有测试 |

## 关键决策（已批准）

1. Phase 0/1 单独成批，Phase 2–4 不混入同一高风险变更。
2. 精确缓存 opt-in，调用方必须显式提供 `cache_namespace`。
3. 缓存命中不虚报当前调用 Token，原始节省量单独记录。
4. 模型权重与本地推理运行时留在后续 Phase 2–4，不进入本批 API 镜像。

## 抽检通过

- ✅ `app/services/ai_gateway/keys.py` — 键包含 project/provider/model/namespace/prompt/input/params
- ✅ `app/services/ai_gateway/cache.py` — TTL、命中计数、namespace 清理
- ✅ `app/services/ai_client.py` — sync/async 均接入，截断响应 bypass
- ✅ `alembic heads` — 单头 `20260916_b235_ai_gateway_cache`
- ✅ `pytest -q` — 2610 passed / 51 skipped / 1 xfailed
- ✅ `npm run typecheck`、`npm run lint`、`npm run build` — 全部通过

## 判决

最终 APPROVED。PR #428 的 required checks 全绿，最终审计通过，已 squash merge 到 main（merge commit `5775f23c`）。

1. 用户完成本批一次总确认（推送 + Draft PR + required checks 通过后合入 main）。
2. Draft PR 创建后运行 `audit-ai-pr.ps1`，并等待 required checks 全绿。
3. 最终审计通过后再将本判决更新为 APPROVED；当前不得宣称已合入或已发布。

## 下一批次 Leader 条件（如有）

- C235-1: Phase 2 必须实现独立本地推理运行时与 Shadow Mode，禁止把模型权重打入 API 镜像。
- C235-2: Phase 3 再启用 local-first 路由和云端兜底；不得在本批默认开启精确缓存。
- C235-3: Phase 4 拆分 API/AI Worker/UI Runner 镜像前，必须先取得镜像体积基线。

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| 新增路由容易漏更新 `route_inventory.json` | 本批已将新增路由纳入基线；后续新增/删除路由必须在同切片同步守卫 | `test-platform-v2/backend/tests/fixtures/route_inventory.json` |
| OpenAPI 全量再生成会携带历史漂移 | 本批采用最小增量更新并明确后续单独治理生成漂移 | `test-platform-v2/frontend/src/types/api.d.ts` |
| 本地模型“Phase 0–4”若单批完成会混淆风险 | 按版本批次生命周期拆批，Phase 2–4 转 C 条件 | 本判决 C235-1~C235-3 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 本会话完成 | 0/0/1/0 | 1 | 路由契约基线遗漏 | 路由切片同时更新基线 |

**技能使用**: `cameltv-agent-team` → 判决与流程回写；`cameltv-bug-guard` → 迁移/缓存/路由边界。
