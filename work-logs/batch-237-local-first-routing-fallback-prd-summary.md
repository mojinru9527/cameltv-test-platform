# Batch 237 — 本地优先路由与云端兜底（Phase 3）
> **Product (🟦)** | Date: 2026-09-13 | Status: Approved

## 1. 问题陈述

Batch 236 已能后台对比本地与云端，但主链仍固定走云端。没有显式路由策略时，无法把已积累的 shadow 证据安全地转成 local-first 决策，也无法在本地 runtime 故障时自动恢复云端。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 路由模式可配置 | 无 | `cloud_only / shadow / local_preferred / local_only` | 本批 QA |
| local-preferred 可用 | 无 | 本地优先调用，失败自动云端兜底 | 单元测试 |
| local-only 安全失败 | 无 | 无本地配置时明确失败，不暗中回云 | 单元测试 |
| 主链可观测 | 无 | 返回 `route_status` / `route_origin` / fallback 来源 | 单元测试 |
| shadow 策略化 | 无 | 路由决定 shadow 对端，而不是固定本地 | 单元测试 |

## 3. 非目标

- 不自动基于 shadow 分数切换生产策略；策略切换需显式配置。
- 不实现前端路由配置 UI；Phase 4 可评估。
- 不做镜像拆分；仍由 C236-2 承接。
- 不删除现有 Provider 配置能力。

## 4. 用户故事与验收标准

- As a 管理员, I want 选择路由模式, so that 可以先 shadow，再 local-preferred，最后 local-only。
- As a 测试工程师, I want 本地失败时自动回云, so that local-first 不会降低可用性。
- As a 运维人员, I want local-only 无配置时直接失败, so that 不会偷偷产生云端成本或掩盖配置错误。
- As a QA, I want 主链返回路由来源, so that 执行证据能判断实际使用了本地还是云端。

## 5. 上线计划

| 阶段 | 默认 | 成功门槛 |
|------|------|---------|
| Batch 237 | `cloud_only` | 全部路由测试通过，默认行为不变 |
| 后续批次 | 手动切 shadow/local_preferred | 基于真实 shadow 证据决策 |

## 6. 技能使用

`cameltv-agent-team` → 六部门工件；`cameltv-bug-guard` → sync/async、回退、缓存与配置边界。
