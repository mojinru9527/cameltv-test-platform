# Batch 151 — QA 报告（功能用例入计划 + 失败自动链路）

> **QA (🔍)** | Date: 2026-08-11 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 1 (C147-6 主链路) | 1 | 0 | 0 |

## 可执行门禁
| 门禁 | 命令 | 结果 |
|------|------|------|
| ruff F821 | `python -m ruff check app/ --select F821` | ✅ |
| 受影响 pytest | `pytest tests/test_batch151_auto_chain.py tests/test_testplan.py tests/test_report_aggregator.py` | ✅ 36 passed |
| alembic | heads 单头 + 临时库迁移 | ✅ 20260811_batch151_auto_defect |
| 前端 typecheck/build | `npm run typecheck` / `npm run build` | ✅ |
| 前端全量 vitest | `npx vitest run` | ✅ 113 files / 456 tests |
| 本地冒烟 | Playwright | 自动缺陷/报告 + 功能用例入计划 ✅ |

## 逐条件验证

### C147-6 功能用例入计划 + 执行→缺陷→报告→通知自动链路
**变更文件**: models/test_plan.py、alembic/versions/20260811_batch151_auto_defect.py、schemas/test_plan.py、services/test_plan_service.py、api/v1/test_plan.py、services/notify_service.py、AddCasesModal.tsx、PlanDrawer.tsx

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 功能用例加入计划 | ✅ | 后端 add_cases 支持任意类型；前端类型筛选（单测 + 冒烟 plan cases api+manual） |
| 开关字段贯通 | ✅ | create/update/list 均含 auto_defect_on_fail（pytest 2/2） |
| 自动转缺陷 | ✅ | 冒烟 [AI分诊]...execution_id=1；pytest defect_count≥1 |
| 自动生成报告 | ✅ | 冒烟 失败自动报告-*；pytest report_id 非空 |
| 自动通知 | ✅ | plan_failed 模板接入；service 调用（测试 patch 断言） |
| 开关关闭不写入 | ✅ | pytest 缺陷数不变 |
| UI 自动化↔用例映射回写 | ⏳ 未纳入 | 登记 C151-1 后续批次 |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 无 | - | - | - | - |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 5h vs 实际 4h | 0/0/0/0 | 2 | 后台任务真实 SessionLocal 污染测试；Radix Select jsdom 交互 | 测试先 patch 后台任务；Select 用 ref 读最新状态 |

**技能使用**: cameltv-bug-guard（后台任务隔离/迁移守卫）；playwright-skill（冒烟）
