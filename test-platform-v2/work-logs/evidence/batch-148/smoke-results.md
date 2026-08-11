# Batch 148 — 本地端到端冒烟证据（2026-08-11）

> 环境：worktree 独立 SQLite（platform-batch-148-p0-defect-execution.db）+ 前端 5237 + 后端 8067，admin 首次登录改密后复测。

## 1. P0-01 缺陷创建（不选处理人）
- 操作：登录 → 缺陷管理 → 新建缺陷 → 只填标题 → 保存
- 结果：toast「缺陷已创建」；页面无 `pageerror`/console error；弹窗关闭
- 证据：`defect-create.png`

## 2. P0-02 执行历史根因可见
- 准备：API 用例（GET /x，含断言）+ 环境（base_url=http://127.0.0.1:1）+ 计划，选中环境后一键执行
- 结果：执行历史表头为「用例/结果/备注/失败原因/HTTP 状态/失败阶段/时间/链路」；
  首行：失败原因=「连接失败: [WinError 10061] …」、HTTP 状态=「-」（status_code=0 未发出请求）、失败阶段=「网络连接」(NETWORK_ERROR)
- 页面无错误；证据：`plan-execution-history.png`

## 3. P0-02 环境预检（前端 + 后端双保险）
- 0 环境项目点「一键执行」→ 前端 toast「计划包含 API 用例，请先选择执行环境（含 base_url 与变量）」，无请求发出；证据：`no-env-guard.png`
- 直接调后端 `POST /test-plans/{id}/execute-all`（无 environment_id）→ `{"code":1,"msg":"计划包含 API 用例，请先选择执行环境（含 base_url 与变量）后再执行"}`，0 条新执行记录
- 缺 base_url / 缺 ${token} 变量：后端回归测试覆盖（见 pytest 8 passed）

## 4. 硬门禁摘要
| 门禁 | 命令 | 结果 |
|------|------|------|
| ruff F821 | `python -m ruff check app/ --select F821` | ✅ |
| 受影响 pytest | `pytest tests/test_testplan.py tests/test_batch148_p0_fixes.py tests/test_api_execution_target_policy.py` | ✅ 22 passed |
| 前端 typecheck | `npm run typecheck` | ✅ |
| 前端 build | `npm run build` | ✅ |
| 前端全量 vitest | `npx vitest run` | ✅ 111 files / 450 tests |
| Alembic | `alembic heads` 单头；临时库 upgrade/downgrade | ✅ |
