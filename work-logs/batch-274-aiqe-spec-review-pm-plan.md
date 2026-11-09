# Batch 274 — AIQE Spec Review：PM Plan

> **部门**：🟨 PM
> **日期**：2026-11-09
> **关联 PRD**：[batch-274-aiqe-spec-review-prd-summary.md](batch-274-aiqe-spec-review-prd-summary.md)

---

## 1. 评审任务拆分

本批无代码任务。七个"评审任务"对应 PRD 中要求的 7 个决策点，每条任务目标 ≤ 60 分钟，可独立完成。

### T1：§0 P0 清零 5 条阻塞 — 顺序与验收标准审计

- **目标**：确认 P0-1 ~ P0-5 的处置顺序正确、验收标准可执行、不重叠。
- **涉及文件**：13 号规格 §0 表格（`f:/CamelTv/docs/platform-refactor/13-ai-quality-agent-merged-spec.md` 顶部 P0 表）。
- **验收标准**：
  - 每条 P0 的"开发要做的事"列是具体命令或文件修改，不是"评估一下"这种模糊语；
  - 每条 P0 的"验收证据"列有可核对的产物（records 表的一行 / curl 日志 / 磁盘水位截图 / 迁移 downgrade 可执行等）；
  - P0-1..5 之间无循环依赖（如 P0-2 不能依赖 P0-5）；
  - 与 C273-1、C273-5 做对账，确认不重复记账。
- **交付**：QA 报告第 1 节结论。

### T2：§4 数据模型 22 张表 — 与现有 app/models 重复风险审计

- **目标**：抽样 5 张高风险表，核对现有 `test-platform-v2/backend/app/models/` 是否已有同义实体；确认 22 张表都带 `project_id`（除 `agent_executions` 等明示例外）。
- **涉及文件**：13 号 §4、现有 `app/models/*.py`（本会话 §18.5 已列 8 个已知接入点，但需扩抽样）。
- **验收标准**：
  - 高风险表清单：`test_scenarios / test_cases / defects / agent_executions / run_events` 共 5 张；
  - 每张给出"现有表 → 13 号目标表 → 建议策略（ALTER 扩字段 / 新表迁移 / 废旧建新）"；
  - 所有 22 张表的 JSON 字段必须声明 `schema_version`——CI 守卫 TA-004.2 承接；
  - project_id 缺失清单（预期 ≤ 3 张全局表）。
- **交付**：QA 报告第 2 节 + Design spec 第 3 节的对账表。

### T3：§5 状态机 — Run(10) × Node(10) × Attempt(7) 完备性与冗余审计

- **目标**：验证合法转换集合完备、无死状态、无不可达状态；状态 vs outcome 分离规则无歧义。
- **涉及文件**：13 号 §5。
- **验收标准**：
  - 画出 Run 状态转换邻接表（文字形式），确认 `COMPLETED` 的入边 ∈ {RUNNING, WAITING_HUMAN, TRIAGING}；确认 `BLOCKED/CANCELED/ERROR` 无 outcome；
  - Node 10 状态的 `SKIPPED` 入边清单明确；
  - Attempt 7 状态的 `TIMED_OUT` vs `ERROR` 边界明确；
  - 回答："`WAITING_HUMAN` 能否直接转 `CANCELED`？" 这类遗漏边场景 ≥ 3 个。
- **交付**：Design spec 第 4 节 + QA 报告第 3 节。

### T4：§6 + ADR-AIQE-008 WorkflowDefinition — 不重蹈 AITDE 的护栏审计

- **目标**：验证 WorkflowDefinition 的建模不构成"第二套 Mission/Scenario/Oracle"。
- **涉及文件**：13 号 §6、§24 ADR-AIQE-008。
- **验收标准**：
  - 对比 AITDE 的 `scope → contract → scenario → oracle` 四层 与 13 号的 `requirement_contract → test_scenario → test_case → workflow_definition` 四层，列出差异：
    - 是否复用现有 `requirement/test_case` 表（不建平行表）？
    - 是否有"Agent 自动冻结 Workflow"反模式？
    - 是否有"LLM 临场决定已批准 Workflow 的每一步"的 bypass 路径？
  - 列出三条明文护栏在规格中的位置，确认每条都有 §2/§9/§10 的硬规则背书。
- **交付**：Design spec 第 5 节 + QA 报告第 4 节。

### T5：§11 噪音治理 — 项目无关性审计

- **目标**：验证 11 类干扰目录 + 6 对照实验对 SaaS/电商/IoT 项目仍然适用。
- **涉及文件**：13 号 §11。
- **验收标准**：
  - 对每个非体育场景（电商退款 / SaaS 租户隔离 / IoT 设备影子）检查：11 类分类里是否至少有 3 类明显适用；6 对照实验里是否至少有 2 项可直接用；
  - 若有任何一类"只对体育适用"的规则，必须指出并建议迁移到 Domain Pack；
  - 噪音规则库 90 天强制复核规则（§11.9）在电商/IoT 场景是否过宽/过严。
