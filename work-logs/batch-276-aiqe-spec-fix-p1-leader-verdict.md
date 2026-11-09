# Batch 276 — AIQE Spec Fix P1：Leader Verdict

> **部门**：🎯 Leader
> **日期**：2026-11-09
> **输入**：PRD-lite + QA report + 修改后的 13 号规格 v1.2-p1-fixed
> **上游判决**：[batch-274 Leader verdict](batch-274-aiqe-spec-review-leader-verdict.md) §3（12 条 P1）

---

## 1. 判决

# ✅ APPROVED

**理由**：

- batch-274 verdict §3 列的 **12 条 P1 全部修完**，每条都有唯一落点 + `batch-276 M-X/D-X` 标记（见 QA 报告 §1 行号表）；
- 13 号规格 `version: v1.1-p0-fixed → v1.2-p1-fixed`，`status: active` 保持；顶部 banner 记录 12 条变更；
- 本批 6 个**技术判断**（D-1 方言拆分 / D-4 正则优先 / D-5 证据边界 / D-6 路由并存 / D-7 自实现资源锁 / M-20 分档）均有仓内代码事实支撑，不是拍脑袋：
  - `task_queue.py` 无 advisory lock（命中 0）、无独立 heartbeat 表；
  - `app/services/knowledge/sanitize.py` 已有生产在用的 9 类脱敏规则；
  - `lanhu_evidence_*` 已有 `project_id + doc_id + version_id` 维度；
  - `frontend/src/router/index.tsx` 已有 3 条 `version-tasks`、0 条 `runs`；
- **无代码 / 迁移 / CI 改动**，风险 ≈ 0；附带修复 4 处（2 处表格渲染、1 处 batch-275 残留、1 处表述）；
- QA 门禁全绿：表格 61/0、锚点 201 + 链接 29/0、54 条 TA 全覆盖优先级档。

---

## 2. 合入路径

```text
feature/batch-276-aiqe-spec-fix-p1（worktree: DeepSeek_Harness-batch-276-aiqe-spec-fix-p1）
    │  13 号 v1.2-p1-fixed + PR 模板护栏 + 4 件工件
    ▼
Draft PR → main（required checks：AI/Git 交付策略 + 后端/前端两路跳过仍返回结果）
    │  audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness -RequireSuccessfulChecks
    ▼
squash merge → main
    │
    ▼
batch-277（完整批次）：§0 P0-1..5 真实清零
```

**批次数推进**：batch-276 完成后，M0 阶段只剩 **batch-277（P0 清零）** 与 **batch-278（TA-001 baseline）**。

---

## 3. 关于 12 条 P1 的裁剪结论（给 batch-277+ 的输入）

| 条目 | 对后续批次的可执行约束 |
|------|----------------------|
| M-6 | 任何 Run 子表 PR 若新增 `project_id` 列 → **Block**；查询评审看是否 join `test_runs` |
| M-12 | PR 模板已加"架构护栏"节；batch-277 起的已合并 PR 不追溯，新 PR 逐条检查 |
| M-13 | TA-015 的 capability registry 必须实现 `ui.overlay.observe/control` 两项；TA-023 检测器按能力派发 |
| M-15 | TA-027.3 的规则 CRUD 必须实现"续期 = 新建行"；禁止 UPDATE 旧行 `effective_until` |
| M-18 | TA-016..018 任一 PoC 失败按回退列执行，不得停工等决策 |
| M-19 | 若团队 ≤3 人，直接采用 §23 放大线重排，不重新论证 |
| M-20 | 每批开工前用"优先级档"裁剪范围，MVP 未全绿不得接 V1.1+ |
| D-1 | TA-006 必过"SQLite + PG 各 1000 事件"双端验收 |
| D-4 | TA-007 的 `app/aiqe/redaction/rules.yaml` 与 knowledge sanitize 共用规则；改规则必须带 fixture |
| D-5 | TA-007 的 EvidenceBundle 必须能并集展示 Run 证据 + 蓝湖证据引用 |
| D-6 | TA-008 只做 `/runs` 一套组件，`/version-tasks/:taskId` 迁移复用 |
| D-7 | TA-001 审计必须给出 `task_queue.py` 行号结论；TA-010.3 落到 `resource_lock.py` |

---

## 4. 本批修订记录

| 修订 | 内容 |
|------|------|
| v1 → v1.1-p0-fixed | batch-275：7 条 P0（M-2/3/4/5/16 + D-3/9） |
| v1.1 → v1.2-p1-fixed | batch-276：12 条 P1（M-6/12/13/15/18/19/20 + D-1/4/5/6/7） |
| 待办 | 13 条 P2（batch-274 QA §3.3）由后续批次承接；§0 P0-1..5 由 batch-277 清零 |

