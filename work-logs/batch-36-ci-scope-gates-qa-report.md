---
title: "Batch 36 CI 按变更范围分层 QA 报告"
owner: "qa"
last_reviewed: "2026-07-23"
status: "local_pass"
tags: ["qa", "ci", "github-actions"]
---

# 当前判决

`LOCAL_PASS / REMOTE_PENDING`。分类红绿测试、workflow 契约、YAML/编译/治理验证已通过；真实 Draft PR 与用户结束确认尚待执行。

# 验收矩阵

| 条件 | 状态 | 证据 |
|---|---|---|
| 文档/Git 治理跳过双端重测试 | ✅ | `test_scope_matrix` |
| 后端/前端/混合路径正确分类 | ✅ | `test_scope_matrix`，含 `lanhu-mcp` Gitlink 边界 |
| 未知/CI/部署路径双端 fail-safe | ✅ | `test_scope_matrix` |
| required contexts 始终存在 | ✅/⏳ | 静态契约及 ruleset API 通过；待 PR 实际 check runs |
| detector 失败阻断 required jobs | ✅ | 固定汇总 job 的 fail-closed 契约断言通过 |
| main push/manual 强制全量 | ✅ | `test_push_and_manual_paths_force_both_domains` |
| 真实 Draft PR | ⏳ | 待 push |
| 用户结束确认 | ⛔ | 首轮验证后问询 |

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

# 保护声明

本批次不修改 `test-platform-v2/` 业务文件；原 `F:\CamelTv` 工作区与安全备份保持不动。
