# Batch 161 — P1-P3 五组问题修复 + 生产复验 QA 报告

> **QA (🔍)** | Date: 2026-08-12 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 13（G1-G5 + follow-up1/2/3 + 门禁 + 生产复验） | 13 | 0 | 0 |

## 可执行门禁（命令 + 结果）
- 后端 `ruff check app --select F821` → All checks passed ✅
- 后端全量 `pytest -q`（每轮）→ 1382 passed / 0 failed / 3 skipped ✅（最后轮含 follow-up3）
- `alembic heads` → 单头 `20260812_batch157_exec_link` ✅
- 前端 `npm run typecheck` → ✅；`npm run build` → ✅；`npm test` → 113 files / 460 tests ✅
- 生产复验：新后端探针（batch-execute 返回 `failed` 字段）✅；模型 `AI_MODEL=deepseek-v4-flash`

## 逐条件验证
### G1（P1）15.0.0 需求→用例生成
- 根因1：`ai_tasks._run_generate` 未 await 协程 → cherry-pick 6988e3a 修复。
- 根因2（follow-up1）：异步 worker 用 `project_id=0` 查文档 → 内容为空 → 0 用例；按 `task.project_id` 修复。
- 根因3（follow-up2）：异步结果未持久化 → UI 查看/导入为空；`_run_generate→update_ai_result`、`_run_extract→update_extraction` 修复。
- 生产复验：15.0.0 doc#10 异步生成 **338 条** → 导入 **276 条**；16.0.0 doc#11 异步生成 **405 条** → 导入 **178 条**（227 旧条去重跳过）；用例库 7879 → **8562** ✅

### G2（P1）失败自动转缺陷/报告/通知
- 代码：逐条容错 + execute-all/auto-execute/batch-execute 统一触发（batch-161）。
- 根因4（follow-up3）：`create_defect/create_report` 仅 flush，链路未 commit → 后台会话回滚；链路末尾统一 `db.commit()`。
- 生产复验：plan4 batch-execute 1 条失败 → 自动生成 **[AI分诊] 缺陷 4 条 + 失败自动报告 1 份**（RP-20260812-003）✅

### G3（P1）蓝湖证据采集
- 自动登录重试 1 次 + Cookie 双通道持久化 + 错误区分（已上线）。
- 生产复验：#30（15.0.0）失败信息已升级为「未配置 LANHU_USERNAME/LANHU_PASSWORD，无法自动登录」——错误可操作 ✅
- 遗留：pinned lanhu-mcp 子模块无 `lanhu_login` 钩子，自动登录无法真正完成 → 登记 **C161-1**（需升级子模块或用户手动粘贴 Cookie）。

### G4（P2）大计划一键执行 / 删除 / 报告统计 / 失败原因
- execute-all 批量预载用例 + 批量落库：plan4（405 条）执行 **3.4s**（此前 2615 条 >120s）✅
- 需求文档删除接口复测：DELETE /requirements/12 正常（UI 弹窗为自动化选择器误判）✅
- 报告统计：列表 5 与 trends total_reports 一致 ✅
- 接口任务失败原因：任务详情每项 status + error_message（如“请求超时 (30s)”）✅
- 遗留：15.0.0 定时调度（目标计划含 API 用例）触发被环境预检拦截 → 登记 **C161-2**（调度需绑定执行环境）。

### G5（P3）surface / Playground / 饼图 / 新建用例
- surface 按“域+模块”推断：生产用例库 surface 用户端 5012 / 运营后台 3437 / 其他 79（此前其他 89，已显著收敛；残留 79 待回填 → 登记 **C161-3**）✅
- Playground 编译错误内联展示（`功能用例 TC-NOT-EXIST-161`）✅；饼图图例「3040（37.7%）」括号分隔 ✅
- UI 新建用例表单：zod 校验存在（此前为自动化误操作）；复测正常 ✅

## 缺陷列表（复验过程中新发现）
| # | 级别 | 描述 | 证据 | 状态 |
|---|------|------|------|------|
| 1 | P1 | 异步 AI 任务 project_id=0 查文档 → 内容为空 | 生产 generate-async 0 用例 + AI“需求文档为空” | 已修复（follow-up1） |
| 2 | P1 | 异步 AI 结果未持久化 → UI 查看/导入为空 | doc11 cases 仍为旧 227 | 已修复（follow-up2） |
| 3 | P1 | 自动转缺陷/报告未 commit → 后台会话回滚 | 生产触发后缺陷/报告仍 0 | 已修复（follow-up3） |
| 4 | P2 | 15.0.0 定时调度含 API 用例但未绑环境 → 触发失败 | schedule trigger execution_failed | 登记 C161-2 |
| 5 | P1 | 蓝湖自动登录依赖 lanhu-mcp lanhu_login（子模块缺失） | #29/#30 失败 | 登记 C161-1 |
| 6 | P3 | surface 仍有 79 条“其他” | taxonomy 其他 79 | 登记 C161-3 |

## 发布建议
状态: READY ✅（5 个代码 PR #221-#224 已合入，生产复验通过；3 个 C 条件跟进）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d vs 实际 1d | 0/3/1/1（复验新发现） | 3 次 follow-up | 异步/后台任务事务边界、跨会话漏检、单测共享会话 | 异步 worker 路径单独加“独立会话持久化”测试；后台任务必须显式 commit |

**技能使用**: cameltv-bug-guard（envelope/事务/测试夹具）、vision（截图识别）、playwright-skill（浏览器复验）
