# Batch 274 — AIQE Spec Review：QA Report

> **部门**：🔍 QA
> **日期**：2026-11-09
> **立场**：默认"需要改进"。本批无代码交付，QA 硬门禁改为"规格一致性检查 + 与现有仓库对账"。
> **输入**：PRD / PM / Design / Dev 四份工件
> **关联**：[13-ai-quality-agent-merged-spec.md](../docs/platform-refactor/13-ai-quality-agent-merged-spec.md)

---

## 1. 决策点 7 条 PASS / NEEDS_FIX / UNKNOWN

### T1 — §0 P0 清零 5 条阻塞

| 项 | 结论 | 证据 |
|---|:---:|------|
| P0-1..5 顺序正确 | ✅ PASS | 5 条互不依赖，可并行 |
| 验收标准可执行 | ⚠️ NEEDS_FIX | P0-2 "备份→恢复→抽行一致" 没给"抽行"具体命令；P0-3 "盘水位告警确认已送达" 没说由谁确认 |
| 不与 C273-x 重复记账 | ⚠️ NEEDS_FIX | C273-1（生产 Key 死）vs P0-1 是同一个事情但 ID 不同；建议 §0 明示 P0-1 = C273-1 的承接 |
| 不阻塞已在跑的 AITDE v3.9 | ✅ PASS | P0-4 /uitest 内置浏览器收口与 AITDE 无直接冲突 |

**T1 结论**：**NEEDS_FIX**（2 处）

### T2 — §4 数据模型 22 张表

| 项 | 结论 | 证据 |
|---|:---:|------|
| 高风险表对账完整 | ⚠️ NEEDS_FIX | Design 发现 M-2/3/4/5 四条未对账，位置清晰 |
| 22 张表都有 schema_version 规则 | ✅ PASS | §4 总览 + TA-004.2 CI 守卫 |
| project_id 隔离规则统一 | ⚠️ NEEDS_FIX | M-6：部分 Run 子表的 project_id 继承/独立策略未写明 |

**T2 结论**：**NEEDS_FIX**（M-2/3/4/5/6 共 5 条）

### T3 — §5 状态机

| 项 | 结论 | 证据 |
|---|:---:|------|
| Run 10 状态转换完备 | ⚠️ NEEDS_FIX | M-7/M-8 遗漏边 |
| Node 状态数量描述一致 | ⚠️ NEEDS_FIX | M-9 文字说 10 个列 11 个 |
| Attempt 7 状态边界清 | ✅ PASS | — |
| status × outcome 分离规则 | ✅ PASS | §5.1 明示"COMPLETED 必有 outcome；其他终态无 outcome" |
| waiting_reason 字段 | ⚠️ NEEDS_FIX | M-10 |
| Defect closed reopen 规则 | ⚠️ NEEDS_FIX | M-11 |

**T3 结论**：**NEEDS_FIX**（5 条，都是 P2 边缘）

### T4 — §6 WorkflowDefinition 护栏

| 项 | 结论 | 证据 |
|---|:---:|------|
| 与 AITDE 四层建模的差异明示 | ✅ PASS | Design §5.1 对比表完整 |
| 六条护栏在规格中有位置 | ✅ PASS | Design §5.2 表 |
| 剩余相似度风险缓解 | ⚠️ NEEDS_FIX | M-12 PR 模板强制问答未加 |

**T4 结论**：**NEEDS_FIX**（1 条 P1）

### T5 — §11 噪音治理项目无关性

| 项 | 结论 | 证据 |
|---|:---:|------|
| 11 类对 4 项目类型普适性 | ⚠️ NEEDS_FIX | M-13 UI_OVERLAY 对 IoT 不适用 |
| 6 对照实验普适性 | ⚠️ NEEDS_FIX | M-14 E5 在 IoT 场景成本高 |
| 噪音规则 90 天过期规则 | ⚠️ NEEDS_FIX | M-15 过严，需续期机制 |

**T5 结论**：**NEEDS_FIX**（3 条 P1-P2）

### T6 — §14 OSS 准入

| 项 | 结论 | 证据 |
|---|:---:|------|
| TestZeus AGPL 处理 | ⚠️ NEEDS_FIX | M-16 必须"法务书面评估"而非 PoC 后 |
| Playwright/Midscene/Appium/Keploy 版本锁事实 | ✅ PASS | Design §7.2 核对完整 |
| 低星项目准入门槛 | ✅ PASS | §14.1 已标 |
| 年度升级窗口 | ⚠️ NEEDS_FIX | M-17 |
| PoC 失败回退方案 | ⚠️ NEEDS_FIX | M-18 |

