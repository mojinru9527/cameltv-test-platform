# Batch 154 — QA 报告（四项收口）

> **QA (🔍)** | Date: 2026-08-11 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 4 (C147-8/C147-9/C151-1/C152-1) | 4 | 0 | 0 |

## 可执行门禁
| 门禁 | 命令 | 结果 |
|------|------|------|
| ruff F821 | `python -m ruff check app/ --select F821` | ✅ |
| 本批 pytest | `pytest tests/test_batch154_remaining.py` | ✅ 8/8 |
| 受影响 pytest | test_testcase/test_testplan/ui_test/wiki/knowledge 等 | ✅ 210 passed |
| alembic | heads 单头 + revision 长度 | ✅ 20260811_batch154_links |
| 前端 typecheck/build/vitest | `npm run typecheck` / `build` / `vitest` | ✅ 455 tests |
| env inventory | `pwsh scripts/env-inventory.ps1` | ✅ 运行正常（仅预期本地文件缺失提示） |

## 逐条件验证

### C147-8 数据集参数化注入 API 用例 UI
| 检查项 | 结果 | 说明 |
|--------|------|------|
| TestCase.dataset_id 贯通 | ✅ | create/update/out 均含（单测 roundtrip） |
| 执行兜底 | ✅ | 未显式传 dataset_id 时用用例默认 → batch_mode 生效 |
| UI | ✅ | CaseDrawer 接口数据 Tab 数据集选择；ApiCaseTab 执行工具栏数据集选择 |

### C147-9 知识图谱治理
| 检查项 | 结果 | 说明 |
|--------|------|------|
| missing_source 回填 | ✅ | backfill 端点 + 按用例标题/需求匹配（单测 updated≥1） |
| graph_evolve 报错修复 | ✅ | 根因 `func.count(...).where()` 非法 → 改 `select(count).where`；加固可选 db |
| 删除级联 | ✅ | 缺陷/需求/用例删除 → knowledge_source deprecated（单测） |

### C151-1 UI 自动化↔用例映射回写
| 检查项 | 结果 | 说明 |
|--------|------|------|
| UiTestJob.case_id + 列表 case_title | ✅ | create/list 单测 |
| 运行结果回写 | ✅ | done→pass 写入 last_run_status/last_response_json |
| 批量创建 | ✅ | POST /ui-tests/jobs/from-cases（单测 created=1） |
| UI | ✅ | 任务表单关联用例选择 + 列表列 |

### C152-1 孤儿文件 + env 统一入口
| 检查项 | 结果 | 说明 |
|--------|------|------|
| env 统一入口 | ✅ | docs/env-unified-guide.md（launcher/config-runtime 单一入口 + 5 份清单） |
| inventory 脚本 | ✅ | scripts/env-inventory.ps1 只读校验 |
| tracked 孤儿 | ✅ | 扫描未发现 .log/.bak/_tmp 等 tracked 孤儿；用户本地未跟踪文件未动 |

## 补充：Batch 151 迁移补录（流程缺陷修复）
- 发现：`20260811_batch151_auto_defect.py` 未随 PR #209 合入 main（模型/服务已上线，迁移缺失）。
- 处理：本批补录同 revision 文件（幂等守卫），并挂接 154 迁移；`alembic heads` 单头验证通过。
- 影响：部署 fresh DB 将正确创建 auto_defect_on_fail 列。

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P1（已修） | Batch 151 迁移文件缺失（历史合入遗漏） | alembic heads 单头 + 本批补录 | 已修复 |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 8h vs 实际 7h | 0/1/0/0 | 2 | 跨文件正则补丁/迁移合入校验缺失 | 迁移文件纳入 PR 文件清单核对；改 import 用整块替换 |

**技能使用**: cameltv-bug-guard（迁移守卫、懒加载防环、类型校验）；pwsh env-inventory
