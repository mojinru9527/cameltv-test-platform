# Batch 274 — AIQE Spec Review：Leader Verdict

> **部门**：🎯 Leader
> **日期**：2026-11-09
> **输入**：PRD / PM / Design / Dev / QA 五份工件
> **评审对象**：[13-ai-quality-agent-merged-spec.md](../docs/platform-refactor/13-ai-quality-agent-merged-spec.md)（2899 行）

---

## 1. 判决

# 🟡 修改后合入（Conditional Approve）

**理由**：
- 规格书**结构完整、术语基本一致、与 AITDE 教训对账清晰、与 11 号方案不冲突**；
- 但存在 **7 条 P0 阻塞**，不修即开工会导致数据模型重复建设 / 法律风险 / 实施阶段卡壳；
- **12 条 P1** 可在 Phase 1 开工前的轻量批次中逐条修；
- **13 条 P2** 可在后续批次陆续处理，不阻断。

**本判决有效期**：14 天。若 14 天内未开 batch-275 修 P0，本判决作废，需重新评审。

---

## 2. 必须修（M-P0，共 7 条）

| M-ID | 位置 | 修改内容 | 承接批次 |
|------|------|---------|---------|
| **M-2** | §4.7 `test_runs` | 显式对账现有 `version_task_run.py`，给出 "扩字段" 或 "新表 + 数据迁移脚本" 的明确方案；在 §4.7 加一节 "与现有 version_task_run 的关系" | batch-275 |
| **M-3** | §4.8 `node_runs` | 显式说明 `node_runs` 与 `execution_job.py / plan_execution_job.py` 的 1:1 或 1:N 关系；在 §4.8 加 `execution_job_id` 字段 | batch-275 |
| **M-4** | §4.14 `target_environments` | 删除新建此表；改为"扩展现有 `environment.py` 加 `allowed_actions / data_sources_json` 字段"；§14 相关引用同步改为 `environments` | batch-275 |
| **M-5** | §4.19 + §0 P0-5 | 明示 `ai_job.py / ai_shadow_run.py / ai_gateway_cache.py` 在 P0-5 一并删除；`agent_executions` 单独承载 Agent 调用审计 | batch-275 |
| **M-16** | §14 TestZeus | §14.1 加硬门禁："**采用 TestZeus 前必须经法务书面评估，闭源商业分发风险不可接受时直接从候选清单剔除**"；§14.4 PoC 矩阵把 TestZeus 的通过条件改为"AGPL 法务通过 + 隔离部署方案成立" | batch-275 |
| **D-3** | §4.12 + TA-007 | 指定对象存储选型（候选：腾讯云 COS / MinIO 自托管 / 本地 FS 三选一），加到 §4.12 Artifact Manager 和 附录 A | batch-275 |
| **D-9** | §21 Benchmark | 明示 benchmark 数据集来源（A1: 从现有 requirement 表导 30 条；A2: 从 test_case 表采样 50 份；A4: 从 defect + run_events 构造 100 个失败样本），并写明"**数据集准备是 TA-001 的并行子任务，不是 Agent 开工时才找**" | batch-275 |

**一句话**：7 条 P0 全部指向同一个根因——**13 号合并时缺少一份与当前 `app/models/` + `app/services/` 真实清单的完整对账**。batch-275 必须先产出这份对账，再改规格。

---

## 3. 建议修（M-P1，共 12 条，batch-276 承接）

| M/D-ID | 位置 | 修改要点 |
|-------|------|---------|
| M-6 | §4 各 Run 子表 | project_id 隔离规则统一到附录 B 一行"所有 Run 子表继承 run.project_id，查询加 join；全局表明示" |
| M-12 | §24 ADR-AIQE-008 | 补 PR 模板强制问答："本 PR 新建带 checksum + approval_status 的实体，是否 AITDE Scenario 翻版？（证据）" |
| M-13 | §11.2 | UI_OVERLAY 分类加 `requires_ui_surface: true` 元数据；adapter capability 层声明启停 |
| M-15 | §11.9 | 噪音规则 effective_until ≤ 90 天 **但可被 Owner 显式续期（重新审批）** |
| M-18 | §14.4 | PoC 矩阵加"失败回退方案"列（如 TesterArmy 不通过 → 回退纯 Playwright；Keploy 不通过 → 回退手写 mock） |
| M-19 | §23 里程碑 | 加一行 "2-3 人团队：MVP 16-20 周 / V1 32-40 周（× 2）" |
| M-20 | §19 TA 表 | 每条 TA 加一列 "优先级档"（MVP / V1 / V1.1+），便于裁剪 |
| D-1 | §8.3 | seq 生成在 SQLite 下走表自增 + 唯一索引，Postgres 下走 advisory lock；在附录加"Durability 分 DB 兼容表" |
| D-4 | §16.2 | 脱敏库候选：`presidio` / `faker-sensitive` / 自写正则；§16.2 指定其一 + 配置 YAML 位置 |
| D-5 | §4.12 | 加"`lanhu_evidence` 承接蓝湖专项证据；`run_artifacts` 承接 Run 执行证据；两者互不迁移，查询时按 `linked_evidence_type` 并集"规则 |
| D-6 | §18.2 | 前端路由决策："**保留 `/version-tasks` 作为业务入口，新建 `/runs` 作为通用 Run 列表**；详情页组件可复用" |
| D-7 | §6.4 | TA-001 代码审计时验证 `task_queue.py` 是否已有 advisory lock + heartbeat；如无，TA-010.3 必须自实现 |

