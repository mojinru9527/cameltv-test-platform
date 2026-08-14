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

## 日期

2026-08-14

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

## 关联

- 实现：`app/services/dsh/`、`app/api/v1/dsh_tasks.py`、`app/models/dsh_task.py`、
  `app/services/knowledge/agent_orchestrator.py`、`frontend/src/pages/dsh-tasks/`
- 配置：`app/core/config.py`（DSH_*）、`backend/.env.example`
- 本地工具：`dsh-cameltv-web.cmd` / `dsh-cameltv.cmd`（C:\Users\26029\bin）
- C 条件：C172-1（生产沙箱加固，见 C-CONDITIONS.md）
