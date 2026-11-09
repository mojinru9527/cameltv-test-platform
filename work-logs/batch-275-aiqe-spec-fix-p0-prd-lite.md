# Batch 275 — AIQE Spec Fix P0：PRD-lite

> **部门**：🟦 Product（lite）
> **日期**：2026-11-09
> **Executor**：Claude Code
> **分支**：feature/ai-quality-agent-landing-plan（复用 PR #497，同 PR 追加提交）
> **批次模式**：**light**（docs-only 修 bug，只产 PRD-lite + QA + Leader + 看板）
> **mode 理由**：本批不引入新行为/新接口/新配置/新依赖；只修 docs 里的 7 条 P0 阻塞，status: proposal → active。

---

## 1. 问题陈述

batch-274 Leader verdict 对 13 号规格书出具"🟡 修改后合入"判决，列出 7 条 P0 必须修：

| M-ID | 位置 | 内容 |
|------|------|------|
| M-2 | §4.7 | `test_runs` vs `version_task_run.py` 未对账 |
| M-3 | §4.8 | `node_runs` 与 `execution_job.py / plan_execution_job.py` 关系不清 |
| M-4 | §4.14 | `target_environments` 与 `environment.py` 完全重复 |
| M-5 | §4.19 + §0 P0-5 | `ai_job / ai_shadow_run / ai_gateway_cache` 删除/保留未定 |
| M-16 | §14 | TestZeus AGPL 需加法务书面评估硬门禁 |
| D-3 | §4.12 | 对象存储选型未定 |
| D-9 | §21 | Benchmark 数据集来源未写 |

7 条不修完，开发按 13 号建表会和现有 `app/models/` 冲突。

## 2. 成功指标

| 指标 | 阈值 |
|------|------|
| 7 条 P0 全部改完 | 7/7 |
| 13 号 frontmatter `status: proposal` → `active` | 1 |
| 13 号 frontmatter `version: v1.0-merged` → `v1.1-p0-fixed` | 1 |
| 不引入新矛盾（内部一致性复核通过） | 0 处 |
| PR #497 所有 CI 保持绿 | 所有 required checks pass |

## 3. 用户决策已入库

| 决策点 | 选项 | 落地动作 |
|-------|------|---------|
| M-4 | **A. 扩字段（扩 environment.py）** | 删 §4.14 target_environments 新表；改为"§4.14 environment 扩字段"；全文相关引用（§4.7/§15.3/§17.1 等）改回 `environment_id` |
| D-3 | **C. 本地 FS（dev 默认，prod 待定）** | §4.12 明示 "dev: 本地文件系统；prod: 候选三选一（腾讯云 COS / MinIO / 本地 FS），由 TA-007 前业务 PoC 后定" |

## 4. 7 条 P0 处置方案

### Slice 1 — M-2：§4.7 加 version_task_run 对账

**位置**：13 号 §4.7 test_runs 字段表末尾加一段。

**新增内容**（节选）：

> **与现有 `version_task_run.py` 的关系**：
> 现有 `app/models/version_task_run.py` 承接"版本任务的一次执行"。本规格 `test_runs` 是**通用执行实例**，`version_task_run` 为其**派生场景**（source_type = `version_task` 的 `test_runs`）。
> 
> **迁移策略**（在 TA-001 代码审计后定案）：
> - 候选 A：废弃 `version_task_run`，将其字段 ALTER 并入 `test_runs`（source_type 区分）；
> - 候选 B：保留 `version_task_run` 作为视图/关联表，`test_runs` 为底层事实；
> - TA-001 产出 `docs/aiqe/baseline.md` 后在 M1 开工前决定。
> 
> **本规格的 `test_runs` 字段表以通用执行实例为准**，开发时**不得**创建与 `version_task_run` 字段完全重复的新表。

### Slice 2 — M-3：§4.8 加 execution_job_id 字段

**位置**：13 号 §4.8 node_runs 字段表增加一行。

**新增字段**：

| 字段 | 类型 | 说明 |
|-----|------|------|
| execution_job_id | FK execution_jobs | **nullable**；一对一关联调度派发工作单元（现有 `app/models/execution_job.py`） |

**并在字段表下方加一段**：