---

## 4. Known Issues（P2，共 13 条，后续批次陆续）

见 QA 报告 §3.3。总体上都是"边缘场景/typo/工程细节"，不影响合入。

---

## 5. 合入路径

```text
batch-274（本批）✅ 完成 Leader verdict = 修改后合入
    │
    ▼
batch-275-aiqe-spec-fix-p0（docs-only 轻量批次）
    - 修 13 号 7 条 P0
    - 规格 status: proposal → active
    - 产物：13 号 v1.1 + PR
    │
    ▼
batch-276-aiqe-spec-fix-p1（docs-only 轻量批次）
    - 修 13 号 12 条 P1
    - 产物：13 号 v1.2 + PR
    │
    ▼
batch-277-aiqe-ta-000-p0-clearance（完整批次，涉及代码/运维）
    - §0 P0-1..5 清零
    - 产物：真实证据（AI 调用记录、备份演练、盘水位、/uitest 剥离、ai_gateway 删除）
    │
    ▼
batch-278-aiqe-ta-001-baseline-audit（docs-only 完整批次）
    - 产出 docs/aiqe/baseline.md
    - 产物：22 张目标表 → 现有类/表/路由/组件 映射表
    │
    ▼
batch-279+ 真正开 Phase 1 代码（TA-005 Run 模型 / TA-006 Event / TA-007 Artifact / TA-008 Console MVP）
```

**在 batch-278 产出之前，任何 TA-005+ 的代码 PR 必须被 QA 打回**。

---

## 6. 知识审计

### 6.1 本批可入 KB 的知识

| 知识 | 类型 | 入库建议 |
|------|-----|---------|
| "规格合并时必须附现有代码对账表" | 流程教训 | 走 `ingest_platform_knowledge`（type=`platform_knowledge`） |
| "AGPL-3.0 组件采用必须法务前置评估" | 决策 | 同上 |
| "数据模型新建前必须核对 app/models 整树" | 设计规范 | 同上 |
| "Run 状态机 status × outcome 分离模式" | 架构模式 | 同上 |
| "噪音治理 11 分类 + 6 对照实验矩阵" | 测试工程模式 | 同上 |
| "Agent Skills 开放标准 vs MCP Gateway 的使用边界" | 决策 | 同上 |

**建议**：合入 batch-275 时由 Dev 部门产出 KB 入库草稿（6 条）。本批不入，因 13 号本体未合入。

### 6.2 与 KB 已有知识的矛盾检查

- ✅ 不与 ADR-0014 / 0015 / 0019 / 0020 矛盾；
- ✅ 不与 11 号方案 §2 删除清单矛盾（均不恢复 AITDE / DSH / 报告中心）；
- ✅ 不与 10-07 评估教训矛盾（本规格明示不建 Mission/Contract/Scenario/Oracle 平行实体）；
- ⚠️ **ADR-0021 AITDE V3.1 统一执行"已 superseded"状态**与本规格 §24 ADR-AIQE-003 "不引入独立 Workflow Engine" 一致 ✅；
- ⚠️ ADR-0027/0028/0029 Local-first AI / Shadow Mode / Routing **当前状态 active 但对应代码（ai_gateway/）将在 P0-5 删除**——建议 batch-275 一并把这三个 ADR 标为 `superseded by 11 号方案 + 本规格 M-5`。记为 **后续处理**。

---

