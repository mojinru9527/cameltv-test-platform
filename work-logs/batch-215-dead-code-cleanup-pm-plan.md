# Batch 215 — PM Plan
> **PM (🟨)** | Date: 2026-09-03 | Executor: Codex | 完整批次

## 规格摘要
**原始需求**: B5 死代码清理（路线图 §2 + ABC 白名单 §3）。删除无引用页面/组件/文档、V1 工具陈旧宣称根清理、根目录 `_tmp_*`/重复文档。
**目标时间**: M0 收尾（B1–B5 合入）。

## 开发任务

### [ ] Task 1: 删除 /testplan 独立页（前端页面簇）
**描述**: 删除 `test-platform-v2/frontend/src/pages/testplan/` 整个目录（入口已在 batch-212 下架，路由仅 `<Navigate to="/testcase">`）。含该页面自有测试文件。更新 `src/__tests__/touchTargetGuard.test.ts` 移除 `src/pages/testplan/index.tsx` 条目（否则触控守护读文件失败）。
**验收标准**: `rg 'pages/testplan|@/pages/testplan' src`（非测试）零命中；`npm run typecheck && npm test` 绿；删除项可回滚。
**涉及文件**:
- `frontend/src/pages/testplan/index.tsx` — 删除
- `frontend/src/pages/testplan/PlanDetail.tsx` — 删除
- `frontend/src/pages/testplan/PlanDrawer.tsx` — 删除
- `frontend/src/pages/testplan/AddCasesModal.tsx` — 删除
- `frontend/src/pages/testplan/executionStatus.test.ts` — 删除（页面自测）
- `frontend/src/pages/testplan/AddCasesModal.test.tsx` — 删除（页面自测）
- `frontend/src/pages/testplan/__tests__/searchCommit.test.tsx` — 删除（页面自测）
- `frontend/src/__tests__/touchTargetGuard.test.ts` — 更新（移除 testplan 条目）
**参考**: router/index.tsx:21,245-246；batch-212 qa-report C7

### [ ] Task 2: 删除 Playground 独立页
**描述**: 删除 `frontend/src/pages/testcase/playground/index.tsx`（Playground Tab 已在 batch-212 下架，`?tab=playground` 回落列表视图）。保留 `src/api/playground.ts`（M1 场景执行复用）、保留后端 `/api/v1/playground/*`。
**验收标准**: `rg 'PlaygroundPanel|pages/testcase/playground' src` 零命中（除路由注释）；build/test 绿。
**涉及文件**:
- `frontend/src/pages/testcase/playground/index.tsx` — 删除
- `frontend/src/pages/testcase/index.tsx` — 校验无 PlaygroundPanel import（若有则清理）
**参考**: router/index.tsx:262-263；testcase/index.tsx:45,376；batch-212 qa-report C4

### [ ] Task 3: 删除无引用前端组件/Hook（引用审计零引用 + 无测试耦合）
**描述**: 删除前端 import 图不可达（entry=main.tsx）且无测试引用/文档非代码引用共存的 13 个文件。保留有测试耦合或后续复用意图的组件（见非目标）。
**验收标准**: `npm run typecheck && npm test` 绿；对每个删除文件 rg 复核零代码引用。
**涉及文件**（全部删除）:
- `frontend/src/components/ui/accordion.tsx`
- `frontend/src/components/ui/breadcrumb.tsx`
- `frontend/src/components/ui/calendar.tsx`
- `frontend/src/components/ui/combobox.tsx`
- `frontend/src/components/ui/progress.tsx`
- `frontend/src/components/ui/toggle-group.tsx`
- `frontend/src/components/ui/toggle.tsx`
- `frontend/src/components/ListToolbar.tsx`
- `frontend/src/components/trust/VerificationLevelBadge.tsx`
- `frontend/src/hooks/useA11y.ts`
- `frontend/src/hooks/usePaginatedList.ts`
- `frontend/src/pages/apitest/components/ApiDebugPanel.tsx`
- `frontend/src/pages/apitest/components/EnvironmentBar.tsx`
- `frontend/src/pages/missions/StagePlaceholder.tsx`
- `frontend/src/pages/runtime/components/PolicyDecisionDrawer.tsx`
- `frontend/src/pages/runtime/components/RetryHistory.tsx`
- `frontend/src/pages/requirement/ExtractionModal.tsx`
**保留（非删除）**: `api/playground.ts`（M1 复用）、`components/foolproof/*`（B4 待接线）、`components/TriagePanel.tsx`（后续滚动）、`knowledge/components/SphereTab.tsx`/`WikiLintPanel.tsx`/`release-bundles/components/*`（有测试耦合）、`ui-concepts/*`、`theme-lab/main.tsx`（替代入口）

### [ ] Task 4: special/perftest 代码冻结 + V1 工具文档清理
**描述**: 验证 special/perftest 在代码/菜单/README 无「入口/宣称」残留（B2 已完成宣称下架，本批冻结代码即确认无专属前端入口）。更新 `COMMANDS.md` §5 将已废弃 V1 CLI 工具（mock/api_diff/api_tester/av_checker/data_factory/env_check/load_tester/log_aggregator/project_init/report_dashboard/traffic_monitor）段落标注为「已废弃移除」或删除，避免与现网不符。
**验收标准**: `rg 'menu:special|menu:perftest|音视频专项|性能监控'` 在代码/README 无「可用入口」残留；COMMANDS.md §5 与 V1 工具存在状态一致。
**涉及文件**:
- `test-platform-v2/README.md` — 校验（已在 B2 清理，本批复核）
- `COMMANDS.md` — 更新 §5 标注/废弃
- `test-platform-v2/backend/app/services/menu_service.py` — 校验 `menu:special`/`menu:perftest` 仅存在于 `HIDDEN_MENU_CODES`（冻结=隐藏，不再对外宣称）

### [ ] Task 5: 根目录 `_tmp_*`/重复文档/临时文件清理
**描述**: 在根 `.gitignore` 增加 `_tmp_*`、`_verify_*.png`、`_review_tools/`、`.agent-teams/`、`.dsh-vision-router/`、`browser-screenshots/` 等忽略规则，兜底临时物不再污染 `git status`；删除根目录 `.pr-body-batch20.md`、`.pr-body-batch22.md`（临时 PR 正文残留）；历史根文档采用「归档 + 引用更新」处理，避免破坏 repo-boundaries.json/CLAUDE.md/repo-map.md 交叉引用。
**验收标准**: 主 checkout `git status` 不再出现 `_tmp_*`；`git check-ignore _tmp_*.py` 命中；引用文档路径更新后 build/test/校验不破。
**涉及文件**:
- `.gitignore` — 新增忽略规则
- `.pr-body-batch20.md` — 删除
- `.pr-body-batch22.md` — 删除
- 根历史文档（`测试平台-前后端分离重构方案.md`/`CamelTv-测试自动化平台-建设方案.md`/`知识库.md`/`知识中心-用户使用手册.md`/`test-测试平台设计方案.md`）— 归档至 `docs/archive/` 并更新引用

## 质量要求
- [x] 响应式（Desktop + Tablet） — 本批无 UI 变更，不适用
- [x] OpenAPI 同步 — 无 API 变更
- [ ] 单元测试覆盖 — 前端删除项自测文件一并删除；后端受影响测试回归
- [x] 无障碍（ARIA/键盘） — 无新增组件
- [ ] 无 console 报错/告警 — 删除项无 console 遗留