> **与现有 `execution_job.py / plan_execution_job.py` 的关系**：
> - `execution_jobs` 是**派发工作单元**（现有）：承载"节点侧要做什么、给哪个 worker"；
> - `node_runs` 是**DAG 节点执行事实**（本规格新增）：承载"这个节点现在跑到哪一步、结果是什么"；
> - 二者 **1:1** 绑定。创建 `node_runs` 时若尚未派发，`execution_job_id = null`；派发后回填。
> - `plan_execution_job` 是旧的"测试计划执行派发"，在 batch-277 清 P0 时核实是否属于 11 号方案已删的 `plan_execution_queue` 老队列。若是 → 一并删除；若否 → 作为 `execution_job` 的历史别名保留，不参与新 DAG。

### Slice 3 — M-4：§4.14 删 target_environments 新表，改为扩 environment.py

**位置**：13 号 §4.14 整节重写。

**旧内容**：新建 `target_environments` 表（与 environment.py 字段完全重复）。

**新内容**（节选）：

> ### 4.14 `environments`（**扩现有 `environment.py`**，不新建表）
> 
> **扩展规则**：在现有 `app/models/environment.py` 基础上新增以下字段，不建平行表。
> 
> | 字段 | 类型 | 说明 |
> |-----|------|------|
> | base_urls_json | JSON | `{admin, consumer_web, consumer_h5, api}` 多端 base URL |
> | data_sources_json | JSON | DB/Redis/MongoDB/Kafka 连接 slot（env var ref） |
> | build_check_endpoint | varchar(500) | 健康检查 URL |
> | allowed_actions | enum | `read_only / limited_write / full_write` |
> 
> 现有 Environment 的所有字段（name / project_id / 鉴权 slot 等）保留不变。本规格全文的 `target_environment_id` 引用改为 `environment_id`。
> 
> **迁移策略**（Alembic）：
> - `op.add_column('environments', sa.Column('base_urls_json', JSON, nullable=True))` × 4 字段；
> - 老数据 base_urls_json 从 `name` 推断或人工补；
> - `allowed_actions` 默认 `read_only`，production 环境显式升为 `limited_write`。

**并在 §4.7 / §15.3 / §17.1 相关引用处改 `target_environment_id` → `environment_id`**。

### Slice 4 — M-5：§4.19 + §0 P0-5 明示 ai_job / ai_shadow_run / ai_gateway_cache 一并删

**位置**：
1. §0 P0-5 表格 "开发要做的事" 列扩写：

> 删除 `app/services/ai_gateway/` 目录 + `app/models/ai_job.py` + `app/models/ai_shadow_run.py` + `app/models/ai_gateway_cache.py`，以及 Alembic 对应迁移；更新 `docs/ai/local-ai-agent.md` 与 `scripts/ai_agent/README.md`；ADR-0027/0028/0029 标 `superseded by 11 号方案 + batch-275 P0 清理`。

**验收证据**列扩写：

> `rg "ai_gateway|AiJob|AiShadowRun|AiGatewayCache"` 命中 0；相关 Alembic revision 已 downgrade 并删除；3 个 ADR 状态更新；文档口径更新。

2. §4.19 `agent_executions` 表上方加一段：

> **与已删 `ai_job / ai_shadow_run / ai_gateway_cache` 的关系**：
> 这三张表承载的"shadow run 对比 / gateway cache / job 分发"等能力**在 11 号简化批次 + batch-277 P0-5 一并删除**。`agent_executions` 单独承载所有 Agent 调用审计，**不恢复**旧字段。旧数据如需追溯归档至 `work-logs/platform-simplification-production-eval-20261007.md`。

### Slice 5 — M-16：§14 加 TestZeus AGPL 法务硬门禁

**位置**：
1. §14.1 OSS 推荐复用矩阵的 TestZeus Hercules 行"初步建议"列改写：

> ⚠️ **硬门禁**：采用 TestZeus 前**必须经法务书面评估**（AGPL-3.0 对闭源商业分发 / SaaS 网络服务源码披露义务）；评估不通过或 SaaS 化计划在 1 年内触发 → **直接从候选清单剔除**，不走 PoC。评估通过且仅在完全隔离的独立服务中使用时方可 PoC。

2. §14.4 PoC 选择矩阵 TestZeus 行"通过条件"改写：

> **先决条件**：法务书面评估完成且结论为"可采"。满足后 PoC 通过条件为：AGPL 隔离部署方案成立 + 依赖安全 + Playwright 兼容 + 输出映射通过。**法务未通过前不启动 PoC**。

### Slice 6 — D-3：§4.12 加对象存储选型

**位置**：13 号 §4.12 run_artifacts 表下方加一段。