## 7. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 规格合并缺少现有代码对账 → 7 条 P0 落地阻塞 | 新增"规格合并清单"要求：合并类规格必须含 current-codebase-reconciliation 工件 | 待修 `.claude/skills/cameltv-agent-team/DEPARTMENTS.md` 的 Product 节；由 batch-275 顺便改 |
| 单一会话既写规格又评审导致 confirmation bias | 对**自己产出的规格**做评审时，必须在 QA 报告明示"评审者 = 规格作者"并把门槛拉严 | 已在本批 QA §5 风险列明，已落地 |
| 批次编号从 batch-206 直接跳到 batch-274 | 本地分支未同步 origin/main 最新批次号 | 不影响；本批编号正确 |
| AGPL 风险在 OSS 清单只有"法务评估后"模糊语 | §14 需加硬门禁"法务书面评估"而非软 PoC 门槛 | 已列为 M-16，由 batch-275 修 |
| TestPlan、ReportCenter、Dataset 删除后，13 号内部引用是否清理 | QA 核对 PASS（本规格不恢复） | 已验证 |

---

## 8. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 评审 2.5h / 实际 ~3h |
| 缺陷 | **P0 × 7** / P1 × 12 / P2 × 13 / 0 项 PASS |
| 返工次数 | 0（但自身是"13 号规格返工"的产物） |
| 根因分类 | **需求不清**（规格合并时未做现有代码对账）+ **外部依赖**（TestZeus AGPL / Benchmark 数据集 / 对象存储选型） |
| 下次避免 | 任何由"多份文档合并"而成的 proposal 必须附一份与当前仓库的对账表（含 models/services/routers/skills 四类），否则不进入门禁评审 |

---

## 9. 本批 C 条件（Open）

**本批不新增 C 条件**。改由 batch-275 的 Leader verdict 在修完 P0 后决定是否开 C275-x。

但预留如下待办作为 batch-275 的输入（不入 C-CONDITIONS.md，只记录在此）：

- [ ] 修 13 号 §4.7 加 version_task_run 对账
- [ ] 修 13 号 §4.8 加 execution_job_id 字段
- [ ] 修 13 号 §4.14 改为扩 environment
- [ ] 修 13 号 §4.19 + §0 P0-5 明示 ai_job/ai_shadow_run/ai_gateway_cache 一并删
- [ ] 修 13 号 §14 加 TestZeus AGPL 法务硬门禁
- [ ] 修 13 号 §4.12 加对象存储选型
- [ ] 修 13 号 §21 加 benchmark 数据集来源
- [ ] 完成后 13 号 frontmatter `status: proposal` → `active`，版本号 `v1.0-merged` → `v1.1-p0-fixed`

---

## 10. 用户总确认清单（Final Sign-off）

本批无 PR、无代码交付、无合并。用户仅需确认以下三件事：

1. ✅ **接受 Leader verdict = 修改后合入**，开 batch-275 承接 7 条 P0 修复？
2. ⬜ **延迟 batch-275**（优先清 §0 P0-1..5 的真实工作，先开 batch-277 TA-000）？
3. ⬜ **拒绝 verdict，另开 batch-274v2 重评**？

**推荐路径**：选择 1，batch-275 轻量批次只改 docs，不涉代码，1 天内可完；batch-275 合入后再启 batch-277 (P0-1..5 代码/运维清零)。

---

## 11. 关联工件索引

- PRD：[batch-274-aiqe-spec-review-prd-summary.md](batch-274-aiqe-spec-review-prd-summary.md)
- PM：[batch-274-aiqe-spec-review-pm-plan.md](batch-274-aiqe-spec-review-pm-plan.md)
- Design：[batch-274-aiqe-spec-review-design-spec.md](batch-274-aiqe-spec-review-design-spec.md)
- Dev：[batch-274-aiqe-spec-review-dev-plan.md](batch-274-aiqe-spec-review-dev-plan.md)
- QA：[batch-274-aiqe-spec-review-qa-report.md](batch-274-aiqe-spec-review-qa-report.md)
- 看板：[kanbans/DEV-batch-274-aiqe-spec-review.md](kanbans/DEV-batch-274-aiqe-spec-review.md)
- 评审对象：[docs/platform-refactor/13-ai-quality-agent-merged-spec.md](../docs/platform-refactor/13-ai-quality-agent-merged-spec.md)
- 参考对象：[docs/platform-refactor/12-ai-quality-agent-landing-plan.md](../docs/platform-refactor/12-ai-quality-agent-landing-plan.md)
