# 🗂️ Dev 部门项目看板 — Batch 261（B4 体育连续验收）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | batch-261-sports-continuous-acceptance（B4 落地批次） |
| **关联 PM 计划** | [batch-261-sports-continuous-acceptance-pm-plan.md](../batch-261-sports-continuous-acceptance-pm-plan.md) |
| **关联 PRD** | [batch-261-sports-continuous-acceptance-prd-summary.md](../batch-261-sports-continuous-acceptance-prd-summary.md) |
| **批次档位** | 完整批次（协议/接口/配置变更） |
| **总预估工时** | 24h |
| **看板创建** | 2026-09-19 |
| **最后更新** | 2026-09-19 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 证据包校验服务（B4-1 后端） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 17 例 |
| 2 | 校验 API + 篡改显红前端（B4-1） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 前端 168 文件 737 例 |
| 3 | 试点数据集与基线制备（B4-2） | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | **当前位置**，真实导入需环境 → C261-1 |
| 4 | 连续 3 版本演练 + 模板（B4-3/4/5） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 真实数字需 VPN → C261-1 |
| 5 | §5 九条验收报告（B4-5 收尾） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |

## 📍 当前位置

```
Batch 261 — Slice 3：试点数据集与基线制备（B4-2）
├── 已完成: Slice 1（校验服务 17 例）、Slice 2（校验 API + 篡改显红前端）；B4-1 完成
│          commit c2e256c9 / eb4a750a / 173bb15b
├── 🔄 进行中: 接口 50 + Web 30 清单与导入路径 + 环境指纹/账号槽位接线
├── ⏳ 待审批: 本批次一次总确认（推送 + Draft PR + required checks 通过后合入）
└── ⏳ 下一步: Slice 4（连续 3 版本演练 + 报告模板，环境不可达时明确失败）→ Slice 5（§5 九条验收报告）
```

## 📜 批次记录

### Batch 258–260（B1–B3，均已合入）
- B1 PR #477 → `2ced1baf`；B2 PR #478 → `573f5c12`；B3 PR #479 → `3788c66d`
- 审计 S1–S5 已关闭；S6 部分关闭（`C259-2`）

### Batch 261 — B4 体育连续验收（进行中）
- **产出**: 待补
- **审批**: 待一次总确认

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| Test5 不可达 | **P1** | `camel-api-gateway05.svc.elelive.cn` → `192.168.50.170:80` TCP 不通（需 VPN）→ B4-3/4/5 的真实执行在本机不成立 | 用户环境 | 2026-09-19 |
| 库内无体育资产 | P1 | 本机 worktree 库为空 → B4-2 的真实导入与覆盖率不可产出 | 用户环境 | 2026-09-19 |
| 能力重复风险 | P2 | 证据完整率已有既有策略、指纹/账号槽位/版本记录已有模型；若不复用会产生第二份实现（S1/S5 模式） | 已在 PRD §4 写成非目标 | 2026-09-19 |

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [link](../batch-261-sports-continuous-acceptance-prd-summary.md) | ✅ |
| PM 计划 | [link](../batch-261-sports-continuous-acceptance-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-261-sports-continuous-acceptance-design-spec.md) | ✅ |
| QA 报告 | `../batch-261-sports-continuous-acceptance-qa-report.md` | ⏳ |
| Leader 判决 | `../batch-261-sports-continuous-acceptance-leader-verdict.md` | ⏳ |
| 九条验收报告 | `../batch-261-sports-continuous-acceptance-final-acceptance-report.md` | ⏳ |
