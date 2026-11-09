# Batch 274 — AIQE Spec Review：Dev Plan（落地就绪度审计）

> **部门**：💻 Dev
> **日期**：2026-11-09
> **关联 Design**：[batch-274-aiqe-spec-review-design-spec.md](batch-274-aiqe-spec-review-design-spec.md)
> **本批特殊**：**无代码交付**。Dev 的产出是"按 13 号规格开工，开发会卡在哪里"的审计。

---

## 1. 立场

Dev 部门代表"真正按规格写代码的人"发言。读 13 号 2899 行后，我回答一个问题：

> **如果 Phase 1 的 TA-005 ~ TA-008 今天就开工，开发会卡在什么地方？**

---

## 2. 开工前 必须有的输入（Readiness Gate）

| 输入 | 现状 | 是否就绪 |
|------|------|:-------:|
| §0 P0-1..5 已清零 | 未开工 | ❌ |
| TA-001 代码审计产物 `docs/aiqe/baseline.md` | 未产出 | ❌ |
| TA-001.5 CI 守卫脚本 `scripts/ci/check-p0-ready.ps1` | 未产出 | ❌ |
| TA-002 OSS SBOM `docs/aiqe/oss-adoption-register.md` | 未产出 | ❌ |
| TA-003 Test 环境就绪 | 部分（C205-2 超时配置已改，部署未验证） | ⚠️ |
| TA-004 模型映射表 `docs/aiqe/model-mapping.md` | 未产出 | ❌ |
| §4 M-2/3/4/5（P0 冲突）在规格里有明示处置方案 | 未处置 | ❌ |
| M-16 TestZeus AGPL 法务评估 | 未做 | ❌ |

**结论**：**8 项全未就绪**。按 13 号规格直接开 TA-005 会在前两天内撞墙。

---

## 3. 按 TA 编号逐条审计"开工即卡点"

### Phase 1：TA-005 Run 模型 + 状态机

**规格要求**：新建 `test_runs` + Alembic 迁移 + `services/run_state.py::transition()`。

**实际会卡的地方**：

1. ⚠️ **M-2 未解决**：现有 `app/models/version_task_run.py` 已承担"一次执行实例"。开发会疑问：
   - 新建 `test_runs` 还是扩 `version_task_run`？
   - 如果新建，版本任务怎么关联？
   - 如果扩，表名是否改为 `test_runs`（破坏兼容）？
2. ⚠️ **M-3 未解决**：现有 `execution_job.py` 的生命周期与 `node_runs` 关系？
3. ⚠️ **M-7/M-8/M-9/M-10 未决**：状态机漏边 + typo + waiting_reason 字段——写 transition() 时要查规格补细节。

**开发实际卡点 → 必须先回合 Design**，Loop 1 次 ≥ 4 小时。

### Phase 1：TA-006 Run Event Collector（Outbox）

**规格要求**：新建 `run_events + event_outbox` 两张表，同事务写。

**实际会卡的地方**：

1. ⚠️ **project_id 问题（M-6）**：事件表要不要 project_id？如果继承 run 的，查询时要 join；如果独立带，冗余但查询快。规格没说。
2. ⚠️ **seq 生成策略**：§8.3 伪码用 "SELECT ... FOR UPDATE 最大 seq +1 或 advisory lock"。Postgres 和 SQLite 行为不同（SQLite WAL 下 advisory lock 不存在）。规格附录没给兼容方案。记为 **D-1**。
3. ⚠️ **Redis PubSub 可选依赖**：§8.3 提到"SSE / Redis PubSub 由 outbox dispatcher 推送"。Redis 当前没有在 docker-compose 里？需核对。记为 **D-2**。

**开发实际卡点**：D-1 和 D-2 需要在实施前决定，不然代码写两套（SQLite 兼容和 Postgres 优化）。

### Phase 1：TA-007 Artifact Manager

**规格要求**：对象存储适配 + sha256 + 脱敏 + 签名 URL。

**实际会卡的地方**：

