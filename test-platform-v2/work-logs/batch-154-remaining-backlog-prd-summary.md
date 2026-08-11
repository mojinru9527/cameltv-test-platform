# Batch 154 — 剩余四项收口（数据集参数化/图谱治理/UI 映射/环境与孤儿文件）PRD

> **Product (🟦)** | Date: 2026-08-11 | Status: Approved | Mode: full

mode: full
理由: 含新字段（test_case.dataset_id、ui_test_job.case_id，Alembic 迁移）、新接口与 UI，完整批次。
非目标: 无（本批为 C 条件收口）。

## 0. 背景与来源
用户 2026-08-11 指示一次性处理剩余四项：C147-8、C147-9、C151-1、C152-1。

## 1. 问题陈述与目标

### WS1 C147-8 数据集参数化注入 API 用例 UI
- 后端已支持 dataset_id 批量执行与 ${列名} 替换；前端 DebugTab 已有数据集选择，但接口用例**创建/编辑表单**与**用例执行（ApiCaseTab）**未打通。
- 目标：TestCase 绑定默认数据集（dataset_id）；CaseDrawer 接口数据 Tab 加数据集选择；ApiCaseTab 执行工具栏加数据集选择；执行时若未显式传数据集则用用例默认值。

### WS2 C147-9 知识图谱治理
- missing_source 946 实体 source_id 为空；graph_evolve 生产报错；业务删除不级联知识切片。
- 目标：补全接口（按名称匹配用例/需求回填 source_id/source_ref）；evolve 加固（跳过悬空 source、异常兜底）；删除级联（缺陷/需求/用例删除 → 知识源 deprecated）。

### WS3 C151-1 UI 自动化↔用例映射回写 + 批量扩量
- UiTestJob 无 case_id；运行结果不回写用例。
- 目标：UiTestJob.case_id 映射；运行完成后回写 TestCase.last_run_status/last_response_json；UI 任务表单可选关联用例、列表显示用例；新增「从用例批量创建任务」接口。

### WS4 C152-1 孤儿文件清理 + env 统一入口
- env 分散 5+ 份无清单；tracked 孤儿文件未清理。
- 目标：docs/env-unified-guide.md（统一入口=launcher/config-runtime）；scripts/env-inventory.ps1（清单+必填校验）；清理 tracked 孤儿文件（明显临时/备份类）。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 接口用例数据集绑定 | 无 | 表单可绑定 + 执行生效（单测） |
| missing_source | 946 | 接口可回填（名称匹配）+ 统计下降 |
| graph_evolve | 报错 | 加固后单测通过 |
| 删除级联 | 无 | 删除后知识源 deprecated（单测） |
| UI 任务↔用例 | 无映射 | case_id 贯通 + 运行回写（单测） |
| env 统一入口 | 分散 | guide + inventory 脚本 |
| tracked 孤儿 | 未清 | 清理明显临时/备份文件 |

## 3. 非目标
- 不删除用户未跟踪本地文件（.workbuddy/、_review_tools/、test-platform/ 等留在本地）。
- 不做图谱全量重建；不做 UI 用例批量生成脚本内容。

## 4. 技术考量
- 迁移：`20260811_batch154_links`（test_case.dataset_id + ui_test_job.case_id，幂等）。
- 执行兜底：execute_api_case dataset_id=None 时取 case.dataset_id。
- 回写：UI run 完成/失败路径统一调用 writeback（独立 session 内）。
- 级联：knowledge_cleanup.mark_deleted 懒加载调用，避免环依赖。
- env 脚本：只读校验，不修改用户 .env。

## 5. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全部 | checks 全绿 |
| 部署回归 | 测试/知识/UI | 四项路径复测 |

## 6. 技能使用
- cameltv-bug-guard（迁移守卫、懒加载防环、类型校验）
- cameltv-agent-team 流水线
