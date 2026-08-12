# Batch 155 — QA 报告（P1-07 自动链路 + P2 未收口 20 项）

> **QA (🔍)** | Date: 2026-08-11 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 21（C155-1 + P2 20 项） | 21 | 0 | 0 |

## 可执行门禁（命令、退出码、日志摘要）
| 门禁 | 命令 | 结果 |
|------|------|------|
| 后端 ruff F821 | `ruff check app/ --select F821` | ✅ 0，All checks passed |
| 后端受影响 pytest | `pytest tests/test_testplan.py tests/test_batch155_auto_chain.py tests/test_batch155_schedule.py tests/test_apitest_tasks.py tests/test_api_task_worker.py tests/test_apitest_assets.py tests/test_apitest_generation.py -q` | ✅ 62 passed |
| 后端全量 pytest | `pytest -q` | ✅ 1352 passed, 3 skipped, 0 failed |
| alembic heads | `alembic heads` | ✅ 单头 `20260811_b155_sched_reason` |
| 迁移临时库 | upgrade head → downgrade -1 → re-upgrade | ✅ 0 |
| 前端 typecheck | `npm run typecheck` | ✅ 0 |
| 前端 build | `npm run build` | ✅ built in 10.06s |
| 前端全量 vitest | `npx vitest run` | ✅ 113 files / 455 tests |
| scan-common-bugs | `scan-common-bugs.ps1` | ⚠️ 1 HARD 基线：`app/main.py:87 except OSError: pass`（不在本批 diff，豁免；WARN 255 基线） |
| audit-cconditions | `audit-cconditions.ps1` | ✅ 0 硬错 / 0 警告 |
| 凭据/调试扫描 | git diff 范围 grep | ✅ 无 console.log/print/breakpoint/debugger |

## 逐条件验证
### C155-1（C147-6 重开）失败自动转缺陷/报告/通知
**变更文件**: models/test_plan.py、schemas/test_plan.py、services/test_plan_service.py（run_failure_auto_chain）、services/notify_service.py（plan_failed）、api/v1/test_plan.py（后台任务）、PlanDrawer/PlanDetail（开关）
| 检查项 | 结果 | 说明 |
|--------|------|------|
| auto_defect_on_fail 模型/schema/API 贯通 | ✅ | 创建/更新/详情 roundtrip 单测 |
| 开关默认关闭 | ✅ | 默认 False，单测 skipped 分支 |
| 失败自动缺陷 | ✅ | rule triage → bug/case_defect → create_defect（预填 case/execution） |
| 失败自动报告 | ✅ | create_report（失败自动报告-*） |
| 失败自动通知 | ✅ | plan_failed 模板 + notify_sync 调用断言 |
| 独立 session 后台执行 | ✅ | _run_failure_auto_chain_in_new_session（SessionLocal） |

### P2 项（20）
| ID | 结果 | 说明 |
|----|------|------|
| P2-01 | ✅ | 计划单一「执行」+ 范围弹窗（全部/仅API）；手动录入默认「请选择」必选 |
| P2-02 | ✅ | CommandDialog 无 forceMount，关闭即卸载（代码核验，生产复验项） |
| P2-04 | ✅ | 安全弹窗项目名取 currentProject.name（ApiCaseTab/DebugTab） |
| P2-07 | ✅ | 音视频流地址 zod URL 校验 + 错误提示；删除/编辑已有 |
| P2-08 | ✅ | perftest/operations-release 未启用/未配置提示已有；组织页为真实页面 |
| P2-09 | ✅ | DELETE /apitest/tasks/{id} + 前端删除/重跑失败入口（取消已有） |
| P2-10 | ✅ | 服务级「生成全部用例」（batch-generate） |
| P2-11 | ✅ | task_worker 改用 claim_next_task 原子认领，双 Worker 竞态消除 |
| P2-12 | ✅ | requirement_service 懒加载收敛（test_case_service 已懒加载） |
| P2-13 | ✅ | 缺口按业务域排序（numeric）+ 域筛选 |
| P2-14 | ✅ | case 映射回写（Batch 154）+ Trace 列展示 trace_id + 详情 Trace 下载 |
| P2-15 | ✅ | job_type=report 定时生成报告 + report_generated 通知 + UI 类型选择 |
| P2-16 | ✅ | 页面更名「专项测试」+ 描述含专项测量（导航种子名未改） |
| P2-17 | ✅ | 发布包空态构建引导已有（BundleDetail） |
| P2-18 | ✅ | disabled_reason 迁移+停用必填+列表展示+启用清空 |
| P2-19 | ✅ | 行操作按钮文字/aria-label 已具备（special 已补） |
| P2-20 | ✅ | 用例标题可点击打开编辑抽屉 |
| P2-21 | ✅ | 计划状态筛选新增「全部」默认项 |
| P2-22 | ✅ | 集成页无 Test5 硬编码（provider 表单化 jira/tapd） |
| P2-23 | ✅ | 知识中心 12 tab visited forceMount 状态保留 |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | 执行双轨（test_execution ↔ api_execution_task）模型统一未做，仅完成认领式 worker 消除竞态；双向关联可经 case_id join | 代码 | 建议后续架构批次 |
| 2 | P3 | 导航菜单名「音视频专项」来自后端菜单种子，本次未改种子数据 | 代码 | 建议后续批次 |
| 3 | P3 | Command Palette 泄漏需生产环境 a11y 复验 | - | 待复验 |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 20h vs 实际约 6h | 0/0/0/3 | 2 | 迁移 ID 超长（33>32）触犯 revision 长度测试；前端测试 mock 未含 projects | 新迁移先查 revision 长度约束；改 auth store 后同步 mock |

**技能使用**: cameltv-bug-guard（迁移守卫/后台任务 session/React 副作用四律/Tabs 条件渲染）、cameltv-ui-conventions（弹窗/表单/无障碍）、cameltv-agent-team 流水线