---

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 12 条 P1 分布在 10 个章节，单条修改小但数量多，最易漏的是"表级字段归属"（M-6 初稿把 `defects` 误列为无 `project_id`） | 建立"写隔离规则前先 grep 全部字段表 `project_id`"的检查动作 | 本 verdict §3 + QA 复盘卡 |
| 表格内裸竖线破坏渲染（本批发现 2 处历史遗留） | 文档批次 QA 必跑表格列数脚本 | QA 复盘卡"下次避免"已记录，可复用脚本 |
| PR 模板变更会落在 worktree scope 之外 | 批次开始时把 `.github` 一并声明进 scope，并在 PRD-lite 说明原因 | 本批 PRD-lite 头部"声明范围" |

---

## 6. 知识审计

### 6.1 本批可入 KB 的知识

| 知识 | 类型 | 入库建议 |
|------|------|---------|
| "跨表 project 隔离必须逐表 grep `project_id`，不能按'子表'直觉归类" | 设计规范 | 走 `ingest_platform_knowledge`（type=`platform_knowledge`） |
| "噪音规则续期用新建行 + 自引用，旧行不可变" | 架构模式 | 同上 |
| "PoC 矩阵必须带失败回退列，回退不算失败" | 流程实践 | 同上 |
| "DB 方言差异只允许收敛在 repository / resource_lock / seq 三处" | 架构模式 | 同上 |

**建议**：在 batch-277 合入时由 Dev 统一出一份 KB 入库草稿（含 batch-274/275/276 三批）。

### 6.2 与 KB 已有知识的矛盾检查

- ✅ 不与 ADR-0014 / 0015 / 0019 / 0020 矛盾；
- ✅ 不与 11 号方案 §2 删除清单矛盾；
- ✅ 不与 §2 不做清单（不恢复 AITDE / DSH / 报告中心）矛盾；M-12 反而把"禁止 AITDE 翻版"变成 PR 门禁；
- ✅ 与 batch-274 verdict §3 / batch-275 verdict 一致（本批是它们的落地）。

---

## 7. 本批无新增 C 条件

batch-276 不新增 `C-CONDITIONS.md` 条目。13 条 P2 仍按 batch-274 QA §3.3 由后续批次处理；§0 P0-1..5 由 batch-277 承接。

---

## 8. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 2 天（14 号排期 W0）/ 实际 ≈ 1.5h |
| 缺陷 | 本批新增 0 P0 / 0 P1；发现并修 4 处历史小缺陷（2 渲染 + 1 残留 + 1 表述） |
| 返工次数 | 2（M-6 字段归属、附录 C 标题层级/锚点） |
| 根因分类 | 文档工程（跨章节一致性靠人工核对；表格裸竖线无 CI 检查） |
| 下次避免 | 文档批次固定三步：① 表格列数脚本 ② 锚点/链接脚本 ③ 跨表字段 grep |

---

## 9. 合入前核对（Dev 执行，已全部完成）

- [x] 工作树只有本批文件：13 号规格、`.github/pull_request_template.md`、`work-logs/batch-276-*` × 3、看板 × 1；
- [x] commit message 规范：`docs(batch-276): ...`；
- [x] Attribution 齐（Co-Authored-By 行）；
- [x] 13 号 `version: v1.2-p1-fixed` + banner；
- [x] QA / Leader / PRD-lite / 看板 四件工件齐；
- [x] 表格 / 锚点 / 链接校验 0 问题；
- [x] 推送后 PR 自动归入新 commits，CI 分类为 docs-only。

---

## 10. 关联工件

- PRD-lite：[batch-276-aiqe-spec-fix-p1-prd-lite.md](batch-276-aiqe-spec-fix-p1-prd-lite.md)
- QA：[batch-276-aiqe-spec-fix-p1-qa-report.md](batch-276-aiqe-spec-fix-p1-qa-report.md)
- 看板：[kanbans/DEV-batch-276-aiqe-spec-fix-p1.md](kanbans/DEV-batch-276-aiqe-spec-fix-p1.md)
- 修改对象：[docs/platform-refactor/13-ai-quality-agent-merged-spec.md](../docs/platform-refactor/13-ai-quality-agent-merged-spec.md) v1.2-p1-fixed
- 上游：[batch-274 Leader verdict](batch-274-aiqe-spec-review-leader-verdict.md) §3
- 排期：[docs/platform-refactor/14-aiqe-dev-schedule-and-dogfood-plan.md](../docs/platform-refactor/14-aiqe-dev-schedule-and-dogfood-plan.md) §4.1
