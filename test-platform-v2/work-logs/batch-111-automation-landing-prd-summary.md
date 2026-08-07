# Batch 111 — PRD（体育平台自动化落地：接口批量执行回填 + UI 定时回归 + wiki 差异评审 + Test5 契约）

> **Product (🟦)** | Date: 2026-08-06 | Status: Review

```markdown
mode: full
豁免理由: 无（含后端执行回填改造 + 前端任务交互验证 + 生产批量执行 + 定时任务配置，走完整六部门流水线）。
非目标:
- 运营后台生产账号深度操作（系统模块不可用；只读口径维持）
- 外部 LLM-Wiki 连接器（保持 OFF）
- 平台发布门禁 OPS0-3（继续 Deferred）
- 性能采集优化（C99-1）、iOS 真机（CP-C2/C84-1）
- match replays 真实回放 URL（C101-2 待业务）
- 用例生成规范/覆盖度再扩充（C103-1 已达标，本期不扩量）
```

## 1. 问题陈述

Batch 110 已交付体育平台第一期：34 接口 170 条字段级用例、97/97 实跑回填（脚本直连）、P0 UI 自动化 10 条、
wiki 基线（43 raw sources/10 差异任务）、konfi 实测、运营后台 15 模块菜单。但「自动化落地」仍有明确缺口：

1. **平台批量执行不回填用例结果（C110-3/C103-7）**：`/apitest/tasks` 批量执行已存在（含前端「执行任务」Tab），
   但执行结果只写任务明细（ApiExecutionTaskItem），**不回填 TestCase.last_response_json/last_run_status**，
   用例详情「接口数据-请求结果」栏在批量执行后仍为空（Batch 110 靠脚本直连回填，不可持续）。
2. **UI 自动化未定时化**：P0 UI spec（10 条）已执行通过，但未挂平台定时任务，无法每日生产只读回归。
3. **wiki 差异任务结果未评审**：10 组 RAG vs Wiki 差异任务已生成（财务 21/世界杯 7/回放 3 等），
   差异项未走「评审→采纳/驳回→转待审产物」闭环（C110-1 后续 + C107-2 关联）。
4. **Test5 契约未补拉（C95-1/C74-2）**：konfi-service/admin-service 契约占位（61B/0B）；
   用户确认 Test5 环境已恢复，但契约未补拉导入，konfi/运营后台关联仍有推断项。
5. **api-regression workflow 推送即 0s 失败**：Test5 恢复前为已知；恢复后仍失败，需排查是否为 CI 配置问题
   （runner/内网通道/分类器）。
6. **C110-4**：P0 口径（用户端关键域全 P0 + 运营核心模块 P0）需用户确认后固化。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| 批量执行回填 | 执行结果不写 TestCase | 批量任务执行后用例详情「请求结果」可见（last_response_json/last_run_status 回填） |
| 接口批量执行 | 脚本直连（97 条） | 平台 /apitest/tasks 生产批量执行 170 条全部用例，任务通过率记录 |
| UI 自动化定时 | 手动执行 10/10 | ui-test job + 每日定时任务（生产只读）创建并触发 ≥1 次 |
| wiki 差异评审 | 10 任务/部分结果 | 差异任务结果拉取 + 评审（采纳/驳回）+ 差异项转待审产物 ≥3 项 |
| Test5 契约 | konfi/admin 契约占位 | 补拉并导入（若内网/凭据不可达则登记 Deferred + 证据） |
| api-regression | 推送 0s 失败 | 定位根因并修复/登记（Test5 恢复后验证一次成功运行） |
| 平台障碍 | C110-3/4 等 | 本期闭环项关闭，新增障碍登记 |

## 3. 用户故事 + 验收标准

- As a **接口测试工程师**, I want 平台批量执行后自动回填用例「请求结果」，so that 用例详情三栏闭环、可评审可追溯。
  - Given 170 条接口用例，When 在平台创建批量执行任务并完成，Then 每条用例 last_response_json/last_run_status 回填，前端可见。
