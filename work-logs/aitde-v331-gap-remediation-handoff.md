# AITDE v3.3.1 查漏补缺 — 跨会话交接文档

> 交接时间：2026-08-29
> 交接场景：审计会话（F:\CamelTv）→ 开发会话（本 worktree）
> 任务：基于最新 main 开发 v3.3.1，修复审计发现的 V3.0–V3.3 版本间遗漏/缺失问题（全面查漏，分阶段滚动交付）

---

## 1. Worktree / 流程信息

| 项 | 值 |
|---|---|
| 路径 | `F:/CamelTv-worktrees/claude-aitde-v331-gap-remediation` |
| 分支 | `feature/aitde-v331-gap-remediation`（基线 origin/main @ 17b72815） |
| 执行器 | claude（ZCode 宿主，用户确认） |
| 工作流 | agent-team（六部门流水线，完整批次模式） |
| 端口 | 前端 5440 / 后端 8340 |
| 验证 | `verify-ai-worktree.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor claude` 已通过 |

**流程强制项**（详见 `.agents/skills/cameltv-agent-team/SKILL.md`）：
- 完整批次六件：PRD + PM + Design + Dev(代码+看板) + QA + Leader，工件命名 `work-logs/batch-aitde-v331-gap-remediation-{prd-summary|pm-plan|design-spec|qa-report|leader-verdict}.md`
- 批次模式判定：本批次含新行为（Bridge 接入真实执行链路）、新配置（菜单入口）→ **完整批次**；其中纯验收子项（如执行 V3.2 验证清单）在 QA 报告中引用即可
- 首轮 QA 证据完成后做**一次总确认**（推送+Draft PR+checks 绿后合入 main），此后不再逐次询问
- 提交前跑 `pwsh scripts/git/dev-gate.ps1 -RepositoryPath (Get-Location).Path`（G0–G2 机械门禁）
- 每切片即刻 commit（worktree-reset-hazard）
- Leader 判决末尾含「流程回写」小节 + QA/Leader 末尾附复盘卡

---

## 2. 审计背景（为什么有这个批次）

对 `docs/aitde/versions/V3.0~V4.0` 计划包与实际实现做了逐版对账审计，结论：三个版本代码主链已合入，但普遍存在"代码合并完成 ≠ 版本落地完成"——验收门禁（Transition Gate / Release Gate / 专项校验）未执行，部分"集成型"任务停在"模块+单测、未接主链"。

**重要校准**：审计初稿基于旧基线（2e092fa3）。最新 main 已合入 PR #335–#353，其中已修复大量缺口（见 §3）。**以下 §4 清单已在最新 main（17b72815）上逐一重新验证，是当前仍真实存在的缺口。**

## 3. 最新 main 已修复项（勿重复开发）

| 原 audit 缺口 | 修复 PR | 说明 |
|---|---|---|
| V32-009 无 provision 端点 | #335 | `POST /api/v2/fixtures` 已存在 |
| V3.2 列表端点 500 | #336 | response_model 修复 |
| V32-002 派生只认 entity.field | #337 | 兼容非结构化 + Oracle 派生 |
| **V32-014 Run Data 未接线** | #338 | `execution/service.py mark_running → prepare_run_data`，DATA_FAIL 保留不被业务 outcome 覆盖 |
| V3.2 §93 专项校验未执行 | #339 | DB 无关部分已有测试+QA 报告（真实库项标待基础设施） |
| fixture 环境隔离 | #340 | 复用按 environment 隔离 |
| V3.3 全量（PR33-01..10） | #341–353 | Command IR / Browser Driver / Observe / Manual / Hybrid / Healing / Legacy Adapter / UI |

## 4. 仍存在的缺口清单（本批次范围，已在 17b72815 验证）

### A. 接线类（优先级最高 — 阻塞版本验收成立）

| # | 缺口 | 证据锚点 | 计划出处 |
|---|---|---|---|
| A1 | **V3.1 Legacy Bridge 未接入真实执行链路**：`bridge_api_item/bridge_ui_run` 唯一调用点是 v2 HTTP 端点（`api/v2/executions.py:185,189`），且端点不传 request/response/screenshots → 桥接产物永远零 Evidence；`api_execution_service`、`playwright_executor`、UiTestRun 流程均不调用 bridge | `app/modules/aitde/execution/legacy_bridge.py`（#329 后无触碰） | V3.1 计划 §8「现有 API/UI 接入」：复用 api_execution_service / playwright_executor，执行后 Bridge 创建 Run/Step/Evidence/AssertionResult，UI screenshots/video/trace 全部注册为 EvidenceArtifact |
| A2 | **EvidenceCompletenessPolicy 是死代码**：正式 Outcome 计算用简化逻辑（证据数>0 且全 SANITIZED）,"Required Evidence 按 adapter/oracle 完整才 PASS"核心不变量未生效 | `app/modules/aitde/assertion/completeness.py` 无生产调用；实际路径 `api/v2/executions.py:164-167` → `service.compute_outcome` | V3.1 计划不变量 4 |
| A3 | **AssertionEngine 无生产写入方**：真实 Run assertions 恒空 → classify 恒 INCONCLUSIVE（A1 修复后自然解决大半：§8 明确断言写入方就是 Bridge） | `app/modules/aitde/assertion/engine.py:73` 仅测试调用 | V3.1 §8「AssertionResult（若旧数据可映射）」 |

