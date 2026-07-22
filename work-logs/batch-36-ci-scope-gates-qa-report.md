---
title: "Batch 36 CI 按变更范围分层 QA 报告"
owner: "qa"
last_reviewed: "2026-07-23"
status: "passed"
tags: ["qa", "ci", "github-actions"]
---

# 当前判决

`PASS`。分类红绿测试、workflow 契约、本地治理验证、PR #61 首轮 11/11 checks、基础审计、pending 负向门禁和用户 Codex 结束确认均已通过。本证据提交后，必须等待最新 SHA 的 required/扩展检查再次成功并通过最终审计，才可合并。

# 验收矩阵

| 条件 | 状态 | 证据 |
|---|---|---|
| 文档/Git 治理跳过双端重测试 | ✅ | `test_scope_matrix` |
| 后端/前端/混合路径正确分类 | ✅ | `test_scope_matrix`，含 `lanhu-mcp` Gitlink 边界 |
| 未知/CI/部署路径双端 fail-safe | ✅ | `test_scope_matrix` |
| required contexts 始终存在 | ✅ | 静态契约、ruleset API 及 PR #61 两个固定汇总均通过 |
| detector 失败阻断 required jobs | ✅ | 固定汇总 job 的 fail-closed 契约断言通过 |
| main push/manual 强制全量 | ✅ | `test_push_and_manual_paths_force_both_domains` |
| 真实 Draft PR | ✅ | PR #61，首轮 11/11 SUCCESS，MergeState=CLEAN |
| 用户结束确认 | ✅ | 2026-07-23：Codex；授权最终审计、Ready、squash 与安全清理 |

# 本地执行证据

| 检查 | 结果 |
|---|---|
| `python scripts/ci/test_classify_ci_changes.py` | PASS，10 tests |
| Python `py_compile` | PASS |
| 全部 `.github/workflows/*.yml` YAML 解析 | PASS |
| `git diff --check` | PASS |
| `python scripts/check_doc_freshness.py --ci` | PASS，0 过期、0 警告；仓库既有无 frontmatter 清单不阻断 |
| `verify-ai-worktree.ps1` | PASS，schema v3 / Agent Team / Codex / start confirmed / completion pending |
| `test-ai-worktree-tools.ps1` | PASS，入口、双确认、legacy、push/delete 与 protected push guard |
| main ruleset API | PASS，仅 squash；三个 required context 与变更前一致 |
| 业务代码隔离 | PASS，Batch 36 没有修改 `test-platform-v2/` |

当前系统没有可用的 Git Bash 运行时，因此未重复执行未修改的 `.githooks/pre-push` bash 语法检查；同一 hook 已由 `test-ai-worktree-tools.ps1` 的真实临时仓库流程覆盖，远端 `AI/Git 交付策略` 还会在 Ubuntu runner 执行。

# 首轮远端执行证据

| 检查 | 结果 |
|---|---|
| 范围识别 | 2/2 SUCCESS；完整 PR diff 含 workflow，正确输出 backend/frontend 双端受影响 |
| 后端/前端重型回归 | 2/2 SUCCESS；实际执行，未误跳过 |
| 两个固定 required 汇总 | 2/2 SUCCESS |
| backend、PG、frontend、a11y 扩展 | 4/4 SUCCESS |
| `AI/Git 交付策略` | SUCCESS |
| 基础 PR 审计 | PASS：PR #61、Draft、scope、本地/远端/PR SHA 一致 |
| pending 最终审计负测 | PASS：11/11 全绿时仍仅因 completion pending 被拒绝 |
| Batch 36 完成确认 | PASS：schema=3、workflow=agent-team、executor=codex、start/completion 均 confirmed |

# 保护声明

本批次不修改 `test-platform-v2/` 业务文件；原 `F:\CamelTv` 工作区与安全备份保持不动。
