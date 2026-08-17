---
title: "ADR-0018: 接入 DeepSeek Harness（dsh）执行型智能体能力"
owner: "tech-lead"
last_reviewed: "2026-08-14"
status: "active"
expires: "2027-02-14"
tags: ["adr", "ai", "deepseek", "harness", "agent"]
related: ["0007-deepseek-llm-test-case-generation.md", "0014-single-main-trunk-ai-worktrees.md"]
---

# ADR-0018: 接入 DeepSeek Harness（dsh）执行型智能体能力

## 状态

✅ 已采纳（Batch 172，首版 A/B/C 落地）
✅ 扩展（Batch 191，/dsh-tasks 支持 AgentTeams 团队模式，方案 B1）

## 日期

2026-08-14（首版）；2026-08-17（Batch 191 团队模式扩展）

## 背景

平台现有 AI 能力是「直连 DeepSeek Chat API」的受限形态：
- `ai_service.py` 两段式文本生成，无工具、无执行验证；
- Agent 工作台的 Agent 是「RAG + LLM 推理」型，只产出文本工件，不能真正操作系统/代码/测试环境。

DeepSeek Harness（dsh）是 DeepSeek 官方开源 agent harness（MIT，`everything is a plugin`，
由 Cordis 驱动），提供 bash / str_replace_editor / subagent / workflow 等工具，可真实执行任务。
用户要求把 dsh 作为平台的新执行引擎，落地三个形态：A（AI 用例生成 harness 模式）、
B（Agent 工作台执行型 Agent）、C（DSH 任务执行模块）。

## 决策

1. **后端统一抽象 dsh 执行**：新增 `app/services/dsh/dsh_runner.py`，暴露
   `run_dsh_task(task, workspace, session_root, model, timeout) -> DshRunResult`
   与 `runtime_available()`。上层（ai_service / agent_orchestrator / dsh_task_service）只依赖该抽象。
2. **双运行时**：
   - `dsh_runtime=node`：子进程调用 Node CLI headless（`node <entry> --profile headless <task>`），
     用于本地 Windows 开发（官方 Python SDK 持久 PTY 仅支持 POSIX）。
   - `dsh_runtime=python-sdk`：官方 `deepseek-harness-sdk`（bundled runtime，无需 Node），用于生产 Linux。
   默认 `node`，通过 `DSH_RUNTIME` 切换。
3. **配置外置**：`DSH_*`（enabled/runtime/model/base_url/api_key/session_root/harness_path/cordis_config/
   timeout/max_output_chars/workspace）走 `settings` + `.env`，无硬编码密钥；凭据优先 `DSH_API_KEY`，
   回退 `AI_API_KEY`。
4. **A：AI 用例生成 harness 模式为可选项**：`generate_test_cases(use_harness=None)`，None 跟随
   `DSH_ENABLED`；默认关闭，行为与现状一致；harness 执行失败/解析失败自动降级直连，不硬失败。
5. **B：Agent 工作台执行型 Agent**：`AGENT_META` 新增 `dsh_execution`；orchestrator 对该类型走
   dsh_runner，输出持久化为 AiArtifact；可用性跟随 `runtime_available()`。
6. **C：DSH 任务执行模块**：新表 `dsh_task` + Alembic 迁移；服务侧复用 `ai_tasks.py` 的 DB 认领
   worker 模式；API `/api/v1/dsh-tasks/*`（health/create/list/detail/cancel），权限复用
   `agent:view` / `agent:run`；前端新增 `/dsh-tasks` 页面与菜单（`menu:dsh_tasks`）。
7. **版本锁定**：dsh 为开发者预览版，接口可能破坏性变更。本地开发以 `F:\deepseek-harness` 固定
   commit；生产 python-sdk 通过 `requirements.lock` 锁版本。本地启动器：`dsh-cameltv-web` /
   `dsh-cameltv`（复用平台 `AI_API_KEY`）。

## 后果

### 正面

- ✅ 平台获得真实执行型 AI 能力：可读文件、跑命令、生成并自校验用例。
- ✅ 默认链路零回归：A 的 harness 模式是可选开关，关闭时行为不变。
- ✅ 运行时抽象解耦：Windows 本地（node）与生产 Linux（python-sdk）共用同一结果结构。

### 负面 / 权衡