**新增内容**：

> **对象存储选型**：
> - **dev 环境**：**本地文件系统**（`storage_uri = file://<data-dir>/artifacts/<sha256-prefix>/<sha256>`），默认目录 `test-platform-v2/backend/storage/artifacts/`；
> - **test 环境**：同 dev，或走 docker volume；
> - **production 环境**：候选三选一，由 TA-007 开工前业务 PoC 后定：
>   - **A. 腾讯云 COS**（统一服务商；Server-Side Encryption + 签名 URL）；
>   - **B. MinIO 自托管**（制品不出站 + 省钱；需多维护一个服务）；
>   - **C. 本地 FS**（延续 dev 做法；dogfood 跟不上生产）。
> 
> **TA-007 的 driver 接口必须屏蔽后端差异**（`ArtifactStorageBackend` 抽象）；选型变更不影响业务代码。

### Slice 7 — D-9：§21 加 benchmark 数据集来源

**位置**：13 号 §21 顶部加一段。

**新增内容**：

> ### 21.0 数据集准备（**TA-001 并行子任务，不是 Agent 开工时才找**）
> 
> **强制规则**：Agent 评估集的数据收集**在 batch-278 TA-001 代码审计阶段并行启动**，不能等 M3 开工才临时拼凑。否则 Agent 开发会卡在"schema 跑通但没真实样本"阶段。
> 
> **A1 Requirement 的 30 份需求**：
> - 从 `app/models/requirement.py` 现有数据抽样 15 份（覆盖清晰/歧义/冲突/非功能各类）；
> - 从 `lanhu_evidence` 包抽 10 份（含原型）；
> - 从历史 batch PRD 抽 5 份（test-platform-v2/work-logs/batch-*-prd-*.md）。
> 
> **A2 Test Design 的 50 份 PRD**：
> - 从 `app/models/test_case.py` + `test_case_version.py` 已采纳用例中抽样 50 份作为"PRD → case"对照；
> - 必须已有人工审核的 case 作为"黄金答案"。
> 
> **A4 Triage 的 100 标注失败样本**：
> - 从 `app/models/defect.py` 历史真实缺陷 × 50 条（含修复 commit、分类标签）；
> - 从 batch-274 评审期间收集的 M-* + D-* 条目 × 20 条（documentation defect）；
> - 从 M4 Dogfood 7 类注入 + 对照实验 × 30 条（本 session 产生）。
> 
> **A5 Impact 的 20 PR**：
> - 从 origin/main 近 100 PR 中挑 20 个带明确回归记录的（如 batch-240..273 的 PR）；
> - 必须已有"本 PR 应跑哪些用例"的人工标签。
> 
> **数据集版本锁**：所有 benchmark 存 `test-platform-v2/backend/app/aiqe/agents/evals/<agent_key>/`，每份样本 YAML + schema_version + 来源 ref。
> 
> **数据集准备进度**（每周在 kanban 跟踪）：
> - batch-278 结束时（W2）：A1 已 30/30，A2 已 25/50，A4 已 50/100；
> - M2 结束时（W7）：A1 已 30/30，A2 已 50/50，A4 已 100/100，A5 已 20/20；
> - M3 开工（W8）：100% 就绪。

### Slice 8 — status + version 更新

**位置**：13 号 frontmatter。

```yaml
status: active            # 从 proposal 改
version: "v1.1-p0-fixed"  # 从 spec-v1.0-merged 改
last_reviewed: "2026-11-09"
```

同时在 13 号顶部"本文合并了..."段下方加一行：

> **v1.1-p0-fixed**：batch-275 修完 batch-274 Leader verdict 的 7 条 P0（M-2/M-3/M-4/M-5/M-16/D-3/D-9）。剩余 12 条 P1 由 batch-276 承接。

## 5. 非目标

- **不修 P1 / P2**（分别由 batch-276 和后续批次承接）；
- **不改任何代码**（真实代码清零走 batch-277）；
- **不开新 PR**（复用 #497）；
- **不改 Alembic / 迁移** → docs-only。

## 6. DoD（本批）

- [ ] 8 Slice 全部 ✅；
- [ ] 13 号 v1.1-p0-fixed active；
- [ ] QA 一致性复核（内部交叉引用 + 与 batch-274 verdict 对账）；
- [ ] Leader APPROVED；
- [ ] PR #497 保持 CI 绿；
- [ ] 完成后用户总确认 → PR 转 Ready for review。
