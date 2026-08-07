# Batch 121 — PM Plan（全量拓扑入库 + 多 worker 验证）

> **PM (🟨)** | Date: 2026-08-08

## 规格摘要

**原始需求**: PRD Batch 121 — C120-1 全量拓扑入库与缺口计算；C120-2 多会话竞态测试与生产验证；追踪器补登记。
**目标时间**: 1 天。

## 开发任务

### [ ] Task 1: C120-1/2 追踪器补登记
**描述**: C-CONDITIONS.md Open 表补 C120-1/C120-2 行（batch-120 来源）。
**验收标准**: audit-cconditions 0 硬错；两条件可追踪。
**涉及文件**: `C-CONDITIONS.md`

### [ ] Task 2: C120-1 interaction_edge 表 + 迁移 + 模型
**描述**: 新表（project_id/from_module/entry/to/evidence）+ Alembic 幂等迁移 + 模型注册。
**验收标准**: alembic 单头；迁移幂等。
**涉及文件**: `backend/app/models/interaction_edge.py`、`alembic/versions/*`、`models/__init__.py`

### [ ] Task 3: C120-1 导入 + 端点
**描述**: 导入脚本（3172 边 evidence JSON→表）；`GET /interaction-coverage/topology`；gaps 端点无 edges 时用 DB 全量。
**验收标准**: 导入后 count=3172；端点单测。
**涉及文件**: `backend/app/services/interaction_coverage_service.py`、`api/v1/interaction_coverage.py`、`scripts/` 或种子、tests

### [ ] Task 4: C120-1 前端全量模式
**描述**: InteractionGapPanel 默认调全量 topology+gaps，去掉内置 8 条。
**验收标准**: vitest 更新；typecheck/build。
**涉及文件**: `frontend/src/api/requirement.ts`、`components/InteractionGapPanel.tsx`、`__tests__`

### [ ] Task 5: C120-2 多会话竞态测试 + 生产验证
**描述**: 文件型 SQLite 双会话认领测试；部署后提交异步任务轮询 done；登记 Railway 实例数。
**验收标准**: 竞态单测通过；生产验证证据 JSON。
**涉及文件**: `backend/tests/test_ai_tasks.py`（或新测试）、`evidence/batch-121/c1202-prod-verify.json`

### [ ] Task 6: QA 硬门禁 + 报告 + Leader + 合入
**描述**: 全部门禁 + QA/Leader + 一次总确认 → push → PR → checks → 合入。
**验收标准**: 0 硬错；audit-ai-pr -RequireSuccessfulChecks。

## 质量要求

- [x] 迁移离线校验 + alembic 单头
- [x] 竞态测试（双会话不重复认领）
- [x] 前端四态 + 中文
- [x] scan-common-bugs HARD=0
- [x] audit-cconditions 0 硬错