- As a **QA**, I want P0 UI 自动化每日定时生产只读回归，so that 关键路径持续受控。
  - Given P0 UI job 与定时任务已建，When 触发一次，Then 10/10 通过并产出报告证据。
- As a **平台使用者**, I want wiki 差异项可评审并转待审产物，so that 需求/知识迭代差异闭环。
  - Given 差异任务结果，When 评审采纳，Then 生成待审 AI 产物（review_status=pending）。
- As a **承接负责人**, I want Test5 契约补拉导入，so that konfi/运营后台关联从推断变为契约实测。
  - Given Test5 环境可用，When 补拉 konfi-service/admin-service 契约，Then 导入平台资产并更新关联。

## 4. 技术考量

- **后端回填（核心）**：`api_task_worker.execute_task` 每条 item 执行后 UPDATE test_case SET
  last_response_json=<响应快照>, last_run_status=passed/failed；复用 `_build_response_snapshot`；
  TDD：worker 单测断言 TestCase 字段回填。
- **前端**：`frontend/src/pages/apitest/index.tsx` 已有「执行任务」Tab（TasksTab）；
  验证选用例→建任务→结果列表→用例详情「请求结果」联动；必要时补「从用例详情批量执行」入口。
- **生产批量执行**：`POST /apitest/tasks`（case_ids=170 条 + environment_id=体育平台-生产 + confirm_prod=true，
  sportsadmin 超管具备 apitest:execute_prod）；worker 已在生产后端（Railway）运行。
- **UI 定时**：`POST /ui-tests`（test_spec=specs/production-p0-modules.spec.ts + 生产环境）+ `POST /schedules`
  （cron 每日 + plan 或 ui job 绑定，按平台 schedule 支持范围）。
- **wiki 评审**：`GET /wiki/diff/tasks/{id}` → 逐项 `POST /wiki/diff/items/{id}/accept|reject` →
  `POST /wiki/diff/items/{id}/create-artifact`。
- **Test5 契约**：konfi-service/admin-service 经 Test5 Swagger（camel-api-gateway05.svc.elelive.cn）补拉
  OpenAPI → `/apitest/import/preview|confirm`；依赖内网通道（WSL2 OpenVPN）与账号，不可达则登记。
- **api-regression**：检查 `.github/workflows/api-regression.yml` push 触发配置与 runner 选择。

## 5. 范围

**纳入**：批量执行结果回填（后端+测试）、前端批量执行链路验证、生产 170 条批量执行、UI 定时回归、
wiki 差异评审闭环、Test5 契约补拉尝试、api-regression 排查、C110-4 确认、障碍登记。

**非目标**（见头部）。

## 6. 上线计划

| 阶段 | 内容 | 出口标准 |
|------|------|---------|
| S1 | 批次工件 + 看板 + C110-3 后端回填改造（TDD） | 单测通过 + 代码提交 |
| S2 | 前端批量执行链路验证（含用例详情联动） | typecheck/build + 交互证据 |
| S3 | 生产 170 条批量执行 + 回填验证 | 任务结果 + 用例详情三栏证据 |
| S4 | UI 定时回归（job+schedule+触发） | 定时任务运行报告 |
| S5 | wiki 差异评审闭环 | 差异项评审 + 产物证据 |
| S6 | Test5 契约补拉 / api-regression 排查 | 契约导入或 Deferred 登记；workflow 修复或根因登记 |
| S7 | C110-4 确认 + QA + Leader + 一次总确认 | 全部门工件 + PR |

## 7. 技能使用

- `cameltv-agent-team` → 六部门流水线（本 PRD）
- `cameltv-bug-guard` → 后端/前端改造避坑
- `test-case-design` / `cameltv-api-test` → 接口执行与断言核对
- `playwright-cli` / `playwright-skill` → UI 定时回归验证
