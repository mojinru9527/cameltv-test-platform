# 🗂️ Dev 部门项目看板 — Batch 262（生产恢复演练与运维缺口）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | batch-262-ops-restore-drill-evidence（B0 运维项证据补完） |
| **关联 PRD** | [batch-262-ops-restore-drill-evidence-prd-summary.md](../batch-262-ops-restore-drill-evidence-prd-summary.md)（PRD-lite） |
| **批次档位** | **轻量批次**（纯文档/纯证据，零代码改动） |
| **看板创建** | 2026-09-19 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 生产恢复演练 + 手册补写 | ✅ | ✅ | ✅ | ✅ | ⏳ | 演练实测 20 秒，手册 `docs/ops/restore-drill.md` |
| 2 | 验收报告第 ⑧/⑨ 条更新 | ✅ | ✅ | ✅ | ✅ | ⏳ | ⑧ 一半达成 / ⑨ 达成 |
| 3 | 三个运维缺口登记 C 条件 | ✅ | ✅ | ✅ | ✅ | ⏳ | C262-1/2/3 |

## 📍 当前位置

```
Batch 262 — 全部切片完成，等一次总确认
├── 已完成: 生产实测（df -h 73% / 无 85% 告警 / 恢复演练 20 秒）+ 手册补写 + 报告更新 + C 条件登记
├── 阻塞: GitHub 网络中断（direct 与代理两条路径均不可达）→ 暂不能 push/PR
└── ⏳ 待用户: 一次总确认（推送 + Draft PR + required checks 通过后合入）
```

## 📜 批次记录

### Batch 261 — B4 落地（已合入）
- **产出**: PR #480 → squash `334748bf`；§5 九条验收报告

### Batch 262 — B0 运维证据补完（进行中）
- **产出**: `docs/ops/restore-drill.md`（新）+ 验收报告 ⑧/⑨ 条更新 + C262-1/2/3
- **审批**: 待一次总确认

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| GitHub 不可达 | P2 | worktree 创建时 `git fetch` 失败（`Connection reset`）；随后 direct 与代理 `127.0.0.1:7688` **两条路径均不可达** → 无法 push/PR。已用本地 `git worktree add origin/main` + 手工复刻元数据绕过（verifier 通过） | 网络恢复 | 2026-09-19 |
| 生产落后主干 | P1 | 生产库 `alembic_version = 20260922_ai_agent_token`，B1/B3/B4 迁移未上生产 → C262-3 | 发布火车 | 2026-09-19 |
| 无磁盘告警 | P2 | 73% 达标但无 85% 阈值告警 → C262-1 | 运维 | 2026-09-19 |
| 备份节奏 | P2 | 最新 dump 09-17，演练日 09-19，无定时任务 → C262-2 | 运维 | 2026-09-19 |

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD-lite | [link](../batch-262-ops-restore-drill-evidence-prd-summary.md) | ✅ |
| QA 报告 | [link](../batch-262-ops-restore-drill-evidence-qa-report.md) | ✅ |
| Leader 判决 | [link](../batch-262-ops-restore-drill-evidence-leader-verdict.md) | ✅ |
| 恢复演练手册 | `docs/ops/restore-drill.md` | ✅ |
