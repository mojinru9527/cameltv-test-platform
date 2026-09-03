---
title: "Batch 226 体育 16.0.0 AI 全链路 QA 报告"
owner: "qa-team"
last_reviewed: "2026-09-03"
status: "blocked"
expires: "2027-03-03"
tags: ["batch-226", "sports", "16.0.0", "qa", "ai-e2e"]
related:
  - "work-logs/evidence/batch-226-sports-v16-ai-e2e/README.md"
  - "docs/platform-refactor/07-b1-b15-delivery-and-usage.md"
---

# Batch 226 QA 报告：体育 16.0.0 AI 全链路

> QA | Date: 2026-09-03 | Verdict: **BLOCKED** | Executor: Codex | 轻量批次

## 总体结论

B1-B15 功能面为 **12 PASS / 3 BLOCKED / 0 FAIL**。平台已能诚实阻止假成功，但体育 `16.0.0` 尚未真正跑通 AI→Runner→证据→pass 放行的完整链路，因此不能给出“全链路通过”。

- B8/B10：AI 生成 30 条方案并完成审核，但 0 条包含可执行元数据；运行得到 30 blocked、0 pass。
- B15：没有可访问的体育 OpenAPI，向导正确阻断在第 1 步，未假激活。
- AITDE：Scope/Contract/Scenario 三类 AI Operation 均失败；本地无 Temporal Worker，执行未落地；Quality Gate 为 FAIL。
- 详细逐项结论见 `evidence/batch-226-sports-v16-ai-e2e/b1-b15-matrix.json`。

## 实测链路

| 链路 | 结果 | 核心证据 |
|------|------|----------|
| 需求输入 | PASS | 4315 bytes、72 行、SHA-256 已登记；需求正文成功关联任务 |
| VersionTask AI 方案 | PASS（生成/审核） | 30 条生成、30 条采纳；非前端固定模板 |
| VersionTask 执行 | BLOCKED | executable=0；0 pass / 0 fail / 0 skip / 30 blocked |
| 放行与证据包 | PASS（防误放） | 30 checks、0% pass、1 defect；pass 按钮禁用，结论 blocked |
| 知识/回归/对比/指标 | PASS | 2 条复用建议、42 条推荐回归；指标显式标记人天未录入 |
| B14 单一事实源 | PASS | `single_fact_source=version_task`；连续读取一致 |
| B15 接入 | BLOCKED | 无 OpenAPI 时业务错误，step/status 不推进 |
| AITDE | BLOCKED | 3 个 AI Operation FAILED；零执行，Quality Gate FAIL |

## 黑盒与网络

- tester 五个一级入口均存在：工作台、版本验收、结果与缺陷、知识中心、资产与更多。
- `/workbench`、`/version-tasks`、`/report`、`/knowledge`、`/onboarding` 均返回 200。
- 关键页面无控制台错误、无 HTTP 500。
- Source GET 单次有效请求；Contract/Ambiguity 不再出现请求风暴。
- 768×1024 与 390×844 下 body/main 均无横向溢出。

## 缺陷与修复

| 严重级 | 复现问题 | 修复结果 |
|--------|----------|----------|
| P0 | 无执行目标曾以 skip 计数并最终得出 pass | 改为 blocked；空方案/任何 fail、skip、blocked 均禁止 pass |
| P1 | AITDE list API 响应模型声明 dict，实际返回 list | Source/Fragment/Ambiguity/Intent 改为 `R[list]` |
| P1 | Source 与 Contract 页 loading effect 形成请求循环 | 独立 reloadVersion + AbortSignal；网络复测无重复风暴 |
| P1 | Contract 空 rules、Scenario 空 items 被当作 AI 成功 | 空语义结果判 AI 失败，并保留确定性降级与 FAILED 记录 |
| P1 | B15 未真实导入 OpenAPI 且可能假激活 | 第 2 步真实导入；顺序门禁；仅全通过才 active |
| P2 | 缺陷项目 ID 使用 task ID、风险字段往返不一致 | 使用 task.project_id；risk 按字符串列表序列化 |
| P2 | 前端使用虚假 defect id=0 同步 | 仅创建成功后使用真实 defect_id，同步按钮前置禁用 |

