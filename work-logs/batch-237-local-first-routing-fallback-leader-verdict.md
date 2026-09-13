# Batch 237 — 本地优先路由与云端兜底（Phase 3）— Leader Verdict
> **Leader (🎯)** | Date: 2026-09-13 | Decision: APPROVED（已合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | A | 路由显式、sync/async 一致、fallback 可追溯 |
| 风险 | 低 | 默认 cloud_only，行为不变 |
| 覆盖 | A | 四模式、策略建议、fallback、local_only 失败均有测试 |

## 关键决策

1. `cloud_only` 为默认生产模式，不自动切换。
2. `local_preferred` 才允许本地失败回云；`local_only` 禁止暗回云。
3. Shadow 对端由 RoutePlan 决定，避免隐式调度。
4. Shadow 证据只给建议，不自动修改配置。

## 抽检通过

- ✅ `app/services/ai_gateway/router.py` — 四模式与回退计划
- ✅ `app/services/ai_client.py` — sync/async 路由与 fallback
- ✅ `app/services/ai_gateway/policy.py` — 证据到建议，不改配置
- ✅ `app/services/ai_gateway/shadow.py` — 对端策略化
- ✅ `pytest -q` — 2628 passed / 51 skipped / 1 xfailed
- ✅ 前端 typecheck / lint / build — 全部通过

## 判决

最终 APPROVED。PR #430 的 required checks 全绿，最终审计通过，已 squash merge 到 main（merge commit `0e4b5f1b`）。

1. 用户完成 Batch 237 一次总确认（推送 + Draft PR + required checks 通过后合入 main）。
2. Draft PR 创建后通过 `audit-ai-pr.ps1`，等待 required checks 全绿。
3. 最终审计通过后再更新为 APPROVED。

## 下一批次 Leader 条件

- C237-1: Phase 4 必须先采集 API/AI Worker/UI Runner 镜像体积与 BuildKit 缓存基线，再拆镜像。
- C237-2: 不得把模型权重或 CUDA 运行时打入 API 镜像。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 路由与 shadow 隐式耦合 | RoutePlan 同时传递 primary/fallback/shadow | `app/services/ai_gateway/router.py` |
| local-only 容易暗中回云 | 无本地配置直接失败，回退仅允许 local_preferred | `router.py` + 测试 |
| Shadow 证据没有转换成建议 | 新增只读 policy API，不自动改配置 | `policy.py` + API |

**技能使用**: `cameltv-agent-team` → 判决与回写；`cameltv-bug-guard` → sync/async 与回退边界核查。
