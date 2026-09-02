# Batch 224 — D 级收敛（B14）
> **Product (🟦)** | Date: 2026-09-05 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 路线图 §2 B14(batch-224) 完整·后端+DB：TestPlan 数据归档、Dataset/Fixtures 合并、环境/报告/缺陷/任务入口收敛为单一事实源。
- 白名单 §4 D 级重复收敛；C223-1（单事实源 + 双写清零 + 旧数据可读）。

## 1. 问题陈述
平台存在多套重复概念（TestCase/TestPlan vs Mission/Scenario/Campaign vs VersionTask），用户无法聚焦。B14 把 TestPlan 只读归档、数据资产合并、入口收敛到 VersionTask 单一事实源。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| TestPlan 只读归档 | 无 | archive_test_plan（status=archived + 绑 VersionTask） | 本批 |
| 资产视图（单一事实源） | 无 | GET /convergence/assets（single_fact_source=version_task） | 本批 |
| 数据资产合并 | 无 | GET /convergence/data-assets | 本批 |
| 后端 gate | — | 无新增失败 | 本批 |

## 3. 非目标（本次不做）
- **不做数据迁移/双写清零全量**：本批次提供归档+视图（D 级收敛机制）；存量数据迁移/双写清零随发布节奏。
- **不做前端降级视图**（留 B15 最终验收）。

## 4. 用户故事 + 验收标准
- As a 平台维护者, I want 旧 TestPlan 只读归档到版本验收任务, so that 不再双写。
  - 验收：archive_test_plan → TestPlan status=archived + converged_to_task。
- As a 维护者, I want 单一事实源资产视图, so that 只从 VersionTask 出来。
  - 验收：GET /convergence/assets 返回 single_fact_source=version_task + 各资产。

## 5. 技术考量
- 复用 TestPlan.status（已有 archived）与 VersionTask。
- 新 convergence_service：归档/资产视图/数据合并。无新表。
- 路由走 service（route-layer ORM ban）。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台 | 后端 gate 绿 + CI 全绿 |

## 7. 技能使用
- `cameltv-agent-team`；`cameltv-bug-guard` → 路由守卫
