# Batch 248 — PRD Summary

> **Product (🟦)** | Date: 2026-09-17 | Status: Draft
> **批次模式**：完整批次（引入新行为/新接口/新配置，按 `pipeline-modes.md` §2 判定）
> **执行器**：Codex（模式① 单会话角色扮演，用户已确认）

## 1. 问题陈述

用户明确要求：**AI 全链路在本地 ChatGPT 客户端运行，平台上不需要任何 AI 能力；平台只负责派发 AI 任务、接收并展示结果。**

现状与该目标的差距（均为 2026-09-17 生产核查实证，见 `work-logs/evidence/batch-248/`）：

1. 平台仍在跑 LLM：`POST /requirements/{id}/extract|generate` 直接调用 `app.services.ai_service`，最终经 `ai-gateway` 打向云端 DeepSeek。
2. 该外部 key 已失效：网关日志 `AiClientUnavailableError: AI API returned HTTP 401`；两个项目的 provider 自检均报「API Key 无效或已过期（401）」。
3. 失败是静默的：需求拆分返回 `modules: []` 且把 `extraction_status` 置为 `confirmed`（0 模块也算"已确认"）。
4. 所谓的"外置链"是空壳：`AiJob` 表与 5 个 agent 端点存在，但**全仓库没有任何地方创建 AiJob**（`AiJob(` 只出现在模型定义），`ai_agent_service` 仅被自身 router 引用；前端无 AI Job 页面；register 不发放 agent 凭据。

即：平台既没有真正停止推理，也没有可用的"平台派发 → 本地执行 → 平台展示"闭环。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 平台侧 LLM 调用（需求拆分/生成路径） | 100% 请求走 ai_service | 0 次（`ai_platform_inference=false` 时） | 本批 QA 用例 + 架构守卫 |
| 需求拆分端到端（无任何 AI Key） | 不可用（401 静默空结果） | 可完成：建 Job → 本地产出 → 导入用例库 | 本批 QA |
| AI Job 可观测性 | 无页面、无列表 API | 列表/详情/结果/Agent 在线状态可见 | 本批 QA |
| 本地 Agent 可用性 | 无执行端 | `register/doctor/next/report/import` 全通 | 本批 QA |

## 3. 非目标（本次不做）

- 不做蓝图 §9.4 的完整五页（Result Diff、审核工作流、模型评测）；本批只做「列表 + 详情 + 结果查看 + 导入」。
- 不做多 agent 并发池与优先级队列；沿用现有 `capability` 过滤 + 单任务认领。
- 不做 embedding/RAG 本地化（知识库检索仍在平台侧，且不依赖 LLM key）。
- 不做历史 `AiTask` 数据迁移；旧链路保留只读查询能力。
- 不做 UI 自动化脚本资产上传（属 DEF-013，另批）。
- **C 条件处理**：`C-CONDITIONS.md` 当前 41 条 Open，与本批主题（本地 AI Agent 闭环）无直接关联，本批不承接；本批新增条件将在 Leader Verdict 中登记（预计 2 条）。

## 4. 用户故事 + 验收标准

**US-1 本地跑 AI（A 模式，模型可切换）**
As a 测试工程师, I want 在本地 ChatGPT 客户端认领平台下发的 AI 任务并回传结果, so that 平台不需要任何 AI Key 也能完成需求拆分与用例生成。
验收：Given 平台 `AI_PLATFORM_INFERENCE=false` 且无任何 provider / When 我在需求页点「AI 拆分」/ Then 平台创建一个 `AiJob(status=pending)` 并返回 `job_id`，且不发起任何 LLM 调用。
验收：Given 一个 `pending` 的 AiJob / When 本地 agent 用 agent token `claim` 并 `report` 结果 / Then 平台落 `AiResult`，我能在 AI 任务页看到结果与使用的模型名。

**US-2 平台只展示与导入**
As a 测试工程师, I want 把本地产出的功能用例一键导入用例库, so that 我不必手工复制。
验收：Given 一个 `completed` 的 generate 类型 Job / When 我点「导入用例库」/ Then 用例按现有 `requirements/{id}/import` 规则入库，返回 imported/skipped 计数，重复导入幂等（不产生重复用例）。

**US-3 Agent 身份可控**
As a 平台管理员, I want agent 有独立可吊销凭据, so that 不必把真人账号密码交给本地进程。
验收：Given 已注册 agent / When 我用 `X-AI-Agent-Token` 调用 claim/report / Then 通过鉴权且 `last_used_at` 更新；Given token 被禁用 / Then 返回 401。

**US-4 任务不丢**
As a 测试工程师, I want 客户端崩溃后任务能回到待认领, so that 我不会拿到永久 running 的僵尸任务。
验收：Given 一个 `running` 且 `heartbeat_at` 超过 `AI_JOB_STALE_SECONDS` 的 Job / When 另一个 agent claim / Then 该 Job 被回收为 `pending` 并成功认领。

## 5. 技术考量

- 复用既有 `ai_jobs` / `ai_agents` / `ai_results` 表，不新建第二套 Job 模型（延续 PR-01「唯一事实」原则）。
- Agent 凭据：新增 `ai_agent_token` 表（sha256 存哈希，明文仅注册时返回一次），不复用用户 JWT。
- 需求拆分/生成的返回契约从"结果"变为"Job 引用"，前端需同步改造（含 422/404 既有错误提取链）。
- 无平台 LLM 时失败必须显式（禁止 0 模块静默 confirmed）：本批顺带修正该缺陷。
- 风险：现有生产需求页依赖同步返回，改动需与前端同批上线；`AI_PLATFORM_INFERENCE` 默认 false 会让"平台内 AI"失效（这正是用户要求），需在发布说明中标注。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 团队 | PR required checks 全绿 + Leader APPROVED |
| 生产发布 | 全员 | 按发布火车；发布说明标注「平台内 AI 默认关闭」 |
| 本地接入 | 需要 AI 的成员 | 按 `docs/ai/local-ai-agent.md` 跑通一次 register→claim→report→import |

## 7. 技能使用

- `cameltv-agent-team`（模式①）→ 六部门工件与本流水线
- `cameltv-bug-guard` → 编码前扫描；本批需重点防的 4 条：静态路径先于路径参数、envelope 码 vs HTTP 码、pytest 夹具 StaticPool、前端 useEffect cleanup/错误提取链
- `cameltv-ui-conventions` → 前端 AI 任务页组件与四态（Design 部门执行）