1. ⚠️ **对象存储选型未定**：规格没说用 S3 / MinIO / 本地文件系统。生产已上腾讯云，是否走 COS？记为 **D-3**。
2. ⚠️ **redaction_status 的实现**：§4.12 定义了枚举，但脱敏规则（§16.2）只说"手机号/身份证/银行卡/token/密码"——具体正则 or 库？规格没给。记为 **D-4**。
3. ⚠️ **lanhu_evidence.py 的角色**：§3.1 对账说"lanhu_evidence 继续承担蓝湖专项"，但没说 `run_artifacts` 和 `lanhu_evidence` 的数据迁移/共存策略。记为 **D-5**。

### Phase 1：TA-008 React Run Console MVP

**规格要求**：`/runs` 列表 + `/runs/:id` 详情 + SSE `useRunEvents()`。

**实际会卡的地方**：

1. ⚠️ **路由冲突**：当前 `frontend/src/pages/version-tasks/[taskId].tsx` 已经是 Run 详情页。新建 `/runs/:id` 还是复用 version-tasks？记为 **D-6**。
2. ⚠️ **EvidenceReplay 通用组件**：12 号 §4.6 提过要抽；13 号 §18.2 列了目录；但组件 contract（props shape）没定。
3. ⚠️ **SSE 后端未实现前，前端只能 polling**：§8.5 `useRunEvents` 说"超过 N 次重连 → 切轮询"，但 N 和 backoff 没给默认值。

### Phase 2：TA-009 ~ TA-015

- TA-009 Workflow Validator 依赖 §6.2 的 7 条校验规则，规格明确，可直接实现；
- TA-010 DAG Scheduler 依赖 fencing token 实现，§6.4 说"复用 task_queue.py 的 Postgres advisory lock + heartbeat 表"——**现有 task_queue.py 是否有这个？需 TA-001 审计产出后验证**。记为 **D-7**。
- TA-014 DB Read-only Driver 要"SQL Template 白名单"——Template 的存储位置（DB 表 or yaml？）规格没定。记为 **D-8**。

### Phase 3：TA-016 ~ TA-021 Agent 系列

- TA-019/020/021 的 benchmark 数据集（§21）**现在还没有**，Agent 开发只能跑 schema 校验不能验收。记为 **D-9**。
- TA-017 TesterArmy e2e Adapter 假设 node 能装 Node.js runtime。当前 `cameltv-node` 是 Python；增加 Node.js 运行时有空间/权限影响。记为 **D-10**。

### Phase 4：噪音治理

- TA-023 Interference Detectors 需要节点侧采集"浏览器崩溃/console error/network failed"。现有节点是否已具备？需 TA-001 产出后确认。记为 **D-11**。
- TA-024 A4 Triage Agent 的 100 标注失败样本（§21.4）→ 从哪里来？规格没说。建议从 `defects` 表历史数据 + evidence 构造。记为 **D-12**。

### Phase 5：跨端 + Learning + MCP

- TA-028 跨端矩阵 UI：现有前端是否有可复用的矩阵组件？需核对。
- TA-032 MCP Gateway：需要新增 `scripts/mcp-server/` 目录 + 独立进程 / 独立端口。与现有 `knowledge-mcp/` 共存策略？记为 **D-13**。

### Phase 6：硬化 + 生产试点

- TA-033 压测基线：无基准数据。
- TA-034 Sports 纵向验收：依赖 `cameltv-sports.adapter.yaml` **完整版**（§17.4 当前只有 api 1 platform），需先补。记为 **D-14**。

---

## 4. D 条目汇总（Dev 发现的"规格落地时才会暴露"的问题）

