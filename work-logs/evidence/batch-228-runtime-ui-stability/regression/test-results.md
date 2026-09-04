# Batch 228 自动化与门禁结果

> Date: 2026-09-04 | Final local result: PASS

| 检查 | 结果 | 关键摘要 |
|------|------|----------|
| `npm ci` | exit 0 | 561 packages installed from lockfile |
| 前端定向 Vitest | exit 0 | 5 files / 10 tests passed |
| 前端全量 Vitest | exit 0 | 137 files / 622 tests passed |
| `npm run typecheck` | exit 0 | TypeScript build check passed |
| `npm run lint` | exit 0 | 0 warnings / 0 errors |
| `npm run build` | exit 0 | 3666 modules transformed，生产构建成功 |
| Worker heartbeat + registry | exit 0 | 23 tests passed；含失败重试、停止清理、过期淘汰、管理员状态、UTC 响应和能力单次批量查询 |
| 后端全量 Pytest | exit 0 | 2421 passed / 49 skipped / 1 xfailed / 0 failed / 60 warnings，567.57s |
| app import | exit 0 | `import app.main` passed |
| Ruff F821 | exit 0 | All checks passed |
| Alembic head | exit 0 | 单一 head `20260911_business_onboarding_context` |
| revision/single-head Pytest | exit 0 | 8 tests passed |
| route-layer guards | exit 0 | 4 tests passed |
| `audit-cconditions.ps1` | exit 0 | 0 hard / 0 warning |
| `dev-gate.ps1` | exit 1 | `PASS_WITH_WARN`；0 HARD / 330 全仓 WARN，其余 G1-G2 全过 |

## 门禁复核

- G0 首轮识别出本批心跳模块 2 处裸 `except: pass`，已改为明确 `return` 与兼容性 debug 日志；定向测试复跑通过，最终 `HARD=0`。
- 最终代码审查发现启动器工作目录落在仓库根，按 Runbook 执行时无法导入后端 `app`；已改为进入 `test-platform-v2/backend`，并在现有启动器测试中固定该路径契约。全部增量修正后 heartbeat + registry 23 项复跑通过，目标目录 `import app` 通过。
- 最终浏览器复验发现 naive UTC 心跳响应没有时区标记，Asia/Shanghai 浏览器少显示 8 小时；响应边界已补 UTC 标记，新增契约测试先红后绿，页面从 12:14 修正为 20:14。
- 完整 Worker 回归同时固定：列表/路由先淘汰过期节点、心跳不覆盖 DRAINING/DISABLED、OFFLINE 可恢复、TaskQueue 能力查询固定为一次批量 SQL。
- 330 条 WARN 是全仓待人工复核清单；本批修改文件在 verbose 结果中命中 0 条 WARN。既有基线 JSON 为 209 条，当前主干新增文件造成 121 条存量差异，不属于本批修改范围。
- 首次把前端全量测试与生产构建并行运行时，测试进程因本机资源竞争以 exit 1 提前结束，未产生失败用例集合；随后独占运行得到 622/622 通过。最终判定以独占复跑结果为准。
- 后端全量的 49 skipped、1 xfailed 与 60 warnings 均为现有测试标记或兼容性告警，没有失败集合。
