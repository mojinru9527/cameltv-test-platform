---
title: "Batch 36 CI 按变更范围分层 PM 计划"
owner: "pm"
last_reviewed: "2026-07-23"
status: "active"
tags: ["ci", "github-actions", "agent-team"]
---

# 交付切片

| 切片 | 验收标准 | 状态 |
|---|---|---|
| 1 分类契约红测 | 8 类路径矩阵在实现缺失时失败 | 完成：先 `ModuleNotFoundError`，workflow 契约随后 3 项红测 |
| 2 分类器实现 | 纯标准库、NUL 输入、GitHub outputs、未知路径 fail-safe | 完成：10 项测试通过 |
| 3 required jobs 分层 | 固定 context 始终产生结果，重步骤按域执行 | 完成：静态契约通过，待真实 PR |
| 4 extended jobs 分层 | backend/PG 与 frontend/a11y 分域 | 完成：静态契约通过，待真实 PR |
| 5 静态与真实 PR 验证 | YAML/契约/本地测试及 Draft PR 首轮检查 | 完成：PR #61 首轮 11/11 SUCCESS |
| 6 二次确认与交付 | 用户确认后最终审计、Ready、squash、清理 | 进行中：Codex 与最终交付授权已确认，待证据提交检查 |

# 质量要求

- 分类器未知输入必须双端全量，不能默认跳过。
- required job 的名称不得变化，detector 失败必须使 required jobs 失败。
- 不使用第三方路径过滤 Action，避免新增供应链依赖。
- 仅修改 CI、治理和 Batch 36 工件，不触碰测试平台业务代码。
