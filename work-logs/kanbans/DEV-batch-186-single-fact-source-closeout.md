# 🗂️ Dev 部门项目看板 — batch-186-single-fact-source-closeout

> Batch 186（完整）：C182-1 执行单一事实源 / C182-2 回填脚本验证 / C184-1 OS 沙箱评估

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | batch-186-single-fact-source-closeout |
| **关联 PRD** | test-platform-v2/work-logs/batch-186-single-fact-source-closeout-prd-summary.md |
| **看板创建** | 2026-08-16 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 工件 PRD/PM/Design/看板 | ✅ | ✅ | ✅ | ⏳ | ⏳ | commit b88a4b9 |
| 1 | C182-1 移除计划双写（execute_all + auto_execute） | ✅ | ✅ | ✅ | ⏳ | ⏳ | test_single_fact_source 4 例 + batch169 更新 |
| 2 | C182-2 脚本可测化 + 30 例单测 + 三阶段 dry-run 证据 + 生产手册 | ✅ | ✅ | ✅ | ⏳ | ⏳ | evidence/batch-186/backfill-domain-b182-dryrun.txt |
| 3 | C184-1 ADR-0020 评估 + README 索引 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 纯文档 |
| 4 | C-CONDITIONS：C182-1/C184-1 Closed、C182-2 Deferred | ✅ | ✅ | ⏳ | ⏳ | ⏳ | 待提交 |
| 5 | QA/Leader 工件 + 全量回归 | ✅ | ✅ | ⏳ | ⏳ | ⏳ | 首轮 1576/0+2（batch-157 旧契约测试，已更新 commit afb2234）；全量重跑中 |
| 6 | 总确认 → push → PR → 合入 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |

---

## 📍 当前位置

```
Batch 186 — 实现完成，全量回归中
├── 已完成: C182-1 双写移除 + C182-2 测试/证据/手册 + C184-1 ADR-0020（commit b88a4b9）
├── 进行中: backend 全量 pytest
└── ⏳ 下一步: QA/Leader 工件 → 用户一次总确认 → push → Draft PR → checks 全绿 → 合入
```
