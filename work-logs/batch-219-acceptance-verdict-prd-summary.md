# Batch 219 — 版本任务放行与证据包（B9）
> **Product (🟦)** | Date: 2026-09-05 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 路线图 §2 B9(batch-219) 完整·前后端：放行页（覆盖/通过率/风险）+ 绑定 release_bundle + 报告/通知；产出可分享放行证据包。
- 前置：B6-B8 VersionTask + 方案 + 执行/证据；C218-1（verdict/coverage 生成证据包 + 绑定 release_bundle + verdict→released）。

## 1. 问题陈述
方案审了、执行跑了、失败分类了，但「能不能放行」还没有正式结论。需要给版本任务加「放行」：基于覆盖/通过率/风险生成可分享的放行证据包，绑定发布包，并发送通知。测试员只做「放行 / 有条件放行 / 打回」。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 放行证据包（覆盖/通过率/风险/缺陷） | 无 | GET /release-package | 本批 |
| 放行/打回 + 绑定发布包 | 无 | POST /release（verdict/release_bundle_id/risk） | 本批 |
| 通知 | 无 | POST /notify | 本批 |
| 前后端 gate | — | 全绿 + 后端无新增失败 | 本批 |

## 3. 非目标（本次不做）
- **不做知识沉淀**（B11）、**指标看板**（B13）。放行即通知，不做跨版本对比。
- **不改既有 release_bundle**：仅绑定 ID（B14 收敛时统合）。

## 4. 用户故事 + 验收标准
- As a 测试员, I want 一键出放行证据包并绑定发布包, so that 一个版本产出可分享证明。
  - 验收：Given 已执行任务 / When POST release(verdict, release_bundle_id, risk) / Then 返回 evidence package（verdict/coverage/pass_rate/risk/defects/release_bundle_id），task 状态→released。
- As a 测试员, I want 放行/打回后发通知, so that 相关人知道结果。
  - 验收：Given 放行后 / When POST notify / Then NotificationLog(sent) 写入。

## 5. 技术考量
- `release_task`：校验 verdict∈{pass,blocked,conditional} 与 status∈{executed,verdict}；绑定 release_bundle；生成 `build_release_package`。
- `NotificationLog` 用 event=version_release 记录（该表为发送审计，无 title/content）。
- 前端放行卡片：通过率/风险/结论 + 放行/有条件/打回 + 发布包 ID + 发送通知。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台 | 前后端 gate 绿 + CI 全绿 |

## 7. 技能使用
- `cameltv-agent-team` → 六部门工件；`cameltv-bug-guard` → 语义守卫
