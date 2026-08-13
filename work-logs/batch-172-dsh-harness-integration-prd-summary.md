# Batch 172 — PRD Summary
> **Product (🟦)** | Date: 2026-08-13 | Status: Review | Executor: codex | 完整批次

## 1. 问题陈述

平台现有 AI 能力是「直连 DeepSeek Chat API」的受限形态，无法完成需要真实工具/执行的工作：

- **AI 用例生成（`app/services/ai_service.py`）**：两段式文本生成（骨架→反向评审），无工具、无执行验证。生成的用例无法自动校验结构、无法读取真实被测系统/接口来补全请求参数，遇到需要「跑一下确认」的问题只能靠模型猜测。
- **Agent 工作台（`/api/v1/agent.py`）**：现有 Agent 是「RAG 检索 + LLM 推理 → AiArtifact」型（requirement_analysis / impact_analysis / case_generation / failure_analysis），只产出文本工件，**不能真正操作系统、代码、测试环境**。
- 用户需要平台具备「执行型 AI 能力」：提交自然语言任务 → 平台用带工具（bash/文件编辑/子代理/工作流）的智能体真实执行 → 返回可验证的结果与日志。

**DeepSeek Harness（`dsh`）** 是 DeepSeek 官方开源 agent harness（MIT），支持 bash/str_replace_editor/subagent/workflow/todo 等工具，可作为平台的新执行引擎。已在本地验证可运行（headless 模式真实调用 DeepSeek API 成功读取 CamelTv 仓库）。用户明确要求 A（AI 用例生成引擎升级）、B（Agent 工作台接入执行型智能体）、C（新增 DSH 任务执行模块）三个功能都做。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| A：harness 模式用例生成结构合规率 | 直连模式基线（现有 parse 容错） | 与直连模式持平或更高，0 schema 解析失败 | 本批 QA 回归 |
| A：默认链路零回归 | 现有 `ai_service.py` 全量用例生成测试通过 | harness 模式为**可选项**，默认行为不变，全量回归无新增失败 | 本批 QA 回归 |
| B：执行型 Agent 可触发并可追踪 | 无 | `/agents/types` 新增 dsh 执行型；触发→队列→runs 记录含 status/output/log；成功与失败均可查 | 本批 QA 回归 |
| C：DSH 任务模块闭环 | 无 | 提交任务→列表/详情状态流转（pending/running/success/failed）→最终输出可查→历史可检索 | 本批 QA 回归 |
| 通用 | — | 后端 F821/相关 Pytest、前端 typecheck/build/相关 Vitest 全绿；无新增 console.log/print 调试残留 | 本批 QA 硬门禁 |

## 3. 非目标（本次不做）

- **不在平台内嵌 dsh Web UI（3080 端口）作为产品界面**：平台用自己已有的 UI 形态呈现 A/B/C；dsh Web UI 仅作为本地开发工具保留在 `F:\deepseek-harness`（用户已确认两条线并存）。
- **不替换现有 AI 链路的默认行为**：A 的 harness 模式是可选项（配置/参数开关），默认仍走现直连链路，避免大面积回归。
- **不做生产环境的 dsh Web UI / 独立服务部署**：本批只做平台 API + 任务执行集成；dsh 运行时以进程内/子进程方式由后端编排。
- **不做 APP 真机/金融档 UI 自动化**（C167-1 的 T1 金融档、C170-2 外部授权）。
- **Open C 条件豁免（Product 开工检查）**：C167-1（APP 真机/授权，外部）、C167-3（`release_bundle.api_spec_url` 接入 import-api-spec，与 dsh 集成无关）、C170-2（T1 金融档外部授权）均与本批无关，保持 Open，由对应后续批次处理。

## 4. 用户故事 + 验收标准

- As QA，I want AI 用例生成可切换 harness 执行模式（读取需求+技能规范，生成并**自校验**结构化用例），so that 生成质量更高且可执行验证。
  - 验收：Given 已配置 DSH 开关与凭据 / When 触发 harness 模式生成 / Then 返回与现格式一致的用例 JSON，schema 校验通过；未开启时行为与现状完全一致。
- As QA，I want 在 Agent 工作台触发「执行型智能体」执行真实任务（如跑接口回归、生成并校验用例），so that 平台能完成需要真实工具的工作。
  - 验收：Given 有 agent:run 权限 / When 触发 dsh 执行型 agent / Then 进入队列 → 后台执行 → runs 记录含 status/output/log；失败有原因，均可查询。
- As QA，I want 在平台提交一个 DSH 任务并查看执行过程与最终结果，so that 可以用自然语言让平台代理完成可执行工作。
  - 验收：Given 有对应权限 / When 提交任务 / Then 列表与详情可见状态流转与最终输出、历史可检索；无权限者不可见。

## 5. 技术考量

- **dsh 运行时接入策略（待 Design 定稿）**：生产 Linux 用官方 Python SDK（bundled runtime，无需 Node）；本地 Windows 开发用 Node CLI headless（`F:\deepseek-harness` 或仓库内锁定版本）作为后端子进程。统一由后端 service（如 `dsh_runner`）抽象，上层不感知运行时差异。
- **复用现有异步基础设施**：`task_worker.py` / `ai_tasks.py` / agent queue 已有异步任务模式（batch-161/163/169），A/B/C 复用，不新增重型队列。
- **新配置项**：`DSH_*`（enable / runtime 选择 / model / base_url / session_root / timeout 等）走 `settings` + `.env`，无硬编码密钥。
- **风险**：dsh 为开发者预览版，接口可能破坏性变更 → 锁定版本（requirements 锁版本 / 本地 clone 固定 commit），并写 `docs/adr/`。
- **成本控制**：harness 执行 token 消耗高于单次 chat → 任务级超时 + 执行前确认/额度提示（复用现有 AI 成本控制思路）。
- **Windows 限制**：持久 PTY 仅 POSIX → 本地 Windows 用 Node CLI 规避；生产 Linux 用 Python SDK。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 阶段 1（A）AI 用例生成 harness 模式 | 内部 QA | 后端单测 + 一次真实 harness 生成回归，默认链路零回归 |
| 阶段 2（B）Agent 工作台执行型 Agent | 内部 QA | 触发→执行→记录闭环，前后端硬门禁 |
| 阶段 3（C）DSH 任务执行模块 | 内部 QA | 任务提交→状态流转→结果/日志→历史检索，前后端硬门禁 |
| 合入 | 全量 | QA 全绿 + Leader APPROVED + 用户总确认 + PR checks |

## 7. 技能使用

- `cameltv-agent-team` → 六部门流水线与批次工件
- `cameltv-bug-guard` → Dev 编码前避坑清单
- `cameltv-ui-conventions` → Design/前端 UI 规范
- `test-case-design` → A 的用例生成输出规范（tests/test-case-standards）
- `karpathy-guidelines` → 保持改动聚焦、避免过度设计
