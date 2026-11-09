# Batch 276 — AIQE Spec Fix P1：PRD-lite

> **部门**：🟦 Product（lite）
> **日期**：2026-11-09
> **Executor**：DeepSeek Harness（workflow: agent-team，worktree `DeepSeek_Harness-batch-276-aiqe-spec-fix-p1`）
> **分支**：feature/batch-276-aiqe-spec-fix-p1（从 origin/main `9d851ed38` 切出）
> **批次模式**：**light**（docs-only，只产 PRD-lite + QA + Leader + 看板）
> **声明范围（worktree scope）**：`docs,work-logs,.github` —— `.github/pull_request_template.md` 是 M-12 "PR 模板强制问答"的唯一可执行落点，故纳入声明范围。
> **mode 理由**：不引入新行为 / 新接口 / 新配置 / 新依赖 / 数据库变更；只修 13 号规格的 12 条 P1 + 1 条 PR 模板护栏 + 3 处渲染/残留缺陷。

---

## 1. 问题陈述

batch-274 Leader verdict §3 对 13 号规格列出 **12 条 P1**；batch-275 只修了 7 条 P0（v1.1-p0-fixed），12 条 P1 仍未落地。逐条不修的后果：

| ID | 不修的后果 |
|----|-----------|
| M-6 | Run 子表 `project_id` 口径散落（§4 一句话 vs 各表实际字段），开发者会重复加列或在查询里漏过滤 |
| M-12 | 新建"带 checksum + approval_status"的实体没有 PR 守卫，AITDE Scenario 翻版会静默复活 |
| M-13 | `UI_OVERLAY` 干扰检测无法按 Driver 能力启停，纯 API Driver 会被误派发 UI 任务 |
| M-15 | 噪音规则 90 天到期只能重建，审计链断裂；没有续期语义 |
| M-18 | 4 个 OSS PoC 没有失败回退方案，PoC 一挂就阻塞 M2 |
| M-19 | 只有 5-6 人基准工期，2-3 人团队无法对排期 |
| M-20 | 54 条 TA 没有优先级档，无法裁剪出 MVP |
| D-1 | `seq` 分配只写了 Postgres 方案，SQLite 开发环境直接撞号 |
| D-4 | 脱敏库三选一未定，TA-007 开工即卡 |
| D-5 | 蓝湖证据与 Run 证据边界不清，会重复建表或复制证据 |
| D-6 | `/version-tasks` 与 `/runs` 路由关系未决，前端会做两套详情页 |
| D-7 | 误以为 `task_queue.py` 已有 advisory lock + heartbeat 表，TA-010.3 会漏做资源锁 |

---

## 2. 成功指标

| 指标 | 阈值 | 结果 |
|------|------|:----:|
| 12 条 P1 全部落地且带 `batch-276 M-X/D-X` 标记 | 12/12 | ✅ |
| 13 号 frontmatter `version` | `v1.1-p0-fixed` → `v1.2-p1-fixed` | ✅ |
| §19 每条 TA 有优先级档（9 张表 / 54 行） | 54/54 | ✅ |
| Markdown 表格列数校验（新建 / 改动表格） | 0 问题（61 张表） | ✅ |
| 内部锚点 + 相对链接 | 0 断链（201 锚点 / 29 链接） | ✅ |
| PR 模板新增"架构护栏"节 | 1 处 | ✅ |
| 不引入新矛盾（与 §2 不做清单 / §24 ADR / 11 号方案对账） | 0 处 | ✅ |
| PR required checks | 全绿后 squash merge | ⏳ |

---

## 3. 关键决策（本批自行决策，不涉用户业务决策）

| ID | 决策 | 依据 |
|----|------|------|
| D-1 | SQLite 用 `run_seq_counters` 计数器行自增（单写者天然串行）+ `(run_id, seq)` 唯一索引兜底；Postgres 用 `pg_advisory_xact_lock` + 计数器行 `UPDATE ... RETURNING` | `task_queue.py` 无 advisory lock；SQLite 无 advisory lock 能力 |
| D-4 | 默认**自写正则引擎**（抽取 `app/services/knowledge/sanitize.py` 规则）+ YAML 规则表；`presidio` 留 V1.1+ 且需 ADR / OSS 准入 | 仓内已有生产在用的 sanitize 正则；presidio 带 spacy 模型，镜像与启动成本高 |
| D-5 | `run_artifacts` 加 `linked_evidence_type + linked_evidence_id` 两个可空列；蓝湖证据与 Run 证据**互不迁移** | 现有 `lanhu_evidence_*` 已有 `project_id / doc_id / version_id` 维度，复制会双写 |
| D-6 | 保留 `/version-tasks` 业务入口 + 新增 `/runs` 通用列表；详情组件只写一份 | `frontend/src/router/index.tsx` 已挂 `version-tasks/*`，无 `runs` |
| D-7 | `TA-010.3` 自实现 `resource_lock.py`；**不得**复用队列认领锁 | 预检：`app/core/task_queue.py` 只有 `atomic_claim` + `reap_stale`，无 advisory lock / 无独立 heartbeat 表 |
| M-20 | 优先级档按 Phase 划分：Phase 0-2 = `MVP`（19 条）/ Phase 3-6 = `V1`（25 条）/ Phase 7 + 预留 = `V1.1+`（10 条） | 与 §23 "MVP = M0-M2" 对齐 |

