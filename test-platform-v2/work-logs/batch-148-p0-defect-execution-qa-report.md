# Batch 148 — QA 报告（P0 缺陷契约 + 执行根因可见/环境预检）

> **QA (🔍)** | Date: 2026-08-11 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 2 (C147-1/C147-2) | 2 | 0 | 0 |

## 可执行门禁（命令、退出码、日志摘要）

| 门禁 | 命令 | 退出码/结果 |
|------|------|-------------|
| 后端 F821 | `python -m ruff check app/ --select F821` | 0，All checks passed |
| 后端受影响 pytest | `python -m pytest tests/test_testplan.py tests/test_batch148_p0_fixes.py tests/test_api_execution_target_policy.py -q` | 0，22 passed（19.16s） |
| 后端导入 | `python -c "import app.main"` | 0（solox 警告为既有基线） |
| Alembic | `alembic heads`；临时 SQLite `upgrade head` + `downgrade -1` | 单头 `20260811_batch148_execution_error_fields`；三列增减正确 |
| 前端 typecheck | `npm run typecheck` | 0 |
| 前端 build | `npm run build` | 0，✓ built in 11.05s |
| 前端全量 vitest | `npx vitest run` | 0，111 files / 450 tests passed |
| 本地端到端冒烟 | Playwright（worktree 独立库） | 缺陷创建/执行历史/预检三路径通过，0 pageerror |

## 逐条件验证

### C147-1 缺陷新建 422 契约修复 + 前端错误边界
**变更文件**: backend/app/schemas/defect.py:16、backend/app/services/defect_service.py:162、frontend/src/api/client.ts:31-50、frontend/src/pages/defect/DefectFormDialog.tsx

| 检查项 | 结果 | 说明 |
|--------|------|------|
| POST /defects 不传 assignee_id | ✅ | HTTP 200 code=0，assignee_id=0（pytest 2/2） |
| POST /defects assignee_id=null | ✅ | HTTP 200（pytest） |
| 前端 422 数组 detail 字符串化 | ✅ | client-422-detail.test 3/3；不再把对象当 React child |
| 缺陷弹窗失败态 | ✅ | DefectFormDialogFailure.test 2/2：失败显示可读错误、不关闭、不崩溃 |
| 浏览器端到端 | ✅ | toast「缺陷已创建」，0 pageerror（evidence/batch-148/defect-create.png） |

### C147-2 执行失败根因可见性 + 环境/Token 预检
**变更文件**: backend/app/models/test_plan.py、backend/alembic/versions/20260811_batch148_execution_error_fields.py、backend/app/services/test_plan_service.py、backend/app/schemas/test_plan.py、frontend/src/api/testplan.ts、frontend/src/pages/testplan/PlanDetail.tsx

| 检查项 | 结果 | 说明 |
|--------|------|------|
| test_execution 三独立字段 + 迁移 | ✅ | status_code/error_type/error_message；upgrade/downgrade 幂等 |
| 新执行记录写独立字段 | ✅ | 冒烟首行 error_type=NETWORK_ERROR、error_message=连接失败… |
| 历史 JSON 回填解析 | ✅ | pytest test_execution_history_backfills_error_fields_from_json |
| 执行历史 UI 三列 | ✅ | 表头「失败原因/HTTP 状态/失败阶段」；冒烟截图 |
| 前端未选环境拦截 | ✅ | toast「计划包含 API 用例，请先选择执行环境…」；0 环境场景冒烟 |
| 后端无环境拦截 | ✅ | code=1 + 明确 msg，0 条新执行记录（pytest + 冒烟） |
| 缺 base_url/缺 ${var} 拦截 | ✅ | pytest test_execute_all_blocked_missing_base_url / missing_token_variable |

## 缺陷列表
| # | 严重级(P0-P3) | 描述 | 证据 | 状态 |
|---|--------------|------|------|------|
| 1 | P3 | 项目仅 1 个环境时自动选中（设计内），前端守卫不提示；后端仍强制校验兜底 | smoke9/10 | 已接受（设计行为） |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0

## 复盘卡（Batch 75 起强制）
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h vs 实际 3.5h | 0/0/0/1 | 1 | 测试环境：单环境自动选中与首登改密 | 冒烟脚本先检查首登改密与自动选中语义 |

**技能使用**: cameltv-bug-guard → 迁移 inspector 守卫/错误提取链/Select sentinel 核对；playwright-skill → 本地端到端冒烟证据