- **交付**：Design spec 第 6 节 + QA 报告第 5 节。

### T6：§14 OSS 准入 — AGPL 风险 + 版本锁审计

- **目标**：确认 TestZeus AGPL-3.0 的处理方案满足闭源商业分发要求；验证 Playwright / Midscene / Appium / Keploy 的版本锁合理。
- **涉及文件**：13 号 §14、附录 A。
- **验收标准**：
  - TestZeus 的处理方案（"仅在完全隔离的独立服务中使用，不深度合并"）必须经过"闭源商业分发 = 是/否"二选一确认；
  - Playwright 1.56 版本锁 → 确认 Test Agents 功能从 1.56 起支持的事实证据；
  - Midscene.js 的 2026-04 iOS/Android/HarmonyOS 支持事实证据；
  - Appium MCP：确认使用"官方 pulsemcp" 实现而非低星非官方 fork；
  - Keploy 的 eBPF 权限审计具体命令是否可执行。
- **交付**：Design spec 第 7 节 + QA 报告第 6 节。

### T7：§19 TA-000..045 工期估算现实性审计

- **目标**：验证 MVP 8-10 周 / V1 16-20 周估算对 5-6 人团队合理；如果是 2-3 人团队要给出放大倍数。
- **涉及文件**：13 号 §19 全表 + §23 里程碑表。
- **验收标准**：
  - 对每个 Phase（0 ~ 6）核算"人日总数 / 并行度"，与里程碑周数相除，得出"人数需求下限"；
  - 若 5-6 人假设下某 Phase 实际需 > 6 人并行 → 标红；
  - 给出 2-3 人团队的时间线放大倍数估算；
  - 列出可以从 V1 推迟到 V1.1 / V1.2 的 TA 任务（如 Appium/miniapp/desktop/硬件相关）。
- **交付**：Design spec 第 8 节 + QA 报告第 7 节。

## 2. 任务分配（单 Session 顺序执行）

| 任务 | 预估工时 | 负责部门 | 依赖 |
|-----|---------|---------|------|
| T1 | 15 min | Design + QA | 无 |
| T2 | 25 min | Design + Dev + QA | 无 |
| T3 | 20 min | Design + QA | 无 |
| T4 | 20 min | Design + QA | 需引 11 号方案 §6 D 规则 |
| T5 | 15 min | Design + QA | 无 |
| T6 | 15 min | Design + QA | 无 |
| T7 | 15 min | Design + QA | 需查 §19 工时数字 |
| Dev 审计 | 30 min | Dev | T2 + T7 完成后 |
| Leader 判决 | 20 min | Leader | 全部完成 |
| **合计** | **~2.5h** | | |

## 3. 不做的事（范围蔓延防护）

- **不实际修 13 号规格文本**：所有修改建议写到 QA/Leader verdict 的 M-N 条目，不执行 Edit。
- **不开 PR / 不 commit**：评审产物保留 untracked。
- **不扫 test-platform-v2/ 代码**：只对账本会话 §18.5 已列的 8 个接入点；完整代码审计是 TA-001 的工作（在 Phase 0），不是本批责任。
- **不定 iOS 真机方案**：13 号 §13 已登记三选一，本批只确认"登记充分"不拍板。

## 4. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|:---:|:---:|-----|
| 评审者（即本 Session）对规格过于自信（既是作者又是评审者） | 高 | 中 | QA 部门默认立场"需要改进"，对每条决策用 NEEDS_FIX 开门 |
| 对账 §4 数据模型抽样不足以发现所有重复 | 中 | 高 | 明示 TA-001 承接完整审计；本批只覆盖 5 张高风险表 |
| 工期估算无历史基线做对比 | 中 | 中 | 参考 B1-B4 (batch-258 ~ 261) 的实际工期，粗估倍数 |
| 本批工件自身占用 token 过多拖累后续开工 | 低 | 低 | 控制每份工件 ≤ 500 行 |

## 5. Definition of Done（本批）

- [ ] 7 个评审任务全部有结论（PASS / NEEDS_FIX / UNKNOWN）；
- [ ] QA 报告含复盘卡；
- [ ] Leader verdict 给出三选一判决；
- [ ] 若 "修改后合入" 列出 M-1 ... M-N 具体条目；
- [ ] 流程回写小节产出（见 Leader verdict 末尾）；
- [ ] 看板 slice 全部标 ✅；
- [ ] C-CONDITIONS.md 不新增条件（本批不定硬门禁，不开 C274-x）——若评审产生待办，由后续批次承接。
