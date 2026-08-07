# Batch 120 — PM Plan（异步多 worker + 采集对接 + 缺口前端 + 外部探测）

> **PM (🟨)** | Date: 2026-08-07

## 规格摘要

**原始需求**: PRD Batch 120 — C117-2 DB 队列多 worker；C119-1 差异面板对接采集；C119-2 缺口前端；外部项探测。
**目标时间**: 1–2 天。

## 开发任务

### [ ] Task 1: C117-2 ai_task 表 + 迁移 + 服务改造
**描述**: 新增 AiTask 模型与 Alembic 迁移；ai_tasks.py 改 DB 队列（submit→pending，worker 原子认领，完成写回 result/error）。
**验收标准**: 单测覆盖认领互斥/状态流转/失败写回；alembic 单头；app 导入。
**涉及文件**: `backend/app/models/ai_task.py`、`backend/alembic/versions/*`、`backend/app/services/ai_tasks.py`、`backend/tests/test_ai_tasks.py`

### [ ] Task 2: C119-1 差异面板加载采集任务
**描述**: ProductionDiffPanel 增加采集任务 ID 输入 → GET /ui-tests/capture/{id} → pages→label → 生成差异。
**验收标准**: vitest 覆盖加载成功/失败；typecheck/build。
**涉及文件**: `frontend/src/api/requirement.ts`、`frontend/src/pages/requirement/components/ProductionDiffPanel.tsx`、`__tests__`

### [ ] Task 3: C119-2 InteractionGapPanel 前端
**描述**: 需求页新增交互覆盖缺口面板：内置模块级代表边 → POST /interaction-coverage/gaps → 覆盖率 + 缺口列表。
**验收标准**: vitest 3 态；typecheck/build。
**涉及文件**: `frontend/src/api/requirement.ts`、`frontend/src/pages/requirement/components/InteractionGapPanel.tsx`、`index.tsx`、`__tests__`

### [ ] Task 4: 外部探测（Test5/iOS）
**描述**: 探测 Test5 网关 health + konfi/admin 登录；tidevice/solox 探测 iOS 设备；更新 C-CONDITIONS.md 解除条件。
**验收标准**: 探测证据 JSON + 追踪器更新（可解锁则推进，否则 Deferred 更新条件）。
**涉及文件**: `evidence/batch-120/external-probe-summary.json`、`C-CONDITIONS.md`

### [ ] Task 5: QA 硬门禁 + 报告 + Leader + 合入
**描述**: 后端 ruff/alembic/pytest；前端 typecheck/build/vitest；audit-cconditions；QA/Leader + 一次总确认 → push → PR → checks → 合入。
**验收标准**: 全部门禁 0；audit-ai-pr -RequireSuccessfulChecks。

## 质量要求

- [x] 迁移离线校验 + alembic 单头
- [x] 认领互斥单测（两个 worker 不重复执行）
- [x] 前端四态 + 中文标签
- [x] scan-common-bugs HARD=0
- [x] audit-cconditions 0 硬错
