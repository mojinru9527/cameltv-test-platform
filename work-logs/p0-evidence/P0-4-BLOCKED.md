# P0-4 阻塞分析：控制面浏览器不止 `/uitest`，且生产有未执行的可逆性缺口

> 状态：**PARTIAL**（277b-1 契约/执行器已合入；277b-2 未闭环）
> 日期：2026-11-09

## 1. 已完成

- `ExecutionJob(kind="ui")` 派发契约、`UiTestRun.execution_job_id`、状态投影、节点 `run_spec_files`（PR #502，`e7d744952`）；
- 默认 `local`，生产行为未变；
- 单测 12 条 + 全量回归 1332 passed。

## 2. 为什么不能直接"删 Dockerfile 的 playwright + 切 node"

### B1. 控制面 Chromium 的用户不止 `/uitest` 执行腿

| 使用者 | 代码 | 是否需要 Chromium |
|--------|------|:----------------:|
| `/uitest` 旧执行器 | `app/services/playwright_executor.py` + `ui_runner_queue` | 是（277b-1 已提供 node 替代） |
| 蓝湖证据截图 | `app/services/lanhu_evidence/*`（Python Playwright） | **是**，未迁移 |
| 页面 XHR 采集 `/ui-tests/capture` | `app/services/xhr_capture_service.py` | **是**，未迁移 |
| Playground 脚本执行 | `app/services/playground_service.py`（经 `playwright_executor`） | **是**，未迁移 |

只删 `playwright install` 会把 B1 中后三项打断；"控制面镜像无 Chromium"必须先把这四项一起迁走或显式降级。

### B2. 生产 DB 仍在旧 revision，部署 main 会触发 104 张表的不可逆 DROP

- 生产 `alembic current` = `20260927_ai_guard_and_job_attempts`；
- 当前 main 含 `20261007_platform_simplification_drop_tables`（upgrade 侧 DROP 104 张表，**downgrade 为 no-op**）；
- 任何一次部署当前 main 的 `alembic upgrade head` 都会执行该 DROP，属不可逆生产变更。

**部署当前必须满足**：① 用户确认简化批次范围；② 在发布窗口执行；③ 先做一次生产备份（2026-11-09 22:13 已产出 168MB dump，sha256 `8f100def…`）。

### B3. 真实节点 E2E 未做

- 节点机器需要 `npx playwright`（仓库 `test-platform-v2/tests/playwright` 已装依赖最佳）；
- 本机/CI 无 Playwright 浏览器，未完成"真实节点跑通 `/uitest`"的验收。

## 3. 建议的 277b-2 执行顺序（需发布窗口）

1. **先迁 B1 的三项浏览器依赖**（或明确降级：关闭 `/ui-tests/capture`、蓝湖截图、playground，并在 UI 标注不可用）；
2. 测试环境：`UITEST_EXECUTION_MODE=node` + 真实节点跑通 `/uitest`（report/screenshot/sha256 证据）；
3. 部署窗口：确认 104 表 DROP → 备份（已有）→ `alembic upgrade head` → 部署新 backend/frontend；
4. 控制面镜像才可删 `playwright install` 两行；`docker image inspect` 验证无 Chromium；
5. 产出 `P0-4-control-plane-no-browser.json`，守卫 P0-4 转绿。

## 4. 关联

- 13 号 §0 P0-4
- `docs/aiqe/baseline.md` C-07
- PR #502（277b-1 契约）
