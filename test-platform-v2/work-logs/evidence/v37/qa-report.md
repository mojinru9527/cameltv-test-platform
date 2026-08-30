# V3.7 QA Report — Impact Analysis + Smart Regression

> 分支：`feature/aitde-v37-impact-smart-regression`（based on `origin/main` @ `dae54ace`）
> 执行器：DeepSeek Harness（`DeepSeek_Harness`，direct workflow）
> 计划：`docs/aitde/versions/V3.7_Detailed_Development_Implementation_Plan.md`
> 交付粒度：一个分支一副 PR 合并到 main（对齐 V3.6 #366 先例）

## 一、V3.6 合并确认

- `origin/main` 已包含 `dae54ace` **「feat(aitde-v36): Production Evidence & Real-World Data Template (V36-001..V36-014) (#366)」**
- `origin/feature/aitde-v36-production-evidence` 已在合并后随 `--prune` 删除
- 结论：**V3.6 已合并**，V3.7 从最新 main 切出（前置条件满足）

## 二、交付内容（V37-001..014）

### 后端（`test-platform-v2/backend`）
- `app/modules/aitde/smart_regression/models.py` — `lineage_edges` / `change_sets` / `change_items` / `impact_analysis_runs` / `impact_results` / `regression_selections` / `regression_selection_items`
- `app/modules/aitde/smart_regression/repository.py` — 薄数据访问层（无 ORM 外泄）
- `app/modules/aitde/smart_regression/diff.py` — 6 个确定性 Diff Provider（Requirement/OpenAPI/DB_Schema/UI_Discovery/Environment/HistoricalRisk）
- `app/modules/aitde/smart_regression/service.py` — LineageService/LineageBackfillService/ChangeSetService/ImpactAnalyzer/ImpactExplanationService/RegressionSelector/CoverageGuard/SmartRegressionCampaignFactory
- `app/modules/aitde/smart_regression/schemas.py` — Pydantic 请求模型
- `app/modules/aitde/common/enums.py` — 新增 V37 枚举（ChangeSetType/ChangeItemKind/LineageNodeType/LineageEdgeType/RiskHint/ImpactRunStatus/ImpactDecision/SelectionType/SelectionDecision）
- `app/api/v2/smart_regression.py` — 13 个 `/api/v2` 端点（检测/风险/详情/Impact/解释/选择/Guard/Campaign/Lineage/Backfill/AddEdge）
- `app/api/v2/router.py` — 挂载 smart_regression 路由
- `alembic/versions/20260901_aitde_v37_smart_regression.py` — 带存在性守卫的幂等迁移（down_revision=v36_prodev）
- `app/modules/aitde/intelligence/prompts/impact_semantic_assist_v1.txt` — AI 语义辅助 prompt（assist-only 硬规则）

### 前端（`test-platform-v2/frontend`）
- `src/api/smartRegression.ts` — API 客户端 + 类型 + 标签映射
- `src/pages/missions/changes.tsx` — ChangeSet 检测与差异查看
- `src/pages/missions/impact.tsx` — 影响分析 → 回归选择 → Guard → Campaign
- `src/pages/missions/trace.tsx` — Lineage 视图 + 回填
- `src/pages/regression-selections/index.tsx` — 回归选择详情（include/exclude/fallback）
- `src/router/index.tsx` + `src/pages/missions/MissionLayout.tsx` — 路由与导航登记

### 测试
- `backend/tests/aitde/v37/` — conftest + test_diff_providers / test_lineage / test_impact_selector（18 用例）

## 三、自检结果（AGENTS.md §3）

| 检查 | 命令 | 结果 |
|------|------|------|
| 后端硬门禁 F821 | `ruff check app/ --select F821` | ✅ All checks passed |
| 后端受影响模块 | `pytest tests/aitde/v37` | ✅ 18 passed |
| 相邻域回归（v36+v37） | `pytest tests/aitde/v36 tests/aitde/v37` | ✅ 41 passed |
| 相邻域回归（v35，非 temporal） | `pytest tests/aitde/v35/test_continuous.py test_gate_wiring.py test_orchestration.py` | ✅ 24 passed |
| 前端类型检查 | `npm run typecheck` | ✅ |
| 前端 lint | `npm run lint`（--max-warnings=0） | ✅ |
| 前端 build | `npm run build` | ✅ built in ~10s |
| ruff（新文件全规则） | `ruff check app/modules/aitde/smart_regression ...` | ✅ All checks passed |
| 调试残留 / 密钥 | 人工排查 | ✅ 无 |

## 四、已知限制（本分支已知）

1. `test-platform-v2/backend/tests/aitde/v35/test_api_driver.py` 依赖 `temporalio`，本地 dev venv 未安装，无法本地执行（CI 测试环境会安装；与本分支无关的既有环境差异）。
2. 本地无法执行依赖 `app.main` 的整库后端测试（root conftest 引入 `app.main` ∋ temporalio），故后端全量回归在 CI 完成。
3. DB 表 diff 的 `DATA_ENTITY` 与 OpenAPI 的 `API_ENDPOINT` 变更项需 baseline/current 以「节点 id 作为 key」传入方可建立 Lineage；否则落入「未知变化 → CoverageGuard fallback」的保守路径（符合 plan §5 的 UNKNOWN_CHANGE 策略）。

## 五、任务映射

- V37-001 Lineage Edge Schema/Service ✅（dangling detect）
- V37-002 Backfill ✅（幂等）
- V37-003 Requirement Diff ✅（baseline/current hash）
- V37-004 OpenAPI Diff ✅（required 变更 detect）
- V37-005 DB Schema Diff ✅（enum/column detect）
- V37-006 UI Discovery Diff ✅（cosmetic 低风险）
- V37-007 Historical Risk ✅（severity weight）
- V37-008 Impact Analyzer ✅（path include/确定性）
- V37-009 Regression Selector ✅（P0 永不被 AI 排除）
- V37-010 Coverage Guard ✅（unknown/空选择 fallback）
- V37-011 Smart Campaign Factory ✅（selection immutable）
- V37-012 Change/Impact UI ✅
- V37-013 Regression Preview UI ✅
- V37-014 Lineage UI ✅（cross project isolation 由 API project_id 限定）