---

## 4. 12 条 P1 处置（Slice 1-12）

| # | ID | 位置（v1.2 行号） | 落地内容 |
|---|----|------------------|---------|
| 1 | M-6 | §4 关键规则 L261 + 附录 B.1 L3069 | Run 子表不存 `project_id`、继承 `run.project_id`；`test_cases` 经 `test_scenarios`；9 类全局/半全局表逐张明示；禁止冗余列 |
| 2 | M-12 | §24 ADR-AIQE-008 L2997 + 强制问答 L3004 + PR 模板 | ADR 行加护栏；3 问强制问答（AITDE 翻版自检）；`.github/pull_request_template.md` 新增"架构护栏"节 |
| 3 | M-13 | §11.2 L1528 + L1533 | `UI_OVERLAY` 加 `requires_ui_surface: true`；`ui.overlay.observe / ui.overlay.control` 两条独立 capability；缺 observe 记 `unsupported`，缺 control 只观察 |
| 4 | M-15 | §4.20 L788/L790 + §11.9 L1700 | 单次窗口 ≤ 90 天；Owner 显式续期 = 新建行 + `renewal_of_rule_id` 指向旧行；到期未续期自动失效并计入 `quarantine_expiry_overdue_count` |
| 5 | M-18 | §14.4 L1945 | PoC 矩阵加"失败回退方案"列；4 个 PoC 各给回退（Playwright / 纯 Playwright / mock+HTTP Driver / 删除候选）；"回退不阻塞 M2" |
| 6 | M-19 | §23 L2969 | 团队规模换算表（M0-M6 + MVP 16-20 周 / V1 32-40 周 ≈ ×2）；M0 只延长不缩短 |
| 7 | M-20 | §19 L2599-2602 | 9 张 TA 表全部加"优先级档"列（MVP 19 / V1 25 / V1.1+ 10）；"MVP 未全绿不得启动 V1.1+" |
| 8 | D-1 | §8.3.1 L1209 + 附录 C L3086 | 按方言拆 seq 分配 + 唯一索引兜底；附录 C 列 9 项 DB 兼容差异（主键/时间/JSON/行锁/咨询锁/队列/seq/迁移/降级） |
| 9 | D-4 | §16.2 L2165 | 默认正则引擎 + `app/aiqe/redaction/rules.yaml`（schema_version）+ `RedactionEngine` 接口；presidio 为 V1.1+ 升级路径；明确不选 faker 类库 |
| 10 | D-5 | §4.12 L548/L563 | 加 `linked_evidence_type / linked_evidence_id`；边界 5 条（互不迁移 / 各自权限 / 并集查询 / TA-007 验收） |
| 11 | D-6 | §18.2 L2488 | 保留 `/version-tasks`，新增 `/runs`、`/runs/:runId`、`/runs/:runId/compare`；组件复用；导航去重 |
| 12 | D-7 | §6.4 L1020 | 记录 `task_queue.py` 预检结论（无 advisory lock / 无 heartbeat 表）；TA-001 复核 + TA-010.3 自实现；队列锁 ≠ 资源锁 |

### 4.1 附带修复（同文件内，QA 发现）

| 位置 | 问题 | 处置 |
|------|------|------|
| §4.1 实体图 | `TargetEnvironment` 残留（batch-275 M-4 已删该表） | 改为 `Environment (扩展现有 environment 表)` |
| §4.5 `source_json` | 行内 `"ai" \| "human"` 的竖线未转义，表格列数 3→4 渲染错位 | 转义为 `\|` |
| §4.13 `config_json` | `locale` 与 `timezone` 之间用裸竖线，表格列数 3→4 | 改为 `locale 与 timezone` |
| §4.19 | "不加 project_id 不行" 表述不清 | 改为"全局表：project_id nullable…见附录 B.1" |

---

## 5. 非目标

- **不改任何代码 / Alembic / CI workflow**（batch-277 做真实代码与运维清零）；
- **不修 13 条 P2**（batch-274 QA report §3.3，后续批次）；
- **不做 TA-001 真实代码审计**（batch-278 产出 `docs/aiqe/baseline.md`）；
- **不动 14 号排期文档**（批次状态由看板与 verdict 记录，与 batch-275 做法一致）。

---

## 6. DoD

- [x] 12/12 P1 落地，每处带 `batch-276 M-X/D-X` 标记；
- [x] `version: v1.2-p1-fixed` + banner 变更日志；
- [x] PR 模板"架构护栏"节；
- [x] 表格 / 锚点 / 相对链接校验 0 问题；
- [x] QA 报告 + Leader verdict + 看板（本批四件）；
- [ ] PR required checks 全绿后 squash merge 到 main。
