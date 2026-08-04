# Batch 83 — PRD Summary（本地开发操作备忘，Agent Team 常驻资产）

> **Product (🟦)** | Date: 2026-08-04 | Status: Approved

mode: light
豁免理由: 纯文档 / 内部流程工具，不引入新行为/新接口/新配置/新依赖；按 SKILL.md「批次模式」判定为轻量批次，PM/Design 工件省略，QA/Leader/看板/流程回写/复盘卡照常。

## 1. 问题陈述

本地开发与主干视图边界不清晰：`F:\CamelTv` 曾长期停在旧分支（feature/batch-51），`git pull` 只更新当前分支、不会切分支，导致"拉了最新代码但工作区还是旧的"、batch-82 审计脚本缺失等实际困扰；同时 `.agents` 与 `.claude` 两份 Agent Team 技能存在漂移，Codex 运行时读取的是 git 忽略的本地镜像。需要一份常驻操作备忘，把主干视图规则、工作区隔离、批次生命周期、push 门禁固化，并作为 Agent Team 流程资产被后续批次引用。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量 |
|------|------|------|------|
| 备忘文档 | 无 | `docs/agent-team/local-dev-workflow.md` 存在 | 文件检查 |
| 覆盖面 | 无 | 铁律 / 标准流程 / 常见坑 ≥5 条 / 命令速查 | 内容核对 |
| 技能引用 | 无 | SKILL.md「关联」新增链接（.claude 入库 + .agents 本地镜像同步） | 文件检查 |
| CHANGELOG | 无 | .claude/.agents 各一条 batch-83 记录 | C75-2 核对 |

## 3. 非目标（本次不做）

- **不修改任何运行时行为/接口/配置/依赖**：纯文档 + 技能引用。
- **不修复技能双档既有漂移内容**：本批只同步新增的关联引用；漂移作为流程回写发现记录在 Leader 判决与备忘 §5。
- **不创建自动化门禁脚本**：继续使用现有 scripts/git 门禁。

## 4. 用户故事 + 验收标准

- As 本地开发者 / Agent Team 执行者, I want 一份不依赖对话记忆的操作备忘, so that 按统一流程建工作区、走 push/PR 门禁、避免误伤主干。
  - 验收：Given 最新 main / When 按备忘执行批次流程 / Then 工作区隔离、push 门禁、PR 合入门禁均可照做；备忘覆盖导致 batch-82 困惑的根因（pull 不切分支、main 被占用、venv 误报）。

## 5. 技术考量

- 事实源：`.claude/skills/cameltv-agent-team/`（入库）；`.agents/` 为 git 忽略的本地镜像（`.gitignore:97`）。
- 门禁：C75-1（mode 记录）、C75-2（流程回写 + CHANGELOG）、C75-3（推送前 audit-cconditions -RequireLatestBatch）、C76-2 / C80-1（无新增 WARN）。

## 6. 本批追加范围（Batch 83 进行中用户确认）

用户要求把 Agent Team 交付门禁收敛为**一次总确认**：一次确认覆盖本批次推送、创建 Draft PR、required checks 通过后合并到 main，不再逐次询问/二次确认；直接任务保持 AGENTS.md §2.4 逐次 Push 确认。据此追加：

- `AGENTS.md`（§2.1.2 / §2.3 / §2.4 / §2.5）：Agent Team 一次总确认措辞 + §2.4 Agent Team 例外。
- `.claude/skills/cameltv-agent-team/SKILL.md`、`DEPARTMENTS.md`（+ `.agents` 本地镜像）：标准流程 / Leader / 合入章节同步。
- `docs/agent-team/pipeline-modes.md`：两档共同强制项措辞。
- `scripts/git/audit-ai-pr.ps1`：最终审计不再强制完成确认。
- `.github/pull_request_template.md`：完成确认字段改为一次总确认。
- `docs/agent-team/local-dev-workflow.md`：§3.3 / §3.4 同步。
