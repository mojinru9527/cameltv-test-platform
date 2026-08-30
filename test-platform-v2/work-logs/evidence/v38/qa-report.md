# V3.8 QA Report — AI QA Closed Loop

> 分支：`feature/aitde-v38-ai-qa-closed-loop`（based on `origin/main` @ `27ce1a51`）
> 执行器：DeepSeek Harness（`DeepSeek_Harness`，direct workflow）
> 计划：`docs/aitde/versions/V3.8_Detailed_Development_Implementation_Plan.md`
> 交付粒度：一个分支一副 PR 合并到 main（对齐 V3.6 #366 / V3.7 #367 先例）

## 一、V3.7 合并确认

- `origin/main` 已包含 `27ce1a51`「feat(aitde-v37): Impact Analysis + Smart Regression (V37-001..014) (#367)」。
- V3.7 QA 报告存在于 `test-platform-v2/work-logs/evidence/v37/qa-report.md`（随 #367 合入 main）。
- 结论：**V3.7 已合并**，V3.8 从最新 main 切出（前置条件满足）。

## 二、交付内容（V38-001..014）

### 后端（`test-platform-v2/backend`）
- `app/modules/aitde/ai_closed_loop/models.py` — 8 张表：`failure_hypotheses` / `flaky_signals` / `flaky_clusters` / `ai_suggestions` / `human_feedback` / `strategy_performance` / `scenario_gap_candidates` / `model_evaluation_runs`
- `app/modules/aitde/ai_closed_loop/repository.py` — 薄数据访问层（无 ORM 外泄）
- `app/modules/aitde/ai_closed_loop/schemas.py` — Pydantic 请求模型
- `app/modules/aitde/ai_closed_loop/service.py` — FailureEvidencePackBuilder / FailureTriageAgent / HypothesisReviewService / HealingPolicy / ApprovedHealingApply / FlakyDetector / FlakyClusterService / StrategyPerformanceService / DataStrategyAdvisor / ScenarioGapDetector / SuggestionInboxService / HumanFeedbackService / PromptEvaluationService / AutoRetryPolicy（含硬护栏）
- `app/modules/aitde/common/enums.py` — 新增 V38 枚举（FailureHypothesisStatus/FailureClassification/HealingPolicyDecision/FlakySignalType/FlakyClassification/SuggestionType/SuggestionStatus/FeedbackType/StrategyType/ScenarioGapType/GapCandidateStatus/ModelEvaluationStatus/AutoRetryDecision）
- `app/api/v2/ai_closed_loop.py` — 15 个 `/api/v2` 端点（triage/hypotheses/healing/flaky/stability/suggestions/gaps/feedback/model-evaluations）
- `app/api/v2/router.py` — 挂载 ai_closed_loop 路由
- `alembic/versions/20260902_aitde_v38_ai_closed_loop.py` — 带存在性守卫的幂等迁移（down_revision=v37_smartreg，单头）
- `app/modules/aitde/intelligence/prompts/*.txt` — `failure_triage_v1` / `action_healing_v2` / `scenario_gap_analysis_v1` / `data_strategy_advice_v1`（均含 forbidden-mutation 规则）
- `tests/fixtures/route_inventory.json` — 路由基线一次性对齐（+15 条，总数 580）

### 前端（`test-platform-v2/frontend`）
- `src/api/aiClosedLoop.ts` — API 客户端 + 类型 + 标签映射
- `src/pages/ai-suggestions/index.tsx` — Suggestion Inbox
- `src/pages/flaky/index.tsx` — Flaky 分析
- `src/pages/missions/gaps.tsx` — Mission 场景缺口
- `src/pages/admin/ai-evaluations/index.tsx` — AI 模型评估
- `src/router/index.tsx` + `src/pages/missions/MissionLayout.tsx` — 路由与导航登记

### AI Skills（`test-platform-v2/.claude/skills/`）
- `test-failure-triage` / `test-action-healing` / `test-flaky-analysis` / `test-scenario-gap-analysis`

### 测试
- `backend/tests/aitde/v38/` — conftest + 6 个测试文件（23 用例）

## 三、自检结果（AGENTS.md §3）

| 检查 | 命令 | 结果 |
|------|------|------|
| 后端硬门禁 F821 | `ruff check app/ --select F821` | ✅ All checks passed |
| 后端受影响模块 | `pytest tests/aitde/v38` | ✅ 23 passed |
| 相邻域回归（v37+v38） | `pytest tests/aitde/v37 tests/aitde/v38` | ✅ 41 passed |
| ruff（新文件全规则） | `ruff check app/modules/aitde/ai_closed_loop app/api/v2/ai_closed_loop.py ...` | ✅ All checks passed |
| Alembic 单头 | `python -m alembic heads` | ✅ 单头 `20260902_aitde_v38_ai_closed_loop` |
| 前端类型检查 | `npm run typecheck` | ✅ |
| 前端 lint | `eslint ... --max-warnings=0` | ✅ |
| 前端 build | `npm run build` | ✅ built in ~10s |
| 前端受影响测试 | `vitest run src/layouts/nav-config.test.ts` | ✅ 9 passed |
| 调试残留 / 密钥 | 人工排查 | ✅ 无 |

## 四、已知限制（本分支已知）

1. `tests/test_route_inventory.py` 依赖 `app.main` ∋ `temporalio`，本地 dev 环境无法执行；CI 测试环境执行（路由基线已按 +15 条对齐）。
2. 本地无法执行依赖 `app.main` 的整库后端测试（root conftest 引入 `app.main` ∋ temporalio），故后端全量回归在 CI 完成。
3. Failure Triage / Healing / Gap / Data Strategy 的 AI 语义部分由确定性 service 承载（assist-evidence + 硬护栏），Full-LLM 语义摘要未在本分支引入（对齐 plan §4/§9 的「AI 是增强层」边界）。

## 五、任务映射

- V38-001 Failure Evidence Pack ✅（secret/PII 脱敏）
- V38-002 FailureTriageAgent ✅（Outcome immutable）
- V38-003 Hypothesis Review ✅（confirm/reject 审计）
- V38-004 HealingPolicy ✅（Oracle/Contract diff reject）
- V38-005 Approved Healing Apply/Retry ✅（new plan version，old 保留）
- V38-006 Flaky Signal Pipeline ✅（BusinessFail excluded）
- V38-007 Flaky Cluster UI ✅（样本可追溯）
- V38-008 Strategy Performance ✅（project isolation）
- V38-009 Data Strategy Advisor ✅（不绕 Policy）
- V38-010 Scenario Gap Detector ✅（proposal only）
- V38-011 Suggestion Inbox ✅（P0 bulk approval 保护）
- V38-012 Human Feedback Metrics ✅（append-only）
- V38-013 Golden Model Evaluation ✅（regression threshold）
- V38-014 AutoRetry Policy ✅（BusinessFail 不无限重试）
