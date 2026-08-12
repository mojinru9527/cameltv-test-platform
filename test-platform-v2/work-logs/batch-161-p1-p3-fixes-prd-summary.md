# Batch 161 — P1-P3 五组问题修复（PRD-lite）

> **Product (🟦)** | Date: 2026-08-12 | Status: Draft | Mode: light

mode: light
豁免理由: 全部为生产验证暴露的 Bug 修复 + 既有功能的健壮性补强（修复档），不引入新接口/新配置/新依赖，按 pipeline-modes.md 归为轻量批次。
非目标: 不做 Test5 内网可达性改造（环境限制，改由执行前预检+失败原因透出兜底）；不做性能监控模块；不改蓝湖 Cookie 有效期机制本身。

## 1. 问题陈述（生产复验证据，2026-08-12 全模块使用留痕）
| # | 级别 | 问题 | 证据 |
|---|------|------|------|
| G1 | P1 | 15.0.0 需求文档「生成用例(基于拆分)」后端失败：`'coroutine' object has no attribute 'get'`（AI 异步任务 `_run_generate` 未 await 协程） | 生产 doc#10 generate-async 任务 ai-52d22ec2ea status=failed error=coroutine bug；doc#11 同路径成功 |
| G2 | P1 | 计划「失败自动转缺陷/报告/通知」生产未生效：TP-SPORTS-1500/1600 `auto_defect_on_fail=True`，20 条失败后缺陷/报告仍为 0 | 生产 plan 3/4 auto_defect_on_fail=True；缺陷/报告模块 0 自动产物；batch-execute 路径未触发链路 |
| G3 | P1 | 蓝湖证据采集失败：证据任务 #29「蓝湖会话失效且自动登录未获取到 Cookie」 | 生产 lanhu-evidence #29 failed；#28 之前成功（Cookie 过期） |
| G4 | P2 | 2615 条大计划一键执行 >120s 无响应（同步逐行建执行记录）；接口批量执行失败原因不透明（Test5 不可达但无预检提示） | 生产 POST /test-plans/3/execute-all 120s 超时；API-5C87BB63/API-143E3E5B 全失败 |
| G5 | P3 | 16.0.0 导入用例 surface=其他（无端标识）；Playground 404 提示不友好；工作台饼图「P0 2925 37.3%」拼接显示；UI 新建用例曾静默失败（需复测） | 生产 test-cases 统计 surface=其他 89；/playground/compile 业务 404；workbench 文本快照 |

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 15.0.0 doc#10 生成用例成功率 | 0%（coroutine 失败） | 100%（新模型重跑成功） | 合入+部署后生产复验 |
| 自动转缺陷链路 | 0 缺陷/0 报告 | 失败执行后自动生成缺陷+报告 | 生产复验（plan 失败触发） |
| execute-all 大计划（2615 条） | >120s 超时 | 返回 <60s（人工用例批量落库） | 生产复验 |
| 16.0.0 用例 surface 非「其他」占比 | 89 条「其他」 | 回填后 ≤0 | 生产复验 |
| 蓝湖证据采集 | 自动登录失败 | 重试+持久化 Cookie，错误原因明确 | 生产复验（需用户更新 Cookie 后） |

## 3. 非目标
- 不新增接口/Schema/依赖（G4 的环境预检复用 Batch 148 `ensure_plan_execution_ready`）。
- 不修改蓝湖 Cookie 过期机制、不绕过蓝湖登录验证码。
- 不做 Test5 内网/VPN 连通性改造。
- G5 中「UI 新建用例静默失败」「报告统计短暂不一致」「doc#12 删除无响应」先复测：若为自动化误判/时序问题，则以证据记录为准，不做无谓改动。

## 4. 用户故事 + 验收标准
- As 测试人员, I want 15.0.0 需求能一键生成用例, so that 已上线需求可完整回归。验收：doc#10 生成用例成功并导入。
- As 测试人员, I want 失败执行自动转缺陷/报告/通知, so that 质量闭环不需手工补录。验收：计划执行含失败且开关开启 → 自动出现缺陷+报告。
- As 测试人员, I want 蓝湖采集失败原因明确且可自愈重试, so that 不因 Cookie 过期阻塞采集。验收：自动登录重试 1 次并持久化 Cookie；失败信息区分「未配置账号」与「登录失败」。
- As 测试人员, I want 大计划执行不卡死、接口失败原因可见, so that 可放心编排全量回归。验收：execute-all 批量落库 <60s；任务详情显示每项 HTTP 状态/错误。
- As 测试人员, I want 用例端标识正确、错误提示友好, so that 统计与操作体验可靠。验收：16.0.0 用例 surface 回填正确；Playground 错误内联展示；饼图格式正常。

## 5. 技术考量
- G1：cherry-pick 历史未合并修复提交 6988e3a（ai_tasks `asyncio.run` + 回归测试）。
- G2：`run_failure_auto_chain` 已存在于 main（Batch 155），生产未生效疑因部署后端偏旧；本批同时补强：缺陷创建逐条 try/except 防单条中断、batch-execute 失败也触发链路、补单测。
- G4：execute_all_cases 由逐行 `db.add` 改为批量 `add_all` + 避免非 API 用例逐行 flush；任务详情透出 error/status（前端补齐）。
- G5：用例 surface 按域/模块关键词推断 + 存量回填（batch update）；Playground 错误态；饼图格式。
- 部署说明：本批合入 main 后 Railway 重新部署，此前旧后端（health 2.3.0、无 model_used）将更新到最新代码；随后用新模型做生产复验。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批合入 main + Railway 部署 | 内部 | 硬门禁全绿、PR 审计通过 |
| 生产复验（新模型重跑） | 用户 | G1 生成成功、G2 自动缺陷/报告出现、G4 大计划 <60s、G5 surface 回填 |
| 蓝湖 Cookie 更新 | 用户 | G3 采集任务成功 |

## 7. 技能使用
- cameltv-bug-guard → 异步协程、envelope 码、批量落库避坑清单
- cameltv-ui-conventions → 前端错误态/组件规范
