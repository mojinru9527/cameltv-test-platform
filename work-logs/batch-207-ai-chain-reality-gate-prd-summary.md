# Batch 207 — AI 全链路 Reality Gate — PRD Summary
> **Product (🟦)** | Date: 2026-09-02 | Status: Approved

## 1. 问题陈述
main@34225781 的 AITDE「需求 → 范围 → 歧义/意图 → 契约 → 场景 → Oracle → CommandPlan → 执行/信任门」AI 全链路存在系统性骨架与断链，代码审计确认如下根因（详见对话审计结论）：

1. **Provider 是空壳**：`LegacyAIServiceProvider` 5 个方法全部 `return self._fallback.xxx()`，`ai_enabled` 参数永远为 False 且全仓库无任何生产入口传 True → 平台无论是否配置 AI 都永久走 `DeterministicScopeProvider` 占位。
2. **确定性占位产物不可信也不可执行**：`design_scenarios` 产出 `when.action=rule_key`、`oracle(DB).target={"state": ...}`、`expected={"ok": True}`；Oracle 又标 `AI_INFERRED + required=True`（违反 golden 校验「AI_INFERRED required 必须 False」），且 Oracle Guard 使 AI_INFERRED 永远无法 approve → **Trusted Release Gate（G4）结构性不可达**。
3. **CommandPlan 无服务端生成方**：`ActionPlanner` 是全仓库零引用的死代码；`/action-plans/generate` 接受客户端任意 plan JSON；执行器/`oracle_engine`/registry 三种 IR 方言互不兼容；`ScenarioOracleBinding` 无任何生产写入方 → oracle 评估恒 `NOT_EVALUATED`、Outcome 恒 `INCONCLUSIVE`。
4. **假 AI 溯源**：确定性输出被落库为 `actor=AI / created_by_type=AI / AI_INFERRED` + 写死 confidence 0.80，`source_refs` 全部 `artifact_id=0`（`validate_source_refs` 显式跳过）→ 溯源校验空转；且因 0.80<0.85，**每个 scope 项都会被判定为歧义**，人工评审量被系统性放大。
5. **AI 治理/闭环是空转表面**：`ai_ops`（AIOperationRecord）无任何生产者（scope 接口返回 `operation_id=None`）；V38「AI QA Closed Loop」全规则引擎、无 run 完成钩子、无 suggestion 生产者、PromptEvaluation runner 未实现；12 份提示词模板零代码引用。
6. **Smart Regression 生产快照 loader 未实现**（只认 `inline:`）；真实 LLM 调用栈四套并存；AI 可用性门控项目级/环境级两套并存。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| AI provider 5 方法真实调 LLM（resolve 成功 + mock） | 0/5 | 5/5 | 单测 |
| 无 AI 配置时确定性降级且既有测试全绿 | — | 相关 pytest 全绿 | PR |
| 确定性/AI 溯源诚实（created_by_type、oracle source_type/required/confidence 一致） | 伪造 | 诚实可审计 | 单测 |
| ActionPlanner 有服务端调用方并生成 DRAFT plan | 0 | ≥1 端点 | 单测/API |
| run 缺 binding/plan 显式失败（不再静默 NOT_EVALUATED） | 静默 | fail-fast | 单测 |
| G4 可达性：oracle promote + binding 创建路径 | 不可达 | 可构造达标 | 单测 |
| ai_ops 在真实 AI 调用时写入记录并回传 operation_id | 0 | AI 路径必写 | 单测 |
| 主链 4 份提示词模板被 AI provider 真实读取 | 0 | 4 | 单测 |

## 3. 非目标（本次不做）
- **不引入 async 全链重构**：provider/route/service 保持同步（对齐 legacy_cutover 现有同步 httpx 先例）。
- **不实现真实浏览器 UI 自动化执行后端 / 不把 AI planner 产出直接接浏览器运行**：本批为「AI 能产出可信、可校验、可被现有执行面消费」的 reality gate；把 AI→可执行浏览器 plan（`browser_action_planner_v1`）与「从真实 DOM/API 观测自动物化 binding」列为 Leader C 条件（需观察/混合运行运行时已真实接线，超出本批）。
- **不统一重构既有 4 套 LLM 调用栈**（ai_service/llm_json_client/legacy_cutover/api_generalization）：本批新增统一同步 client 供 intelligence 使用并复用解析，栈合并列 C 条件。
- **不改前端**：`/action-plans/generate` 向后兼容（缺 plan 时服务端生成），前端 ActionPlanEditor 继续可用。
- 不改 v1 knowledge agent / requirement 两阶段 AI（已真实接线，不在断点内）。

## 4. 用户故事 + 验收标准
- As a 测试平台用户, I want 配置 AI 后评审流真正调用 LLM（mock 验证），未配置时确定性降级，so that「AI 生成」不再名不副实。
  - 验收：Given 项目已配置 AiProvider / When scope·ambiguity·contract·scenario 任意生成 / Then provider 以 `ai` 模式调用 mock LLM 并落 `created_by_type=AI` + 写 ai_ops 记录、返回 operation_id。
- As a 测试负责人, I want 每个评审对象可审计来源，so that 我不用猜它是 AI 还是规则产物。
  - 验收：deterministic 产物 `created_by_type=DETERMINISTIC`、oracle `RULE_BASELINE`/`required=False`、真实 source_refs；AI 产物 `AI_INFERRED/required=False` + 真实 source_refs。
- As a 测试工程师, I want 场景能由服务端生成 CommandPlan，缺 binding/plan 时得到明确报错，so that 我不会拿到永远 INCONCLUSIVE 的运行。
  - 验收：Given 场景已 approve / When 调生成端点（不带 plan）/ Then 返回 ActionPlanner DRAFT；run 提交时缺必要 plan/binding → 400 明确原因。
- As a 测试工程师, I want 对 AI 生成的 oracle 做显式人工信任升级 + 建立 binding，so that G4 信任门可达。
  - 验收：`review oracle {promote:true}` → source_type=TESTER_APPROVED + APPROVED；binding 创建后 evaluate 可得 TRUSTED PASS/FAIL。

## 5. 技术考量
- 同步 LLM 调用复用 `ai_config_service.resolve(db, project_id)` + httpx（对齐 `legacy_cutover/service.py:85` 先例）；解析复用 `ai_service` JSON 解析思路（统一放新 `intelligence/llm_sync.py`）。
- 新行为涉及 Oracle 信任语义（human promote）→ 属于「新行为」，判定**完整批次**。
- 风险：行为语义变更（deterministic ambiguity、oracle required、approve guard 例外）需同步更新少量既有测试并逐条在 QA 记录；不破坏 V3.9 不变量「AI 永不静默成为 Required」。
- CI 域：仅 backend（scope=test-platform-v2/backend）+ work-logs 文档。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main（本批） | 开发/测试 | required checks 全绿 + Leader APPROVED |
| 真实 AI 配置验证 | 企业 dev 环境 | 用真实 provider 冒烟 scope 生成一次 |
| C 条件批次 | 后续 batch | 见 Leader C1–C7 |

## 7. 技能使用
- cameltv-agent-team → 六部门流水线 + 工件（本文件所属）。
- cameltv-bug-guard → 编码前避坑清单（静态路由/except 顺序/降级分类/StaticPool 测试等）。
- karpathy-guidelines → 外科手术式改动、明确验收标准。
