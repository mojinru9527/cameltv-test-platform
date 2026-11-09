# Batch 275 — AIQE Spec Fix P0：QA Report

> **部门**：🔍 QA
> **日期**：2026-11-09
> **立场**：默认"需要改进"。docs-only 批次，门禁改为"规格一致性 + 与 batch-274 verdict 对账"。
> **输入**：PRD-lite + 修改后的 13 号规格

---

## 1. Slice 验收

| # | Slice | 落地位置 | 验收 |
|---|-------|---------|:----:|
| 1 | M-2 §4.7 加 version_task_run 对账 | line 410-424 | ✅ 含迁移策略 A/B 候选 + "不得新表"硬规则 |
| 2 | M-3 §4.8 加 execution_job_id 字段 | line 440-453 | ✅ 含 1:1 关系说明 + plan_execution_job 待核实项 |
| 3 | M-4 §4.14 改为扩 environment | line 562-589 | ✅ 删新表 + 扩字段迁移脚本 + 全文引用等价约定 |
| 4 | M-5 §0 P0-5 + §4.19 明示删 3 张 ai_* 表 | line 83 + line 690-694 | ✅ 具体表名列齐 + ADR 状态更新路径 |
| 5 | M-16 §14 TestZeus AGPL 法务硬门禁 | line 1857 + line 1900 | ✅ 推荐矩阵 + PoC 矩阵双处升级为"硬门禁 / 法务未过不启动" |
| 6 | D-3 §4.12 对象存储选型 | line 534-547 | ✅ dev 本地 FS + prod 三选一 + 抽象接口屏蔽差异 |
| 7 | D-9 §21.0 benchmark 数据集来源 | line 2745-2779 | ✅ A1/A2/A4/A5 来源 + 版本锁 + 周度进度 |
| 8 | status: proposal → active；version → v1.1-p0-fixed | frontmatter + banner | ✅ 双处更新 + 变更日志 banner |

**8/8 Slice 全部 ✅**。

## 2. 一致性门禁

| 检查 | 结果 |
|-----|:---:|
| 内部交叉引用一致（22 张表数 + target_environment 全文替换） | ✅ `target_environment_id` 残留仅在 M-4 修正说明 + banner + 等价约定（合法） |
| 与 batch-274 Leader verdict §2 M-P0 清单一致 | ✅ 7 条 P0 一一对应 |
| 与 batch-274 Design spec §3.1 对账表一致 | ✅ M-2/3/4/5 四条表级冲突均有处置 |
| 与 §2 "不做清单" 15 条不冲突 | ✅ M-5 的 "不恢复 ai_job 旧字段"与"不建平行实体"一致 |
| 与 §24 ADR 清单不冲突 | ✅ M-5 更新 ADR-0027/0028/0029 为 superseded |
| 与 11 号方案 §2 已删清单一致 | ✅ 不恢复 AITDE / DSH / 报告中心 |
| 字段表 Markdown 渲染正确（表头 / 列数一致） | ✅ 手工抽查 §4.7 / §4.8 / §4.14 / §4.12 / §21.0 |

## 3. 未解决事项（遗留到后续批次，合规）

| 条目 | 位置 | 承接批次 | 理由 |
|------|------|---------|-----|
| 12 条 P1 | 见 batch-274 Leader verdict §3 | **batch-276** | 分批处理，避免一次 PR 过大 |
| 13 条 P2 | 见 batch-274 QA report §3.3 | 后续批次 | 边缘场景可延 |
| TA-001 实际代码审计 | — | **batch-278** | 代码级审计不在 docs 批次范围 |
| §0 P0-1..5 代码/运维清零 | — | **batch-277** | 真实轮换 Key / 备份演练 / 磁盘清理 |

## 4. 硬门禁

本批 docs-only，无 CI 硬门禁。替代门禁：

| 替代门禁 | 结果 |
|---------|:---:|
| 文件改动均在 docs/ 下 | ✅ 仅改 `docs/platform-refactor/13-ai-quality-agent-merged-spec.md` + 新增 `work-logs/batch-275-*.md` + 看板 |
| 无代码触及 | ✅ `git diff --stat` 无 `.py / .ts / .tsx / .yml / .json / .toml / .md` 外改动 |
| PR #497 CI 保持绿 | ✅ 待 push 后验证 |

## 5. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | ≤ 1 天 / 实际 ≈ 1h（8 Slice 全是 str_replace 级别精修） |
| 缺陷 | P0 × 0 / P1 × 0 / P2 × 0（新建的 7 条修改无一引入新矛盾） |
| 返工次数 | 1 次（frontmatter banner 的 str_replace 第一次因 blockquote 开头字符不匹配，重读后修正） |
| 根因分类 | 流程（规格合并时未带现有代码对账表，被 batch-274 发现后本批修） |
| 下次避免 | 已在 batch-274 Leader verdict §7 流程回写记录；后续"规格合并清单"要求 Product 必附 current-codebase-reconciliation |

## 6. QA 判定

- **本 Slice 全部通过**；
- **13 号规格已从 proposal 转 active**；
- **建议 Leader APPROVED**，PR #497 可以推完后转 Ready for review。
