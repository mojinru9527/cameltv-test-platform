# Batch 276 — AIQE Spec Fix P1：QA Report

> **部门**：🔍 QA
> **日期**：2026-11-09
> **立场**：默认"需要改进"。docs-only 批次，门禁 = **规格一致性 + 代码事实核对 + 渲染/链接校验**（无 CI 硬门禁可替代）。
> **输入**：PRD-lite + 13 号规格 v1.2-p1-fixed

---

## 1. Slice 验收（12/12）

| # | ID | 落地位置（v1.2 行号） | 验收结论 |
|---|----|----------------------|---------|
| 1 | M-6 | §4 L261 + 附录 B.1 L3069-3078 | ✅ Run 子表继承 `run.project_id`；`test_cases` 经 `test_scenarios`；全局/半全局表 5 类逐条列出；写明"禁止加冗余 project_id 列" |
| 2 | M-12 | §24 L2997 + L3004-3010 + `.github/pull_request_template.md` | ✅ ADR 行加护栏；3 问强制问答；PR 模板新增"架构护栏（ADR-AIQE-008 / batch-276 M-12）"节 |
| 3 | M-13 | §11.2 L1528 + L1533-1540 | ✅ `requires_ui_surface: true` 入表；`ui.overlay.observe` / `ui.overlay.control` 两条独立 capability；缺 observe → 记 `unsupported` 不降级 PASS；缺 control → 只观察 |
| 4 | M-15 | §4.20 L788-790 + §11.9 L1700 | ✅ 单次窗口 ≤ 90 天；续期 = 新建行 + `renewal_of_rule_id`，旧行不动；到期未续期自动失效并计入 `quarantine_expiry_overdue_count` |
| 5 | M-18 | §14.4 L1945-1951 | ✅ 加"失败回退方案"列；4 个 PoC 各给回退；"回退不是失败、不阻塞 M2"；结论只允许三态 |
| 6 | M-19 | §23 L2969-2984 | ✅ 里程碑换换算表（M0-M6 + MVP 16-20 / V1 32-40 ≈ ×2）；"M0 只延长不缩短" |
| 7 | M-20 | §19 L2599-2602 及各 TA 表 | ✅ 9 张表全部加"优先级档"；54 行 = MVP 19 / V1 25 / V1.1+ 10；表头说明裁剪规则 |
| 8 | D-1 | §8.3.1 L1209-1218 + 附录 C L3086-3100 | ✅ 方言分表（SQLite 计数器自增 / PG advisory lock）；2 条"禁止"；TA-006 追加 1000 并发验收；附录 C 9 项兼容差异 |
| 9 | D-4 | §16.2 L2165-2173 | ✅ 默认正则引擎 + `app/aiqe/redaction/rules.yaml` + `RedactionEngine` 接口；presidio 为 V1.1+ 升级路径（需 ADR + §14.3）；明确不选 faker 类库 |
| 10 | D-5 | §4.12 L548-549 + L563-569 | ✅ 两个可空列；5 条边界（互不迁移 / 权限 / 并集 / TA-007 验收） |
| 11 | D-6 | §18.2 L2488-2495 | ✅ 保留 `/version-tasks`；新增 `/runs`、`/runs/:runId`、`/runs/:runId/compare`；组件只写一份；导航去重 |
| 12 | D-7 | §6.4 L1020-1024 | ✅ 预检结论（无 advisory lock / 无独立 heartbeat 表）+ TA-001 复核要求 + TA-010.3 自实现方案 + "队列锁 ≠ 资源锁" |

**附带修复（同文件，QA 发现）**：

| 位置 | 问题 | 处置 | 结论 |
|------|------|------|:----:|
| §4.1 实体图 | `TargetEnvironment` 残留（batch-275 M-4 已删表） | 改为 `Environment (扩展现有 environment 表)` | ✅ |
| §4.5 `source_json` | 行内 `"ai" \| "human"` 竖线未转义，表格 3→4 列 | 转义 `\|` | ✅ |
| §4.13 `config_json` | `locale` 与 `timezone` 之间裸竖线，表格 3→4 列 | 改为 `locale 与 timezone` | ✅ |
| §4.19 | "不加 project_id 不行" 表述含糊 | 改为"全局表：project_id nullable…见附录 B.1" | ✅ |

---

## 2. 一致性门禁

| 检查 | 方法 | 结果 |
|------|------|:----:|
| 12 条 P1 与 batch-274 Leader verdict §3 一一对应 | 逐条对账（M-6/12/13/15/18/19/20 + D-1/4/5/6/7） | ✅ 12/12 |
| Markdown 表格列数（全文件） | 脚本校验表头/分隔行/数据行 | ✅ 61 张表 0 问题 |
| 内部锚点 + 相对链接 | 脚本比对 GitHub slug + 文件存在性 | ✅ 201 锚点 / 29 链接 0 断链 |
| §19 优先级档覆盖 | 脚本按 Phase 打档并计数 | ✅ 9 表 54 行（MVP 19 / V1 25 / V1.1+ 10） |
| M-6 与真实字段表对账 | 逐表核对 `project_id` 是否存在 | ✅ `defects/test_runs/...` 有；`test_cases`、`regression_requests` 无（已按继承写） |
| 与 §2 不做清单 / §24 ADR / 11 号方案 §2 | 手工对账 | ✅ 无冲突；不恢复 AITDE / DSH / 报告中心 |
| 术语唯一口径 | 全文检索 | ✅ "Run 子表 / 全局表 / 优先级档" 只在 §4 + 附录 B.1 + §19 定义，其他章节引用 |
| 旧版本号残留 | `v1.1-p0-fixed` 全文检索 | ✅ 仅历史 banner / batch-275 工件 / 14 号示例（非本批范围） |

