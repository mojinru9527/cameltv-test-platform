# 🗂️ Dev 部门项目看板 — Batch 67（AI 验收与正式域名发布前置条件收口）

> **用途**：追踪 Batch 67 进度节点。Dev 部门启动时必须先读本看板。

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | CamelTv 测试平台 v2 — 外部前置条件收口 |
| **关联 PM 计划** | [batch-67-ai-acceptance-release-pm-plan.md](../batch-67-ai-acceptance-release-pm-plan.md) |
| **关联 PRD** | [batch-67-ai-acceptance-release-prd-summary.md](../batch-67-ai-acceptance-release-prd-summary.md) |
| **总预估工时** | 2h |
| **已用批次** | 67 |
| **看板创建** | 2026-08-02 |
| **最后更新** | 2026-08-03 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 前置条件收口（清单登记 + 凭据实测 + 构建修复） | ✅ | ✅ | ✅ | ✅ | ✅ | 已合入 #97–#100；6.1 部署登记 ✅（2026-08-03） |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 📍 当前位置

```
Batch 67 — 前置条件收口
├── 已完成: 清单 2.x 登记 + 凭据实测（2.1 AI Key 200，C67-1 关闭）；B67-Q3/Q4 构建与健康检查修复；
│   已合入 main（#97–#100）
├── ✅ 6.1 部署登记: Railway `https://test-platform.up.railway.app` 实测 health 200（版本 2.3.0 与 main 一致）；
│   Vercel `https://cameltv-test-platform1.vercel.app` 公开访问 200（登录页 + /api 反代）
├── ✅ 条件关闭: C67-2 / C58-02 / C58-06
└── ⏳ 下一步: AI 验收批次（G56-011/012/014 全链路 + C67-3 蓝湖 Cookie 实测 + 正式域名发布演练）
```

## 📜 批次记录

### Batch 67 — 前置条件收口 (2026-08-02)
- **产出**: 清单 §2/§6.1 登记、六部门工件、C67 条件、凭据实测证据
- **审批**: ✅ 用户已授权（2026-08-03）
- **耗时**: ~1h

### Batch 67 收口 (2026-08-03)
- **产出**: 6.1 部署登记 ✅（Railway URL 实测 health 200）；Vercel 公开访问 200（新域名登记）；
  C67-2 / C58-02 / C58-06 关闭；清单与 C-CONDITIONS 同步
- **审批**: 待推送授权（§2.4）

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 6.1 | P1 | 已解除 — Railway `https://test-platform.up.railway.app` health 200（2026-08-03 实测）；Vercel 域名变更为 `cameltv-test-platform1.vercel.app`，公开访问 200 | 用户 | 2026-08-02 |

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PM 计划 | [link](../batch-67-ai-acceptance-release-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-67-ai-acceptance-release-design-spec.md) | ✅ |
| QA 报告 | [link](../batch-67-ai-acceptance-release-qa-report.md) | 🔄 |
| Leader 判决 | [link](../batch-67-ai-acceptance-release-leader-verdict.md) | ✅ |