### B. 入口/体验类（V3.0 EPIC-09 遗留）

| # | 缺口 | 证据锚点 |
|---|---|---|
| B1 | **/missions 菜单入口缺失**：seed.py 菜单表无 missions 入口，flag 开启后只能手输 URL | `app/seed.py:17-58`（菜单段）；V30-103 |
| B2 | V30-085 AI Debug Drawer + `mission:ai_view_debug` 权限未实现 | 全仓库 grep 无 ai_view_debug |
| B3 | V30-100 TanStack Query 未用（missions 页裸 fetch + useEffect） | `frontend/src/pages/missions/index.tsx` |
| B4 | V30-107 409 STALE 乐观锁 UI、V30-109 Accessibility 未做 | 同上页面 grep 无 409/aria |

### C. 验收基建类（Release Gate 无法勾选的根因）

| # | 缺口 | 证据锚点 |
|---|---|---|
| C1 | **e2e 无任何 aitde spec**（V3.0/V3.1/V3.2/V3.3 各计划都要求） | `frontend/e2e/` 无 aitde-*.spec.ts |
| C2 | **Golden AI fixtures 缺失**：`backend/tests/fixtures/aitde/v3/` 不存在 | V30-124 |
| C3 | 前端 missions/executions 组件测试为 0 | `src/pages/missions/` 全部无 __tests__ |
| C4 | V30-121 API 契约测试（409/project isolation 专项）缺 | tests/aitde/v31 无 project_isolation 专项 |
| C5 | V30-041 `ambiguity_intent_v1` prompt 缺（现 6 个 prompt 无此文件） | `app/modules/aitde/intelligence/prompts/` |
| C6 | **版本 Transition Gate 全部未勾选**：`docs/aitde/validation/99_Cross_Version_Validation_and_GoLive_Gates.md` V3.0→V3.1→V3.2→V3.3 各门全 `- [ ]`；Shadow Mode（100 Run 对比、False Pass 审计）0 次执行 | 该文档 §2-§5 |
| C7 | V3.2 验证清单（`docs/aitde/versions/V3.2_Verification_Checklist.md`）11 项记录表全未勾选；Part C 描述已过时（Run 现在会走 DATA 时间线，#338 后该描述已部分成立，需复核更新） | 该文档 |

### D. 已知说明（非本批次必须修，注意别误判）

- `data_requirement_derivation_v1` prompt / test-data-design skill 未交付 —— V3.2 §11 是可选项，派生已规则式实现（#337），**降级为实现选择，不算缺失**
- "AI 未接真 LLM" —— LegacyAIServiceProvider 已实现，主链默认确定性 Provider 是设计选择，**不算缺失**（唯一例外是 C5 的 prompt 文件属 V30-041 任务卡硬性要求）

## 5. 建议的子阶段拆分（全面查漏 → 分阶段滚动）

**阶段 1（本阶段，P0 接线+入口）**：
1. A1 Legacy Bridge 深度接线：api_execution_service 执行后调 bridge（带 request/response）；playwright_executor 执行后调 bridge（带 screenshots/video/trace）；v2 端点补可选 payload
2. A3 断言映射：旧数据可映射时写入 AssertionResult
3. A2 completeness policy 接入 compute_outcome
4. B1 /missions 菜单入口（seed.py + 菜单门控）

**阶段 2（验收基建）**：C1 e2e 冒烟（v3 主链 + replay + data runtime 各 1 条）+ C4 project isolation 专项 + C3 核心 UI 组件测试
**阶段 3（门禁闭环）**：C6/C7 补跑 Shadow 对比与验证清单，勾选或显式记录"带门进入"决策 + B2/B4 + C5
**阶段 4（视情况）**：B3 TanStack Query 迁移

## 6. 关键参考

- 审计对话结论 + V3.0 计划范围边界原文：`docs/aitde/versions/V3.0_Detailed_Development_Implementation_Plan.md` §1.1/§1.2（必须完成/明确不做清单——判定缺口归属的依据）
- V3.1 §8 接入要求原文：`docs/aitde/versions/V3.1_Detailed_Development_Implementation_Plan.md:334-373`
- V3.2 §7/§8：`docs/aitde/versions/V3.2_Detailed_Development_Implementation_Plan.md:313-382`
- 避坑：`cameltv-bug-guard` skill（写后端/前端前读）；UI 规范：`cameltv-ui-conventions`
- 每切片提交前：`pwsh scripts/git/scan-common-bugs.ps1`（HARD>0 必须处理）