---

## 3. 代码事实核对（文档结论必须可复核）

| 文档结论 | 证据命令 | 结果 |
|---------|---------|------|
| `task_queue.py` 无 Postgres advisory lock | `Select-String app/core/task_queue.py -Pattern 'advisory'` | ✅ 命中 **0** |
| 无独立 heartbeat 表 | 同文件 `heartbeat` | ✅ 仅 docstring L58 提到 liveness 列；无 heartbeat 表定义 |
| 现有原语是 `atomic_claim` + `reap_stale` | `Select-String -Pattern '^def (atomic_claim\|reap_stale)'` | ✅ `atomic_claim` / `atomic_claim_by_id` / `reap_stale` |
| `sanitize.py` 已覆盖手机号/身份证/邮箱/JWT/鉴权头 | 读 `app/services/knowledge/sanitize.py` 头部与规则注释 | ✅ 9 类规则 + `MASK` |
| `lanhu_evidence_*` 有 project/doc/version 维度 | 读 `app/models/lanhu_evidence.py` | ✅ Job/Page/Asset/OcrBlock 四个模型，`project_id + doc_id + version_id` 索引 |
| 前端已有 `/version-tasks`、无 `/runs` | `Select-String frontend/src/router/index.tsx` | ✅ version-tasks 3 条；runs **0** 条 |

---

## 4. 未解决事项（合规遗留）

| 条目 | 承接 | 说明 |
|------|------|------|
| 13 条 P2 | 后续批次 | batch-274 QA §3.3，不阻断 |
| TA-001 真实代码审计 | **batch-278** | D-7 只做"预检"，最终结论要 TA-001 给文件行号 |
| §0 P0-1..5 代码/运维清零 | **batch-277** | 真实轮 Key / 备份演练 / 磁盘 / `/uitest` 剥离 / `ai_gateway` 删除 |
| 14 号示例 `contract_version: v1.1-p0-fixed` | 不修 | 示例常量，改了反而与 14 号"batch-275 产物"叙述不一致 |

---

## 5. 硬门禁（docs-only 替代门禁）

| 检查 | 命令 | 结果 |
|------|------|------|
| 改动均在 docs / .github 模板 / work-logs | `git status --short` | ✅ 3 类文件，0 代码 |
| 无 `.py / .ts / .tsx / .sql / Alembic` 改动 | `git diff --stat` | ✅ 0 |
| 无调试遗留 / 密钥 | `pwsh scripts/git/dev-gate.ps1 -SkipFrontend -SkipBackend`（G0 `scan-common-bugs`） | ✅ HARD **0** / WARN 340（扫描范围仅 backend `*.py` + frontend `*.ts(x)`，本批 0 代码改动 → 全部为存量；`GATE_RESULT=PASS_WITH_WARN`） |
| 文档保鲜（`scripts/check_doc_freshness.py`） | 13 号规格 0 告警、无过期；4 个新 work-logs 记 `no_frontmatter`，与 batch-274/275 工件一致（全仓存量 1659 份） | ✅ 无新增过期项 |
| PR required checks | push 后 `scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness -RequireSuccessfulChecks` | ⏳ 待执行 |
| 入 main 方式 | Draft PR → squash merge | ⏳ 待执行 |

---

## 6. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 2 天（14 号排期 W0）/ 实际 ≈ 1.5h |
| 缺陷 | 新增 P0 × 0 / P1 × 0；附带修复 4 处（2 处渲染、1 处 batch-275 残留、1 处表述） |
| 返工次数 | 2 次：① M-6 初稿把 `defects` 误列为"无 project_id 的 Run 子表"（实际 §4.17 有），对照字段表后修正；② 附录 C 初稿为 H3 且 TOC 锚点含批次后缀，改为 H2 + 无后缀标题 |
| 根因分类 | 文档工程（跨表 `project_id` 归属必须逐表核对，不能靠"子表"直觉） |
| 下次避免 | 写隔离/继承规则前先 `grep` 所有字段表的 `project_id`；新附录标题不带批次后缀，批次标记写正文 |

---

## 7. QA 判定

- **12/12 P1 通过**，4 处附带修复通过；
- 13 号 `v1.1-p0-fixed → v1.2-p1-fixed`，`status: active` 保持；
- 表格 / 锚点 / 链接 / 事实核对全绿；
- **建议 Leader APPROVED**，push 后开 Draft PR，required checks 绿后 squash merge。
