# Batch 119 — PM Plan（收尾与工具链清理）

> **PM (🟨)** | Date: 2026-08-07

## 规格摘要

**原始需求**: PRD Batch 119 — C118-1 历史 HARD 修复；C104-3/C105-3 api.d.ts 锁定重生成；C105-4 停用组织 UI 走查；C114-1 拓扑缺口提示；C102-4 前端差异面板。
**目标时间**: 1–2 天（含 QA 与合入）。

## 开发任务

### [ ] Task 1: C118-1 修复 3 处 except:pass
**描述**: `ai_service.py:324`、`xhr_capture_service.py:74/95` 静默吞异常改为日志 + 合理降级。
**验收标准**: scan-common-bugs HARD=0；相关单测通过。
**涉及文件**: `backend/app/services/ai_service.py`、`backend/app/services/xhr_capture_service.py`、对应 tests

### [ ] Task 2: C104-3/C105-3 api.d.ts 锁定重生成
**描述**: package.json 锁定 openapi-typescript 精确版本；重新生成 api.d.ts；记录漂移根因（工具版本差异）。
**验收标准**: typecheck/build 通过；漂移说明写入工件。
**涉及文件**: `frontend/package.json`、`frontend/src/types/api.d.ts`、`frontend/package-lock.json`

### [ ] Task 3: C105-4 停用组织 UI 走查
**描述**: Playwright 走查「停用组织后成员入口提示」+ 组织项目联动，截图证据。
**验收标准**: `evidence/batch-119/c1054-*.png` + 走查小结 JSON。
**涉及文件**: 证据目录

### [ ] Task 4: C114-1 交互拓扑缺口提示（后端）
**描述**: 新服务输入拓扑边 + 交互用例，输出未覆盖边清单 + 覆盖率；端点 + 单测。
**验收标准**: 单测覆盖（缺口径/全覆盖/部分覆盖）；OpenAPI 同步。
**涉及文件**: `backend/app/services/.../interaction_coverage_service.py`、路由、tests

### [ ] Task 5: C102-4 前端差异面板
**描述**: requirement 页新增 ProductionDiffPanel（调 production-diff 端点），new/matched/missing 列表 + 徽标。
**验收标准**: vitest + typecheck/build。
**涉及文件**: `frontend/src/pages/requirement/components/ProductionDiffPanel.tsx`、`index.tsx`、`__tests__`

### [ ] Task 6: QA 硬门禁 + 报告 + Leader + 合入
**描述**: 后端 ruff/app 导入/Alembic/pytest；前端 typecheck/build/vitest；audit-cconditions；QA 报告 + Leader 判决 + 一次总确认 → push → PR → checks → 合入。
**验收标准**: 全部门禁退出码 0；audit-ai-pr -RequireSuccessfulChecks 通过。

## 质量要求

- [x] 后端新端点 OpenAPI 同步 + 单测
- [x] 前端无 console 报错；差异面板四态
- [x] scan-common-bugs HARD=0
- [x] audit-cconditions 0 硬错
- [x] api.d.ts 漂移根因记录
