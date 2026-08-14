# Batch 182 — Leader 判决：状态机统一 / ORM 收敛 / P3 打磨

> **mode: full** | 日期：2026-08-16 | 分支：`feature/batch-182-status-orm-p3-polish`

## 1. 判决：✅ APPROVED（待用户一次总确认后推送/PR/合入）

## 2. 抽检与复核

| 工件 | 抽检结果 |
|------|---------|
| PRD | mode:full 正确（重构+Schema）；非目标明确（双写物理删除/AiTask 词表/生产回填自动执行）；C 条件承接表完整 |
| Design | 统一词表 7 值 + 7 表映射一致；写/读站点清单与实际转换一致；open_api 双值兼容设计落实；响应键契约保留映射（统计/报告/趋势） |
| Dev | 迁移单头幂等可逆；canonical 兜底在 execute_case 层；守卫 api/v1 全量（TYPE_CHECKING 豁免合理）；前端共享映射 + 23 子组件纯移动 |
| QA | 后端 1502/0（+7 净增测试）；前端 479 vitest + typecheck + build 全绿；ruff/alembic 门禁绿；基线失败集核对（无新增） |

## 3. 关键风险核验

- **统计/报告口径**：stats 响应键（pass_/fail/skip/block/pending）为契约，转换仅动 DB 查询来源；`_batch_calc_stats`/`report_service`/`trace trend` 三处响应键映射均有专项断言。
- **CI 契约**：open_api 回写旧值继续接受（双值集合 + canonical 落库），通知判定兼容；未破坏外部 CI 脚本。
- **生产数据**：b182 迁移逐值映射 + 可降级；回填脚本 dry-run 默认。
- **前端行为**：页面拆分纯移动（vitest 479 全过 + build 绿）；状态展示新旧双值兼容。

## 4. 遗留条件（已登记 C-CONDITIONS.md）

| ID | 内容 | 优先级 |
|----|------|--------|
| C182-1 | 执行记录双写保留（双 UI 契约），单一事实源改造需 UI 合并决策后另立专项 | P2 |
| C182-2 | 域命名回填脚本生产 dry-run 核对后人工执行 --apply | P3 |

## 5. 知识审计

- 本批沉淀：统一执行状态词表与 canonical 规范（`app/core/execution_status.py`）、前端共享映射（`utils/executionStatus.ts`）、域命名分组规范（`utils/domainNaming.ts`）——已入库为代码级约定；backend/CLAUDE.md 状态词表小节随 PR 更新。
- 与既有 KB 矛盾核对：batch-175 统计口径（用例级 TestExecution）不受影响；batch-181 ADR-0019 约定继续适用。

## 6. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 子代理大任务中断率高（4/6） | 拆分更小文件粒度 + 主代理接管机制；本批接管后全部完成 | QA 复盘卡 |
| 词表变更未同步测试断言 | 全量 pytest 作为断言扫描器（13 文件批量更新） | 后续词表变更批次注意 |
| ORM 守卫盲区（`from app.models.submodule`） | 正则收紧 + TYPE_CHECKING 豁免 | 守卫测试 |
