# Batch 89 — PM Plan（C55-5-P2 / C81-1 / C64-2 / C21-P1-2）

> **PM (🟨)** | Date: 2026-08-05

## 规格摘要

**原始需求**: C55-5-P2 tablet/mobile 响应式回归；C81-1 WARN 周审计；C64-2 误提交文件清理；C21-P1-2 三服务单测证据关闭（PRD §1–§2）。
**目标时间**: 2 个工作日（2026-08-05 → 08-06）；切片 ≤60 分钟。
**批次模式**: full（PRD §0）。

## 开发任务

### Slice 0: 环境就绪 + C21-P1-2 证据（轻量）

**描述**: 启动 batch-89 后端（8046，独立 SQLite seed）与前端（5216）；执行三服务单测 `test_failure_analyzer.py / test_report_aggregator.py / test_task_worker.py / test_api_task_worker.py`，记录退出码；确认引入 commit `a3608b8`。
**验收标准**:
- 三服务单测 103/103 通过（退出码 0）
- C21-P1-2 关闭证据文本（commit + 运行日志）落盘
**涉及文件**: `test-platform-v2/backend/.env`（gitignore）、`test-platform-v2/work-logs/evidence/batch-89/c21-p1-2-closure.md`

### Slice 1: C64-2 误提交文件清理（低风险，先做）

**描述**: 确认根目录两个 `pective pipeline — ...` 文件（第二个含 `\uF022` 尾字符）无引用后删除；`repo-boundaries.json` shared 段移除对应两行；运行 `validate_repo_boundaries.py --check`。
**验收标准**:
- 文件删除后 `git status` 干净（仅预期删除）
- `repo-boundaries.json` 不再含 `pective` 路径
- `validate_repo_boundaries.py --check` 退出码 0
**涉及文件**: 根目录 2 个误提交文件、`repo-boundaries.json`、`scripts/repo/validate_repo_boundaries.py`（只读验证）

### Slice 2: C81-1 WARN 周审计

**描述**: 运行 `scripts/git/run-warn-audit.ps1 -BatchLabel "batch-89"`，对比 `docs/agent-team/warn-baseline.json`；HARD 必须 0、无新增类别；趋势表追加。
**验收标准**:
- AUDIT_RESULT=OK（WARN 209 基线持平或减少，新增类别 0）
- `warn-inventory.md` 趋势表含 2026-08-05 行
**涉及文件**: `docs/agent-team/warn-inventory.md`、`docs/agent-team/warn-baseline.json`（若刷新需 Leader 复核）

### Slice 3: C55-5-P2 响应式回归（核心）

**描述**: 新增 `e2e/batch89-responsive.spec.ts`：登录后以 `768×1024` 与 `390×844` 视口打开登录/工作台/用例/计划/报告/缺陷/定时/知识 8 个页面，断言无水平溢出（scrollWidth<=innerWidth）、主操作元素可点、导航/弹窗可开合；截图存证据目录。发现的缺陷按 P0–P3 修复。
**验收标准**:
- 两个视口 × 8 页面全通过或缺陷已修复后通过
- 截图证据（≥8 张/视口）
- 修复项有对应 vitest/e2e 回归
**涉及文件**: `test-platform-v2/frontend/e2e/batch89-responsive.spec.ts`、`test-platform-v2/frontend/src/**`（仅缺陷修复时）

### Slice 4: QA 硬门禁 + 全量回归

**描述**: ruff F821、后端全量 pytest、前端 typecheck/build/vitest、scan-common-bugs、audit-cconditions -RequireLatestBatch；记录退出码。
**验收标准**: 全绿，无新增失败。

### Slice 5: Leader 判决 + C 条件同步 + 交付

**描述**: C55-5-P2/C81-1/C64-2/C21-P1-2 关闭（含证据）；batch-88 看板合入状态回填；一次总确认 → push → Draft PR → checks → 合入。
**验收标准**: 工件齐备、audit 0 硬错、总确认后交付。

## 质量要求

- [x] 响应式 — 本批核心（768×1024 / 390×844）
- [x] OpenAPI 同步 — 无新端点，不适用
- [x] 单元测试 — C21-P1-2 103/103 + 响应式 e2e
- [x] 无 console 报错 — Playwright 断言 console error 为 0（新增断言）
- [x] 敏感信息 — 不涉及新凭据