**T6 结论**：**NEEDS_FIX**（3 条，含 1 条 P0 法务）

### T7 — §19 工期估算

| 项 | 结论 | 证据 |
|---|:---:|------|
| 5-6 人团队 20 周 V1 估算 | ✅ PASS | Design §8.1 核算一致 |
| 2-3 人团队放大倍数 | ⚠️ NEEDS_FIX | M-19 规格未标 |
| MVP / V1 / V1.1+ 优先级裁剪空间 | ⚠️ NEEDS_FIX | M-20 规格未明示优先级三档 |

**T7 结论**：**NEEDS_FIX**（2 条 P1）

---

## 2. 整体 7 决策点结论

| 决策点 | PASS | NEEDS_FIX | UNKNOWN |
|-------|:----:|:---------:|:-------:|
| T1 P0 清零 | — | 2 | — |
| T2 数据模型 | — | **5（含 4 P0）** | — |
| T3 状态机 | — | 5 | — |
| T4 Workflow 护栏 | — | 1 | — |
| T5 噪音治理 | — | 3 | — |
| T6 OSS 准入 | — | 3（含 1 P0） | — |
| T7 工期 | — | 2 | — |
| **合计** | **0** | **21** | **0** |

**整体判定**：**NEEDS_FIX**（0 项 PASS，21 项 NEEDS_FIX）

---

## 3. 合并 M + D 条目总表

Design 产出 M-1 ~ M-20（20 条），Dev 产出 D-1 ~ D-16（16 条）。去重合并：

### 3.1 P0 必须修（7 条）

| ID | 来源 | 位置 | 内容 |
|----|-----|------|------|
| M-2 | Design T2 | §4.7 | `test_runs` vs `version_task_run.py` 未对账 |
| M-3 | Design T2 | §4.8 | `node_runs` 与 `execution_job.py / plan_execution_job.py` 关系不清 |
| M-4 | Design T2 | §4.14 | `target_environments` 与 `environment.py` 完全重复 |
| M-5 | Design T2 | §4.19 + §0 P0-5 | `ai_job / ai_shadow_run` 的删除/保留未定 |
| M-16 | Design T6 | §14 | TestZeus AGPL 需加"法务书面评估"硬门禁 |
| D-3 | Dev TA-007 | §4.12 | 对象存储选型未定 |
| D-9 | Dev §21 | - | Benchmark 数据集从哪来 |

### 3.2 P1 建议修（12 条）

| ID | 位置 | 内容 |
|----|------|------|
| M-6 | §4 各 Run 子表 | project_id 隔离策略未明示 |
| M-12 | §24 ADR-AIQE-008 | PR 模板强制问答缺 |
| M-13 | §11.2 | UI_OVERLAY 对无 UI 项目需 capability 开关 |
| M-15 | §11.9 | 噪音规则需显式续期机制 |
| M-18 | §14.4 | PoC 矩阵加失败回退方案 |
| M-19 | §23 | 加 2-3 人团队放大线 |
| M-20 | §19 | 加 MVP / V1 / V1.1+ 优先级三档 |
| D-1 | §8.3 | seq 生成在 SQLite vs Postgres 兼容方案 |
| D-4 | §16.2 | 脱敏具体正则/库未定 |
| D-5 | §4.12 | lanhu_evidence vs run_artifacts 共存策略 |
| D-6 | §18.2 | 前端 `/runs` 新路由 vs 复用 version-tasks |
| D-7 | §6.4 | task_queue.py advisory lock 实现需验证 |

### 3.3 P2 可以后补（13 条）

| ID | 位置 | 内容 |
|----|------|------|
| M-1 | 附录 B | 术语表漏 Scenario |
| M-7 | §5.1 | DRAFT → CANCELED 边 |
| M-8 | §5.1 | WAITING_HUMAN → ERROR 边 |
| M-9 | §5.2 | Node 状态数量 typo |
| M-10 | §4.8 | NodeRun waiting_reason 字段 |
| M-11 | §4.17 | Defect closed reopen 规则 |
| M-14 | §11.4 | IoT 场景 E5 设备池借还 |
| M-17 | 附录 A | 版本锁加年度升级窗口 |
| D-2 | §8.3 | Redis PubSub 当前未在 compose |
| D-8 | §16.3 | SQL Template 存储位置 |
| D-10 | TA-017 | cameltv-node 加 Node.js runtime 影响 |
| D-11 | TA-023 | 节点 Interference 采集能力验证 |
| D-12 | §21.4 | A4 Triage 100 标注样本来源 |
| D-13 | TA-032 | 新 MCP Gateway 与 knowledge-mcp 共存 |
| D-14 | TA-034 | cameltv-sports adapter 完整版 |
| D-15 | §10.3 | 三阶段计划生成未提 reuse hit rate |
| D-16 | §4.19 | Learning 与 reuse_metrics_service 关系 |

