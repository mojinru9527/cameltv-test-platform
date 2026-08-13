# Batch batch-166-playground-case-picker — PRD Summary
> **Product (🟦)** | Date: 2026-08-13 | Status: Approved

## 1. 问题陈述
Playground 当前只支持单条输入/单条用例编号编译，测试人员需要批量把功能用例转换为 Playwright spec、执行并回写 UI 任务。人工逐条操作成本高、无法沉淀为可追溯的 UI 自动化资产。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 单次可选用例数 | 1 | 1~N（上限 50 执行 / 100 编译） | 合入后 |
| 批量编译耗时 | 无 | <5s（N≤20 不含 Playwright 下载） | 合入后 |
| 执行回填 | 无 | 用例 last_run_status / 结果摘要回填 | 合入后 |
| UI 任务回写 | 无 | 每条生成 UI job 并关联 case_id | 合入后 |

## 3. 非目标（本次不做）
- 不做 Playground 在线编辑 spec 的持久化版本管理。
- 不自动触发 UI job（只创建任务，触发仍走 UI 自动化既有流程）。
- 不新增生产环境执行权限模型（复用 uitest:trigger）。

## 4. 用户故事 + 验收标准
- As 测试工程师, I want 在 Playground 从功能用例库按域/模块/正负向/关键字筛选并勾选 1~N 条用例, so that 我能批量转换为 Playwright spec。
  - 验收：Given 用例库加载 / When 勾选若干功能用例并点击批量编译 / Then 展示每条生成的 spec 与 TODO 标识。
- As 测试工程师, I want 批量执行已选用例, so that 我能一次获得通过/失败、截图和耗时。
  - 验收：Given 已勾选用例 / When 点击批量执行 / Then 返回逐条结果与截图；失败不阻断后续用例。
- As 测试工程师, I want 执行结果回填用例, so that 用例详情能看到最近 Playground 执行状态。
  - 验收：用例 last_run_status 变为 pass/fail，摘要可追溯。
- As 测试工程师, I want 生成 spec 回写 UI 任务, so that 后续能在 UI 自动化中用真实 runner 产出 trace/report。
  - 验收：每条用例创建关联 UiTestJob，test_spec 指向 generated/playground-case-*.spec.ts。

## 5. 技术考量
- 后端新增 `/playground/batch-compile` 与 `/playground/batch-run`。
- 编译复用 `playground_service.compile_spec`；执行复用 `execute_spec`（临时目录 headless）。
- UI 回写复用 `ui_test_service.create_job`，spec 落入 ui_runner `generated/` 目录。
- 前端 Playground 增加用例库筛选/勾选表格，保持手动输入单条草稿能力。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全队 | 后端/前端 required checks 全绿 |
| test 部署后 | 测试负责人 | 批量编译/执行/回写走查通过 |

## 7. 技能使用
- cameltv-bug-guard → useEffect cleanup / 无 N+1 请求核对。
- cameltv-ui-conventions → 页面/表格/徽标样式基线。
