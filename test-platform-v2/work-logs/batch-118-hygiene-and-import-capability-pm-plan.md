# Batch 118 — PM Plan（追踪器卫生清理 + C109-1 生产收尾 + C102-3/4 需求导入能力 + C117-1）

> **PM (🟨)** | Date: 2026-08-07

## 规格摘要

**原始需求**: PRD Batch 118 — ①卫生审计批量关闭（C103-1~4/6、C102-2、C102-5、C110-3、C103-7 等）；②C109-1 生产收尾；③C102-3 模块树直建；④C102-4 差异标注；⑤C117-1 覆盖缺口前端展示。
**目标时间**: 1–2 天（含 QA 与合入）。

## 开发任务

### [ ] Task 1: 卫生审计证据核对（C103-1~4/6、C102-2、C102-5、C103-7、C110-3、C101-1、C113-1/C114-1/2）
**描述**: 逐项以「production 实测 + 代码锚点 + 既有 evidence JSON」核对完成状态，输出 `evidence/batch-118/hygiene-audit-summary.json`。
**验收标准**:
- 每项含证据（API 实测输出 / 文件:行 / evidence 路径）
- C102-2：`GET /knowledge/search/health` vector_functional=true 实测记录
- C110-3：TaskTab 批量执行 UI 存在 + C111-2 170/170 evidence 引用
- C103-6/C102-5：coverage_report 落地（C116-3 已关）+ C103-6 一并关闭
**涉及文件**: `test-platform-v2/work-logs/evidence/batch-118/hygiene-audit-summary.json`、`C-CONDITIONS.md`

### [ ] Task 2: C-CONDITIONS.md 卫生关闭 + 一致性校验
**描述**: 将核对通过项从 Open 移入 Closed 表（Batch 118 节），带证据；运行 `audit-cconditions.ps1 -RequireLatestBatch` 0 硬错。
**验收标准**: `audit-cconditions.ps1` 0 hard error；关闭项均有证据列。
**涉及文件**: `C-CONDITIONS.md`

### [ ] Task 3: C109-1 生产收尾验证
**描述**: ①确认 SEED_DEMO_USERS=false 生效（Railway 变量或行为验证：部署后 sys_user 无演示账号重建，已实测 3 用户/0 演示）；②Playwright 邀请链接端到端复测（https、页面 200、注册自动入项目/组织）。
**验收标准**: 复测截图+日志证据 `evidence/batch-118/c1091-invite-link-summary.json`；C109-1 关闭。
**涉及文件**: 证据 JSON + `C-CONDITIONS.md`
**参考**: PRD §4 US-2

### [ ] Task 4: C102-3 需求模块树直建（后端）
**描述**: `requirement_modules.py` 增加无 evidence_job_id 的直建端点（从需求文档内容构建模块树）；`ModuleExtractRequest.evidence_job_id` 可选，两条路径并存。
**验收标准**: 直建端点单测（直建路径 + 证据包路径回归）；OpenAPI schema 同步。
**涉及文件**: `backend/app/api/v1/requirement_modules.py`、`backend/app/services/knowledge/module_extractor.py`（如需要）、`backend/tests/test_requirement_modules.py`
**参考**: PRD §4 US-3

### [ ] Task 5: C102-4 生产页面 vs 原型差异标注
**描述**: 新增差异标注端点（复用 diff_json/compare_iterations 基建），输出「新增模块/变更页」差异；前端最小展示（列表+标签）。
**验收标准**: 后端单测覆盖差异计算；前端组件渲染 + vitest。
**涉及文件**: `backend/app/api/v1/requirement.py`（或 knowledge）、`frontend/src/pages/requirement/**`、对应 tests
**参考**: PRD §4 US-4

### [ ] Task 6: C117-1 覆盖缺口报告前端展示
**描述**: `AiResultModal` 增加「覆盖矩阵/缺口」Tab，消费 coverage_report JSON。
**验收标准**: typecheck/build + vitest 新增用例通过。
**涉及文件**: `frontend/src/pages/requirement/**`（AiResultModal 所在）、`frontend/src/**/__tests__/**`
**参考**: PRD §4 US-5

### [ ] Task 7: QA 硬门禁 + 报告 + Leader + 合入
**描述**: 前端 `npm ci && npm run typecheck && npm run build` + vitest；后端 app 导入、`ruff check app --select F821`、Alembic 单头、受影响 pytest；QA 报告 + Leader 判决 + 一次总确认 → push → Draft PR → checks → 合入。
**验收标准**: 全部门禁退出码 0；audit-ai-pr -RequireSuccessfulChecks 通过。
**涉及文件**: `test-platform-v2/work-logs/batch-118-*-qa-report.md`、`*-leader-verdict.md`

## 质量要求

- [x] 响应式（新增 UI 最小化，沿用现有组件）
- [x] OpenAPI 同步（后端新端点）
- [x] 单元测试覆盖（Task 4/5/6）
- [x] 无 console 报错/告警
- [x] C 条件更新后 `audit-cconditions` 0 硬错
- [x] `scan-common-bugs.ps1` HARD=0（提交前）
