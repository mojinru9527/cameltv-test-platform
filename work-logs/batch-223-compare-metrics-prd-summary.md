# Batch 223 — 跨版本对比 + 运营指标（B13）
> **Product (🟦)** | Date: 2026-09-05 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 路线图 §2 B13(batch-223) 完整·前后端+DB：跨版本对比页 + 运营指标看板（回归人天/提测→放行周期/漏测/周活跃）。
- 前置：B6-B12（C222-1：指标挂 version_knowledge_record 并复用 B12 推荐集）。

## 1. 问题陈述
有版本任务但从没看过「平台效率」：每版回归花多少人天、提测到放行多久、漏测多少、每周活跃。B13 上线运营指标看板 + 跨版本对比。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 运营指标接口 | 无 | GET /metrics/operations | 本批 |
| 跨版本对比 | 无 | GET /version-tasks/compare | 本批 |
| 前端看板 + 对比页 | 无 | /metrics 页 | 本批 |
| 前后端 gate | — | 全绿 + 后端无新增失败 | 本批 |

## 3. 非目标（本次不做）
- **不做发布火车/版本聚合**（§2.6 独立节奏）。
- **不做 owner 人工录入**：本批指标为派生（proxy）；人工录入接口后续补。

## 4. 用户故事 + 验收标准
- As a 平台负责人, I want 看到回归人天/周期/漏测/周活跃, so that 知道平台效率。
  - 验收：GET /metrics/operations 返回聚合；/metrics 页 4 卡片。
- As a 测试负责人, I want 跨版本对比覆盖/结论/缺陷, so that 定位版本退化。
  - 验收：GET /version-tasks/compare?version_a&version_b 返回两个版本行。

## 5. 技术考量
- 指标由 version_task + version_knowledge_record 派生（proxy）。
- 前端 /metrics 页（4 卡片 + 对比表单）。跨版本 compare 路由需在 /{task_id} 之前声明（避免被路径参数吞掉）。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台 | 前后端 gate 绿 + CI 全绿 |

## 7. 技能使用
- `cameltv-agent-team` → 六部门工件；`cameltv-bug-guard` → 路由顺序
