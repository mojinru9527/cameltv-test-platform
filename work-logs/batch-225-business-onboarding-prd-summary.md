# Batch 225 — 新业务接入（B15）
> **Product (🟦)** | Date: 2026-09-05 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 路线图 §2 B15(batch-225) 完整·前后端+DB：4 步接入向导 + 业务基线（试点 basketball-service/camel-mimo）。
- 主链路 §7 新业务接入；C224-1（走 VersionTask 主链路，不另造接入容器）。

## 1. 问题陈述
平台要能「接新业务」：一个全新服务进来，30 分钟内跑出业务基线（建任务→生成方案→跑一遍）。B15 提供 4 步接入向导 + 基线，试点 basketball-service / camel-mimo。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 4 步接入向导 | 无 | /onboarding 页 + API | 本批 |
| 业务基线（走 VersionTask） | 无 | step4 跑基线 → VersionTask run + baseline | 本批 |
| 前后端 gate | — | 全绿 + 后端无新增失败 | 本批 |

## 3. 非目标（本次不做）
- **不做真实业务 API 探测**：本批基线为合成（VersionTask 主链路 + 运行），真实外部服务接入随上线。
- **不做多语言/模板扩展**。

## 4. 用户故事 + 验收标准
- As a 平台负责人, I want 4 步接入一个新业务并跑出基线, so that 30 分钟出基线。
  - 验收：POST /onboarding/businesses 登记 → step 3 生成 VersionTask+方案 → step 4 跑基线（VersionTask run），status=active。
- 试点 basketball-service / camel-mimo。

## 5. 技术考量
- business_onboarding 表 + migration；onboarding_service（create/complete_step/list）。
- step 3 走 version_task_service.create_task + generate_plan；step 4 走 start_run（VersionTask 主链路）。
- 前端 /onboarding 4 步向导页。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台 | 前后端 gate 绿 + CI 全绿 |
| B1-B15 里程碑 | 平台 | M3 出口（新业务 30 分钟出基线） |

## 7. 技能使用
- `cameltv-agent-team` → 六部门工件；`cameltv-bug-guard` → 迁移/路由
