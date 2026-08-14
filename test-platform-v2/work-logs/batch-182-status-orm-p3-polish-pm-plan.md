# Batch 182 — PM 计划：状态机统一 / ORM 收敛 / P3 打磨

> 配套 PRD/Design：`batch-182-status-orm-p3-polish-{prd-summary,design-spec}.md`

## 任务清单

| # | 任务 | 验收标准 | 执行 |
|---|------|---------|------|
| T0 | 工件 PRD/PM/Design/看板 | 四件落库、mode:full | 主代理 |
| T1 | 迁移 `b182_status_unify`（7 表映射） | 单头/幂等/降级可逆；存量值断言 | 主代理 |
| T2 | `canonical_exec_status` + 后端写/读站点转换（12 文件） | test_status_unify 全绿；统计/追溯口径不变 | 主代理 |
| T3 | open_api 回写双值兼容 + schema 扩展 | 旧值/新值回写均落库新词表 | 主代理 |
| T4 | 前端 `executionStatus.ts` 共享映射 + 消费方替换（TaskTab/plan/uitest/workbench/trace/report） | typecheck/build/vitest 绿 | 主代理 |
| T5 | C181-1 路由 ORM 收敛（~26 文件） | api/v1 全量守卫通过（模型 import/select/db.query=0，SessionLocal 仅豁免模式） | 子代理×3 |
| T6 | P3-03 追溯轴标签统一 | trace 页全中文标签；vitest | 主代理 |
| T7 | P3-04 域命名：规范 + 前端分组 + backfill 脚本（dry-run） | 前端按前缀分组；脚本 dry-run 报告映射 | 子代理 |
| T8 | P3-09 页面拆分（6 页） | 各文件 <800 行；typecheck/build/vitest 绿 | 子代理×2 |
| T9 | 全量回归 + 门禁 | 后端 pytest 无新增失败；前端全量；ruff F821；alembic 单头；scan-common-bugs | 主代理 |
| T10 | QA/Leader 工件 + C 条件关闭（C181-1/2/3）+ C182-1 登记 | 工件齐全；audit 通过 | 主代理 |
| T11 | 总确认 → push → Draft PR → audit → 合入 | required checks 全绿 | 主代理 |

## 风险提示

- T2 触及统计/报告口径：转换后必须跑 statistics/trace/report 相关全部测试并比对基线失败集。
- T3 open_api 契约：只扩不缩（旧值必须继续接受）。
- T5/T8 子代理产出必须经全量回归 + 守卫验证，主代理统一集成。