- ⚠️ **安全**：dsh agent 具备完整工具能力，必须在受控工作区/隔离容器运行；生产启用前需
  沙箱策略加固（C 条件登记：C172-1）。
- ⚠️ **成本**：harness 执行 token 消耗高于单次 chat；提交任务权限收归 `agent:run`（tester 只读），
  任务级超时（`DSH_TIMEOUT_SECONDS`）兜底。
- ⚠️ **预览版稳定性**：dsh 快速迭代，升级需回归 A/B/C 三条链路。
- ⚠️ **Windows 限制**：Python SDK 持久 PTY 仅 POSIX；Windows 本地必须用 node runtime。

## 弃选方案

- **方案 A：平台内嵌 dsh Web UI（3080）作为产品界面** — 与平台自身 UI 体系重复、权限难收敛，弃选；
  dsh Web UI 仅保留为本地开发工具。
- **方案 B：仅升级直连 LLM 提示词**（不引入 harness）— 无法获得真实执行/验证能力，弃选。
- **方案 C：每个功能独立接 dsh**（无统一抽象）— 运行时切换/测试成本高，弃选；统一走 dsh_runner。

## Batch 191 扩展：AgentTeams 团队模式（方案 B1）

2026-08-17 扩展 `/dsh-tasks` 支持团队模式（`mode=team`）：用户提交单一自然语言目标 +
批次模式（full/light），DSH 船长会话（`agent_teams_*` 九件套）自组织多成员团队执行。

- **模型最小扩展**：`dsh_task` 新增 `mode`（single|team，索引）与 `team_json`（Text，默认 `"{}"`）
  两列；`batch_mode` 随 `params_json` 落库，不加冗余列。
- **执行路由**：`run_dsh_task(mode=...)` — node 走 `--profile agent-team`
  （`$DSH_HOME/profiles/agent-team`），python-sdk 走内置 `team.cordis.yml`
  （minimal + `@nanmicoder/dsh-agent-teams` 插件行，可经 `DSH_TEAM_CORDIS_CONFIG` 覆盖）；
  团队超时 `DSH_TEAM_TIMEOUT_SECONDS`（1800s）；**沙箱语义完全复用**（ws-{uuid} 隔离工作区、
  并发闸门、文本配额，C172-1 不回归，无旁路）。
- **team_json 快照语义**：平台侧只读快照，内容 = 插件 `team.json` 持久化记录原文，
  全量幂等覆盖写（无增量合并）；实时轮询用「隔离根扫描 ws-*/ 首次命中锁定」，
  终态读取用 `DshRunResult.workspace` 精确路径；超长截断加 `_truncated` 标记
  （`DSH_MAX_OUTPUT_CHARS` 口径）。
- **线程安全（R-3）**：执行线程不碰 DB session；轮询线程每次用独立短 `SessionLocal`
  全量幂等写 `task.team_json`，绝不与执行线程共享 session。
- **API/前端**：`DshTaskCreate.mode`（Literal single|team）+ `params.batch_mode` 校验
  （team 必填 full|light，single 拒绝）；`DshTaskOut.mode/team_json`（字符串→dict，
  损坏 JSON 兜底 `{}`）；前端提交面板模式选择 + 批次下拉 + 列表类型徽标 + 详情团队进度树
  （running 3s 轮询，卸载清理遵循 React 副作用规范）。
- **配置**：`DSH_TEAM_TIMEOUT_SECONDS` / `DSH_TEAM_POLL_SECONDS` / `DSH_TEAM_PROFILE` /
  `DSH_TEAM_CORDIS_CONFIG` / `DSH_TEAM_HARNESS_PATH`（= DSH_HOME 覆盖，非 bin.js 路径）。
- **C 条件**：C191-1（python-sdk bundled runtime 加载 npm bundle 插件，失败 → deferred，
  node 先交付，不静默 fallback）；C191-2（running 团队任务取消延后）。

## 关联

- 实现：`app/services/dsh/`、`app/api/v1/dsh_tasks.py`、`app/models/dsh_task.py`、
  `app/services/knowledge/agent_orchestrator.py`、`frontend/src/pages/dsh-tasks/`
- 配置：`app/core/config.py`（DSH_*）、`backend/.env.example`
- 本地工具：`dsh-cameltv-web.cmd` / `dsh-cameltv.cmd`（C:\Users\26029\bin）
- C 条件：C172-1（生产沙箱加固，见 C-CONDITIONS.md）
