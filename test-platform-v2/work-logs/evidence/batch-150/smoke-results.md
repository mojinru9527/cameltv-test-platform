# Batch 150 — 本地端到端冒烟证据（2026-08-11）

> 环境：worktree 独立 SQLite + 前端 5239 + 后端 8069。SPA 内导航：工作台→测试计划→用例服务→目标环境→缺陷管理→用例脑图。

## Network 计数（会话级缓存/去重生效）
| 接口 | 修复前基线 | 冒烟实测 |
|------|-----------|---------|
| /system/menus | ×53 | **×1** |
| /environments | ×6 | **×1** |
| /test-cases/domains | ×4 | **×1** |
| /test-cases?page_size=10000 | 10.1MB | **0 次**（mindmap 改用 /test-cases/taxonomy） |
| /test-cases/taxonomy | - | ×2（KB 级聚合） |

- 页面 0 pageerror；脑图渲染正常（截图 mindmap-taxonomy.png）。

## 代码级覆盖
- client cachedGet：缓存命中/并发去重/clearApiCache/force 单测 4/4
- useDebouncedValue：300ms 防抖单测 1/1
- usePerfWebSocket：500ms→30s 指数退避（setTimeout 链）
- integration：page_size=1 探针 2 处改为 fetchTestCaseStats

## 硬门禁
| 门禁 | 结果 |
|------|------|
| 前端 typecheck/build | ✅ |
| 前端全量 vitest | ✅ 113 files / 455 tests |
| 后端 ruff F821 | ✅（无后端代码改动） |
| alembic heads | ✅ 单头 |
