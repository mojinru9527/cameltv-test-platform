# Batch 222 — 智能回归 + 缺陷闭环（B12）
> **Product (🟦)** | Date: 2026-09-03 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 路线图 §2 B12(batch-222) 完整·前后端：影响面默认接入；缺陷一键同步通知/缺陷库。
- 前置：B6-B11（C221-1：复用 version_task_run 失败分类 + version_knowledge_record 复用建议；不影响面外造回归容器）。

## 1. 问题陈述
建任务时没给「推荐回归集」，业务缺陷也没有一键同步到通知/缺陷库。B12 打通回归推荐 + 缺陷闭环。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 推荐回归集（影响面） | 无 | GET /regression-set | 本批 |
| 缺陷一键同步 | 无 | POST /defects/{id}/sync | 本批 |
| 前端推荐回归集 + 同步 | 无 | 详情页卡片 + 按钮 | 本批 |
| 前后端 gate | — | 全绿 + 后端无新增失败 | 本批 |

## 3. 非目标（本次不做）
- **不做跨版本对比/运营指标**（B13）、**D 级收敛**（B14）。
- **不做真实影响面算法**：本批用「方案/模块/复用」启发式推荐，真实影响面随 B13 指标接入。

## 4. 用户故事 + 验收标准
- As a 测试员, I want 建任务即看到推荐回归集, so that 不用手动圈回归范围。
  - 验收：Given 任务含变更模块 + 方案 / When GET regression-set / Then 返回 方案条目+模块回归+复用 去重推荐。
- As a 测试员, I want 业务缺陷一键同步通知/缺陷库, so that 不遗漏。
  - 验收：Given 任务关联缺陷 / When POST defects/{id}/sync / Then 写 NotificationLog(defect_sync）。

## 5. 技术考量
- `recommend_regression_set`：采纳方案条目 + scope.modules + version_knowledge_record 复用 → 去重推荐（priority 按置信度）。
- `sync_defect_notification`：写 NotificationLog(event=defect_sync)；若未关联补 link。
- 前端推荐回归集卡片 + 同步按钮。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台 | 前后端 gate 绿 + CI 全绿 |

## 7. 技能使用
- `cameltv-agent-team` → 六部门工件；`cameltv-bug-guard` → 路由守卫
