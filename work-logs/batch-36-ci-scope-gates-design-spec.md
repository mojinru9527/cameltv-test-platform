---
title: "Batch 36 CI 按变更范围分层设计规范"
owner: "design"
last_reviewed: "2026-07-23"
status: "ready"
tags: ["ci", "github-actions", "design"]
---

# 分类接口

`scripts/ci/classify_ci_changes.py` 输入完整 PR 文件集合，输出字符串布尔值 `backend=true|false`、`frontend=true|false` 和可读 `reason`。

| 路径类型 | Backend | Frontend |
|---|---:|---:|
| Markdown、docs、work-logs、Agent/Git/CI 本地工具 | false | false |
| `test-platform-v2/backend/**`、`lanhu-mcp` 子模块指针、`.gitmodules` | true | false |
| `test-platform-v2/frontend/**` | false | true |
| 同时命中前后端 | true | true |
| `.github/workflows/**`、deploy、Jenkins | true | true |
| 未知路径、空集合、`--force-all` | true | true |

# Required workflow 状态机

1. workflow 对所有 `pull_request -> main` 始终创建。
2. detector 成功后输出域影响。
3. 域命中时，独立 `backend_tests` / `frontend_tests` 执行原有全部重步骤；域未命中时重 job 为 skipped。
4. 固定名称 required 汇总 job 使用 `if: always()` 始终创建：
   - detector 失败 → 汇总 job 明确失败；
   - 域命中且重 job SUCCESS → 汇总 job SUCCESS；
   - 域未命中 → 汇总 job 输出跳过理由并 SUCCESS；
   - 域命中但重 job 非 SUCCESS → 汇总 job 明确失败。
5. `push main` 与手动触发强制双端全量。

# Extended workflow

四个非 required jobs 使用 job 级条件：backend/PG 绑定 backend，frontend/a11y 绑定 frontend。跳过状态对分支保护无影响，并清楚显示未执行。

# 安全约束

- 不在 workflow `on.pull_request` 添加 `paths`/`paths-ignore`。
- 不改变 required job 的 `name`。
- 分类器和 workflow 契约由同仓库 unittest 覆盖，并在 `AI/Git 交付策略` 中执行。
- 分类使用 PR base/head SHA 的完整 diff，不按单次 push 增量复用旧检查，避免失败代码通过“补一个文档提交”绕过。