## 代码逻辑审计

- 执行结论从持久化 run/coverage 计算，没有新增随机或固定 PASS 分支。
- `release_task(pass)` 后端再次校验：必须至少 1 个真实通过且 fail/skip/blocked 均为 0；前端禁用只是辅助门禁。
- AI 输出解析仅有限重试两次，空/非法输出返回业务错误，不无限重试、不静默成功。
- AITDE 降级产物与 AI Operation 状态分离：人工可继续审阅，但 AI 失败仍可审计。
- B15 必须顺序推进 2→3→4；OpenAPI 必须可解析且至少含 1 个 endpoint；基线完整记录 pass/fail/skip/blocked。
- 新增与修改的异步前端 effect 均有取消或 AbortSignal；实测 GET 请求为单次有效请求。

## 质量门禁

| 门禁 | 结果 |
|------|------|
| 后端聚焦测试 | `73 passed`，exit 0 |
| 前端聚焦测试 | `23 passed`，exit 0 |
| 后端全量 | `2402 passed, 49 skipped, 1 xfailed, 0 failed`，exit 0 |
| 前端全量 | `132 files, 612 tests passed`，exit 0 |
| app import / Ruff F821 | 通过，exit 0 |
| Alembic 单头 / revision tests | 单头；`8 passed`，exit 0 |
| 前端 typecheck / lint / build | 全部通过，exit 0 |
| 文档保鲜 | exit 0；0 expired、25 warnings、1309 missing frontmatter；另有 1 个既有非 UTF-8 看板读取警告（均为仓库基线） |
| `dev-gate.ps1` | exit 1：仅 `requirement_service.py:225,229` 两处 `except json.JSONDecodeError: pass` 基线 HARD；与 origin/main diff 为空 |
| C-condition audit | exit 1：23 orphan；Open=58、Closed=192，为既有仓库条件债务；本批未伪报通过 |

本分支同时修改 backend、frontend、docs/work-logs，CI 分类应按混合变更运行双端 required 回归及 delivery policy。

## 防假成功证据

修复前历史任务 `16.0.0-pre-fix` 曾出现 33 skip 却得出 pass；修复后同类体育任务 `16.0.0` 明确为 30 blocked、verdict=blocked。0 checks 的 pass rate 为 0，放行按钮与后端 pass API 双重拒绝。B15 缺真实 OpenAPI 时不推进，AITDE 的降级内容不改变 AI Operation FAILED 状态。

## 知识检索与流程回写

- 批次启动时检索仓库知识，针对“体育 16.0.0 + B1-B15 最终全链路”的直接复用记录为 0；采用 B1-B15 路线图、F-01…F-09 整改清单及历史 AI 假成功门禁作为基线。
- 新增回归测试固化：列表响应契约、请求次数、空 AI 语义结果、无执行目标、pass 放行、真实 defect id、OpenAPI 接入和步骤顺序。
- 本次结论回写交付/使用文档、实现文档、证据矩阵和看板，不修改与本批无关的 C 条件。

## 阻塞解除条件

1. 提供真实可访问的体育 `16.0.0` OpenAPI 与被测服务地址，使 AI 方案带出可执行目标。
2. 修复项目 AI Provider 的 JSON/空 rules/HTTP 400 问题，并确认实际模型身份与调用健康。
3. 启动匹配版本的 Temporal Worker/Runner，产出可追溯请求、响应、断言或截图证据。
4. 用同一需求重跑 VersionTask 与 AITDE，Quality Gate 全绿且 VersionTask 可选择 pass 放行。

## 复盘卡

| 计划/实际 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|-----------|-------------------|----------|----------|----------|
| 1d / 1d | 1/4/2/0 | 3 | 假成功、响应契约、React 副作用、外部运行依赖 | 方案生成前注入真实契约；空产物即失败；全链路环境预检 AI+Worker+OpenAPI |

## QA 建议

**BLOCKED / 打回全链路通过声明。** 本批修复可以进入 Draft PR 接受 CI 验证，但在上述外部条件解除并补齐真实执行证据前，不得宣称体育 16.0.0 AI 全链路已经跑通。
