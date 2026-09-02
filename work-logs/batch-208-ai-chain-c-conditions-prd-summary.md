# Batch 208 — AI 链 C 条件（C3/C4/C5/C6/C7）— PRD Summary
> **Product (🟦)** | Date: 2026-09-02 | Status: Approved

## 1. 问题陈述
Batch 207 合入后，ADR-0022 记录 7 项 Leader C 条件。本批承接其中 **C3/C4/C5/C6/C7**（C1/C2 依赖真实 UI 运行时，单独后批）：
- C3 PromptEvaluation 黄金回归 runner 未实现（模型/提示词调用从未真实注入）。
- C4 Smart Regression 生产快照 store-backed loader 未实现（自动变更集只能 inline debug）。
- C5 真实 LLM 调用栈 4 套并存、解析/重试/门控各写各的（ai_service / llm_json_client / intelligence.llm_sync / legacy_cutover）。
- C6 AI 可用性门控项目级 resolve 与环境级 settings 两套并存。
- C7 knowledge.module_extractor「AI 辅助模块边界检测」仍是 stub。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 共享 LLM client（sync+async+解析+门控）被 ≥3 处原调用栈复用 | 0 | ≥3 | 单测/引用 |
| llm_json_client / llm_sync / legacy_cutover / ai_service 传输层收敛到共享 client | 0 | 4 | 代码引用 |
| PromptEvaluation 黄金回归 runner 真实调 LLM（mock）并写 ModelEvaluationRun | 无 | 有 | 单测 |
| Smart-Regression loader 支持 env_snapshot/data_source refs + 可注入 | 无 | 有 | 单测 |
| module_extractor AI 边界建议 helper（mock LLM）产出分组 JSON | stub | 实现 | 单测 |
| 既有确定性行为不变（AI 未配置/调用失败降级） | — | 相关 pytest 全绿 | PR |

## 3. 非目标（本次不做）
- C1 Command IR 方言统一、C2 binding 自动物化（依赖真实浏览器/API 运行时，后批）。
- 不改前端；不改 v1 requirement 两阶段对外行为（仅收敛传输实现）。
- 不新增数据库表/迁移（C3 复用 ModelEvaluationRun；C4 只读既有快照来源）。

## 4. 用户故事 + 验收标准
- As a 开发者, I want 一套共享 LLM client，so that 门控/重试/错误分类一致。
  - 验收：sync `chat_completions` 与 async `achat_completions` 同一解析/门控；四栈引用新 client 后相关测试全绿。
- As a 测试平台用户, I want 提示词黄金回归真跑模型并写入评估记录，so that 提示词回归防线不再空转。
  - 验收：mock LLM 下 `PromptEvaluationService.run_golden` 产出 ModelEvaluationRun（_trusted 指标），失败可阻塞回归。
- As a 测试负责人, I want 变更检测能装载真实快照，so that 自动 Smart Regression 不再只吃 inline。
  - 验收：`env_snapshot:{id}` / `data_source:{id}:{kind}` ref 装载成功；未解析 ref 仍显式报错。
- As a 测试设计者, I want 模块边界可获 AI 建议，so that 蓝湖层级归类不再纯启发式。
  - 验收：`ai_boundary_suggestions(...)`（mock LLM）返回模块合并建议；未配置 AI 时返回空且不报错。

## 5. 技术考量
- 判定：引入新行为/新接口/共享能力 → **完整批次**。
- 风险：ai_service 传输收敛可能触碰其健康登记/截断 salvage 逻辑 → 传输层与解析/观测层解耦，收敛仅替换 HTTP 调用；相关测试（test_ai_schema_validation / ai service 相关）全量回归把关。
- CI 域：backend + docs/adr + work-logs。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 开发/测试 | required checks 全绿 + Leader APPROVED |
| 真实模型冒烟 | 企业 dev | C3 runner 用真实 provider 跑一次 golden |

## 7. 技能使用
- cameltv-agent-team（本流水线）；cameltv-bug-guard（except 顺序/降级分类/StaticPool）；karpathy-guidelines。