| D-ID | 位置 | 问题 | 严重度 |
|------|------|------|:-----:|
| D-1 | §8.3 | seq 生成在 SQLite vs Postgres 的兼容方案未给 | P1 |
| D-2 | §8.3 | Redis PubSub 当前未在 compose 中 | P2 |
| D-3 | §4.12 + §7 TA-007 | 对象存储选型未定（S3/MinIO/腾讯云 COS/本地） | **P0** |
| D-4 | §16.2 | 脱敏具体正则/库未定 | P1 |
| D-5 | §4.12 | lanhu_evidence vs run_artifacts 共存/迁移策略未定 | P1 |
| D-6 | §18.2 | 前端 `/runs` 新路由 vs 复用 version-tasks 未决 | P1 |
| D-7 | §6.4 | task_queue.py advisory lock heartbeat 实现需验证 | P1 |
| D-8 | §16.3 | SQL Template 存储位置未定 | P1 |
| D-9 | §21 | Benchmark 数据集从哪来 | **P0** |
| D-10 | TA-017 | cameltv-node 需加 Node.js runtime 的影响 | P2 |
| D-11 | TA-023 | 现有节点 Interference 采集能力需验证 | P1 |
| D-12 | §21.4 | A4 Triage 的 100 标注样本来源 | P1 |
| D-13 | TA-032 | 新 MCP Gateway 与 knowledge-mcp 共存策略 | P2 |
| D-14 | TA-034 | cameltv-sports adapter 完整版需先补 | P1 |

**Dev 判定**：
- **P0 条目 2 个**（D-3, D-9）
- 合并 Design 的 M-P0 条目（M-2, M-3, M-4, M-5, M-16）= 共 **7 个 P0** 必须在 Phase 1 开工前有决策。

---

## 5. KB 检索引用（Dev 开工前置）

| 检索项 | 发现 | 本批处理 |
|-------|------|---------|
| ADR-0019 task_queue 单队列 + soft_delete | 已采纳 | 13 号 §6.4 已承接 ✅ |
| ADR-0020 不加 OS-level sandbox | 已采纳 | 13 号 §3.1 H1-H5 承接 ✅ |
| Batch 190 DSH AgentTeams 迁移 | 已合入 | 13 号 §10 不再依赖 DSH Agent 队列 ✅ |
| Batch 258 B1 ExecutionJob + cameltv-node | 已合入 | 13 号 §7 建立在此之上 ✅ |
| Batch 268 复用命中率埋点 | 已合入 | 13 号 §10.3 三阶段计划生成管线 **未显式关联** reuse_metrics —— 记为 **D-15** |
| Batch 269 版本任务 ⑦ 复用数字自产 | 已合入 | 13 号 §4.19 Learning 需与 reuse_metrics_service 联通 —— 记为 **D-16** |

补：

| D-ID | 位置 | 问题 | 严重度 |
|------|------|------|:-----:|
| D-15 | §10.3 | 三阶段计划生成未提 reuse hit rate 作为 stage3 覆盖率指标输入 | P2 |
| D-16 | §4.19 | Learning 与现有 reuse_metrics_service 的关系未定 | P2 |

---

## 6. 本批"编码"交付（无）

本批无代码交付（评审任务）。不涉及：

- Alembic 迁移
- 后端代码
- 前端代码
- 测试
- `scan-common-bugs.ps1`
- `scan-common-bugs.ps1`（单位扫描）

因此无 CI 门禁、无 typecheck、无 build。QA 部门改为做"规格一致性检查"。

---

## 7. Dev 结论

- 13 号规格**深度够、广度够、术语一致**，但有 **7 个 P0 落地阻塞**（M-2/3/4/5/16 + D-3/9）必须先解决；
- 另 **11 个 P1 + 5 个 P2** 可在开工后逐个随 TA 解决，但前提是 **TA-001 代码审计**产出 `docs/aiqe/baseline.md` 把所有现有同义实体写清楚。
- Dev 部门建议 Leader verdict = **"修改后合入"**：13 号本体保留，但必须补一节"**与现有代码的 P0 冲突处置**"覆盖 M-2/3/4/5；其余 P0/P1 走后续批次。
- 真正开发 TA-005 ~ TA-008 的**最早可行时间**是 P0 清零 + TA-001 审计产出 **之后 1 周**（粗估：下周末）。

---

## 8. 看板同步

- 本批 slice 全部 ✅（评审完成）；
- 开发实际开工要等 Leader verdict 后由用户裁决是否开 batch-275（docs-only 修 13 号）或 batch-275+（TA-000 P0 清零）。
