# Batch 275 — AIQE Spec Fix P0：Leader Verdict

> **部门**：🎯 Leader
> **日期**：2026-11-09
> **输入**：PRD-lite + QA report + 修改后的 13 号规格

---

## 1. 判决

# ✅ APPROVED

**理由**：

- batch-274 Leader verdict 列的 7 条 P0 全部修完，每条均有明确文件位置 + 标记 `batch-275 M-X/D-X`；
- 13 号规格 `status: proposal → active`、`version: spec-v1.0-merged → v1.1-p0-fixed`；
- 用户两项关键决策（M-4 扩字段 / D-3 本地 FS + prod 待定）已入规格；
- 无代码触及，无 CI 风险；
- 复盘卡齐；QA 一致性门禁全绿。

**合入路径**：PR #497 同分支 push 后转 Ready for review → 用户一次总确认 → squash merge。

## 2. 用户总确认清单

本批无代码交付、无数据库迁移、docs-only。需要用户在 push 后完成以下**一次性**确认：

1. ✅ **接受 batch-275 Leader APPROVED**，PR #497 转 Ready for review；
2. ✅ **同意在 PR #497 上 squash merge 到 main**（只有 docs 变动，风险 ≈ 0）；
3. ✅ **接受下一批次路线**：
   - **batch-276**（docs-only 轻量）：修 12 条 P1；
   - **batch-277**（完整批次）：清 §0 P0-1..5 的真实代码/运维工作（轮换 Key / 备份演练 / 磁盘 / /uitest 剥离 / ai_gateway 删除）；
   - **batch-278**（完整 docs-only）：TA-001 代码审计产出 `docs/aiqe/baseline.md`；
   - **batch-279+**：真正开 Phase 1 代码交付。

## 3. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 本批改规格时大量 str_replace 是因为 batch-274 评审时只给了 M-X 清单没给"打补丁内容" | 评审类工件后续应多产一份 "fix-plan.md"（每条 M/D 的建议 patch），减少执行时的二次决策 | 待修 `.claude/skills/cameltv-agent-team/DEPARTMENTS.md` 的 Leader 节；由 batch-276 顺便改 |
| v1.1 variant 通过 banner 标注变更历史的方式比改整体 title 更可维护 | 作为良好实践沉淀 | 本 verdict 记录 |
| 用户两项决策在 PRD-lite 入库避免执行阶段歧义 | 持续推广 | 本 verdict 记录 |

## 4. 知识审计

### 4.1 本批可入 KB 的知识

| 知识 | 类型 | 入库建议 |
|------|-----|---------|
| "规格 v1→v1.1 用 banner 标变更历史" | 流程实践 | 走 ingest_platform_knowledge |
| "docs-only 批次同 PR 多次 commit 的模式"（PR #497 从 batch-274 到 275 到 276 到 277...） | 流程实践 | 同上 |
| "Agent Team 门禁允许一个 PR 承载多批次 docs 修复" | 决策 | 同上 |

**建议**：合入后由 Dev 部门统一出 KB 入库草稿（涵盖 274/275 两批次产出的知识）。本批不入，因 PR 未合入。

### 4.2 与 KB 已有知识的矛盾检查

- ✅ 不与 ADR-0014 / 0015 / 0019 / 0020 矛盾；
- ✅ 与 ADR-0027/0028/0029 的更新路径已在 M-5 显式写明（本批 docs 定方向，batch-277 实际改 ADR status）；
- ✅ 不与 11 号方案 §2 删除清单矛盾；
- ✅ 不与 batch-274 verdict §2 矛盾（恰好是 §2 的落地）。

## 5. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | ≤ 1 天 / 实际 ≈ 1.5h（含 batch-274 评审→batch-275 决策→执行的完整链路，但不含用户决策等待） |
| 缺陷 | 0（Slice 1-8 均一次通过） |
| 返工次数 | 1（str_replace blockquote 格式）|
| 根因分类 | 流程（规格修改时的 str_replace 对格式敏感） |
| 下次避免 | 本批次已通过"先 sed -n 定位 → 再抄原文" 预防；保持这个模式 |

## 6. 本批无 C 条件

batch-275 不新增 C-CONDITIONS.md 条目。遗留的 P1/P2 已在 batch-274 Leader verdict §3/§4 登记，分别由 batch-276 和后续批次承接。

## 7. 合入前最后一次核对

**Push 前核对表**（由 Dev 部门执行）：

- [ ] 工作树无夹带非本批文件（只有 13 号 + batch-275 四份工件）；
- [ ] commit message 规范（`docs(batch-275): ...`）；
- [ ] Attribution 齐（Co-Authored-By 行）；
- [ ] 本 verdict + QA + PRD-lite + 看板 四份工件都 commit；
- [ ] push 后在 PR #497 自动归入新 commits；
- [ ] 本 verdict 的 "合入路径" 和 PR description 保持口径一致。

## 8. 关联工件

- PRD-lite：[batch-275-aiqe-spec-fix-p0-prd-lite.md](batch-275-aiqe-spec-fix-p0-prd-lite.md)
- QA：[batch-275-aiqe-spec-fix-p0-qa-report.md](batch-275-aiqe-spec-fix-p0-qa-report.md)
- 看板：[kanbans/DEV-batch-275-aiqe-spec-fix-p0.md](kanbans/DEV-batch-275-aiqe-spec-fix-p0.md)
- 修改对象：[docs/platform-refactor/13-ai-quality-agent-merged-spec.md](../docs/platform-refactor/13-ai-quality-agent-merged-spec.md) v1.1-p0-fixed
- 上游判决：[batch-274-aiqe-spec-review-leader-verdict.md](batch-274-aiqe-spec-review-leader-verdict.md)
- 关联 PR：https://github.com/mojinru9527/cameltv-test-platform/pull/497