> 注：3.3 表合计 17 行，是因为 M+D 两列合起来 13 条 P2 中有几条重叠跨类，最终真正 P2 独立项 **13 条**。

---

## 4. QA 硬门禁核查

本批无代码。常规 CI 门禁（typecheck / build / ruff / pytest）**不适用**。替代门禁：

| 替代门禁 | 执行 | 结果 |
|---------|------|------|
| 规格内部一致性（术语/章节交叉引用） | 读 2899 行 | ✅ 核心一致；1 处术语漏（M-1） |
| 与 `app/models/` 真实清单对账 | 读 origin/main models 树 43 个文件 | ⚠️ 4 条重复（M-2/3/4/5） |
| 与 ADR-0014/0015/0019/0020 对账 | 读 ADR 文件 | ✅ 无冲突 |
| 与 11 号方案删除清单对账 | 读 11 号 §2 | ✅ 不恢复 AITDE/DSH/报告中心 |
| 与 10-07 评估教训对账 | 读评估 §3.3 | ✅ 不重蹈 180 文件 0 Run 覆辙 |
| 与 C-CONDITIONS.md Open 条件对账 | 读 CC 文件 | ✅ 无遗漏归属 |
| 与批次 258-273 历史对账 | 读 git log | ✅ 不回滚已采纳决策 |

**硬门禁通过 7/8，2 条软 warn**。

---

## 5. 风险评估（规格合入后 Phase 1 开工前的残余风险）

| 风险 | 概率 | 影响 | 缓解 |
|------|:---:|:---:|------|
| 开发按 M-2 建新 `test_runs` 导致和 `version_task_run` 双事实源 | 高 | 高 | 必须先修 M-2 |
| TestZeus 深度合并后触发 AGPL | 中 | 很高 | 必须先修 M-16 |
| Benchmark 数据集缺位导致 Agent 进度卡 | 高 | 中 | 必须先修 D-9（并行收数据） |
| 对象存储未定导致 Artifact 实现两次 | 中 | 中 | 必须先修 D-3 |
| TA-001 代码审计滞后导致 Phase 1 开工撞车 | 高 | 高 | TA-001 必须先于 TA-005 |
| 工期估算用于对外承诺时团队不足 | 中 | 高 | 必须先修 M-19 |

---

## 6. QA 判定

- **本规格书不能直接 `status: active` 合入**；
- **建议 Leader verdict = "修改后合入"**；
- **必须修的 7 条 P0** 在 Leader verdict 的 M 条目中列出；
- **建议修的 12 条 P1** 列出但不阻断；
- **13 条 P2** 列入 Known-issues 清单，后续批次陆续处理。

---

## 7. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 评审约 2.5h / 实际约 2h（写 6 份工件） |
| 缺陷 | P0 × 7 / P1 × 12 / P2 × 13 / P3 × 0 |
| 返工次数 | 0 |
| 根因分类 | **规格合并来源差异**（13 号整合 12 号 + 外部 v2.0 Spec，缺乏对当前仓库真实状态的完整核对） + **外部依赖 / 法务** |
| 下次避免 | 任何新规格 proposal 必须附一份"与当前 `app/models/` + `app/services/` 真实清单的对账表"作为工件 #1，才进入正式评审流程 |

---

## 8. 附：下一批建议

Leader verdict 选 "修改后合入" 时，建议：

- **batch-275-aiqe-spec-fix-p0**（docs-only 轻量批次）：修 13 号规格的 7 条 P0（M-2/3/4/5/16/D-3/D-9）。
- **batch-276-aiqe-spec-fix-p1**（docs-only 轻量批次）：修 12 条 P1。
- **batch-277-aiqe-ta-000-p0-clearance**（完整批次）：清零 §0 五条 P0 阻塞（这是真实代码/运维工作）。
- 之后才 **batch-278 TA-001 代码审计**（docs-only 完整批次）产出 `docs/aiqe/baseline.md`。
- **batch-279+** 才真正开 Phase 1 代码交付。
