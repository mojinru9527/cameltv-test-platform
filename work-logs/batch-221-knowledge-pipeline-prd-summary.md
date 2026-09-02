# Batch 221 — 知识管线（B11）
> **Product (🟦)** | Date: 2026-09-05 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 路线图 §2 B11(batch-221) 完整·后端+DB：版本沉淀 + AI 任务探索新知识 双输入；复用建议自动带出。
- 主链路 §6 知识闭环；ABC §4 D 级收敛（知识为副产品）。
- 前置：B6-B10 版本验收主链路闭环（C220-1：消费 VersionTask 完结数据）。

## 1. 问题陈述
版本跑完就放行了，但「这版怎么测的 + 下版复用建议」没有被沉淀。B11 打通知识闭环：放行自动沉淀版本知识记录；建任务时自动带出上版复用建议。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 版本沉淀（放行自动记录） | 无 | record_version_knowledge hooked into release | 本批 |
| 复用建议（建任务带出上版） | 无 | get_reuse_suggestions | 本批 |
| 前后端/DB gate | — | 后端 F821/路由/Alembic drill/全量无新增失败 | 本批 |

## 3. 非目标（本次不做）
- **不做 AI 任务探索新知识自动捕获**（本批先打通「版本沉淀 → 复用建议」；AI 探索新知识随 DSH/知识中心 AI 审核台 B11 后续；本批以版本沉淀为主线）。
- **不做知识中心 UI**（普通视图 3 Tab 已由 B2/B11 命名，UI 随前端批次）。

## 4. 用户故事 + 验收标准
- As a 测试员, I want 放行后版本知识自动沉淀, so that 下版能复用。
  - 验收：Given 放行 / When release_task / Then VersionKnowledgeRecord 落库（version/verdict/coverage/plan/defect）。
- As a 测试员, I want 建任务时自动带出上版复用建议, so that 不用从零开始。
  - 验收：Given 有多条知识记录 / When GET /version-tasks/knowledge/reuse / Then 返回上版复用条目。

## 5. 技术考量
- 新表 version_knowledge_record（task_id 唯一）；release_task 自动调 record_version_knowledge。
- get_reuse_suggestions 按 project 取最近记录，抽出「采纳/修改」方案条目作为 reuse。
- 路由走 service（route-layer ORM ban）。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台 | 后端 gate 绿 + CI 全绿 |

## 7. 技能使用
- `cameltv-agent-team` → 六部门工件；`cameltv-bug-guard` → 路由守卫/迁移单头
