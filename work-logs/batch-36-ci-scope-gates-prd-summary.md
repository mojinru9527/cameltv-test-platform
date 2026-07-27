---
title: "Batch 36 CI 按变更范围分层 PRD"
owner: "product"
last_reviewed: "2026-07-23"
status: "approved"
tags: ["ci", "github-actions", "agent-team"]
---

# 问题陈述

当前每次向已打开 PR 推送提交，`main-quality-gate.yml` 与 `pr-check.yml` 都会重新执行前后端全部检查。文档、Git 治理或单端修改因此承担不相关的安装和全量回归成本，Batch 35 的纯证据提交也重复等待约 6 分钟。

# 开始确认

| 字段 | 记录 |
|---|---|
| Workflow | `agent-team` |
| Executor | `codex` |
| 入口 | ChatGPT/Codex 桌面客户端 |
| 日期 | 2026-07-23 |
| 状态 | 用户已明确确认，可开始 Batch 36 |

# 成功指标

| 指标 | 基线 | 目标 |
|---|---:|---:|
| 文档/Git 治理 PR 的重型前后端 jobs | 6 | 0 |
| 后端单域 PR 的前端重型 jobs | 3 | 0 |
| 前端单域 PR 的后端重型 jobs | 3 | 0 |
| required check 名称缺失 | 0 | 0 |
| 未知路径误跳过双端测试 | 允许风险 | 0 |

# 用户故事与验收

- 作为开发者，我希望无关域测试被跳过，以便减少 PR 等待时间。
  - Given 仅修改 Markdown/Git 治理 / When PR checks 运行 / Then required contexts 成功返回且前后端依赖安装与测试不执行。
- 作为维护者，我希望单端修改仍得到完整相关回归。
  - Given 修改后端文件 / When PR checks 运行 / Then后端 required/扩展检查执行，前端重型检查跳过。
- 作为仓库负责人，我希望分类失败时偏向安全。
  - Given 未识别路径、CI/部署配置或空文件集 / When 分类 / Then 双端测试均执行。

# 非目标与 C 条件

- 不减少现有测试命令，不改变覆盖率/a11y 的软硬门禁级别。
- 不改变 ruleset 的三个 required context 名称、squash-only 或分支保护。
- 不承诺同一受影响域在后续 push 时复用旧 SHA 的测试结果；最新 PR SHA 仍重新执行相关域测试。
- `C-CONDITIONS.md` 的 32 个 Open 条件均为平台功能、环境或生产验收事项，与 CI 调度优化无关，本批次全部豁免且不改变其状态。

# 官方约束

GitHub 官方文档说明：顶层路径过滤跳过整个 required workflow 会让检查保持 Pending；job 级条件跳过则报告成功。因此本批次保持 workflow 常驻，只条件化 job/step。参考：[Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks)。
