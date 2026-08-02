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
| **最后更新** | 2026-08-02 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 前置条件收口（清单登记 + 凭据实测 + 构建修复） | ✅ | ✅ | ✅ | ⏳ ⬅️ | ⏳ | **当前位置** |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 📍 当前位置

```
Batch 67 — 前置条件收口
├── 已完成: 清单 2.x/6.1 登记、六部门工件、看板；AI Key 换新实测 200（C67-1 关闭）；
│   B67-Q3 锁文件跨平台修复（docker build --target builder 通过）
├── 🔄 进行中: 等待 push 授权 → Draft PR → 首轮 checks → 合并
├── ⏳ 待审批: 用户 push 授权 + 二次确认
└── ⏳ 下一步: 合并后 Railway 自动部署最新主干 → 用户回传 URL（C67-2，6.1）
```

## 📜 批次记录

### Batch 67 — 前置条件收口 (2026-08-02)
- **产出**: 清单 §2/§6.1 登记、六部门工件、C67 条件、凭据实测证据
- **审批**: 待用户 push 授权
- **耗时**: ~1h

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 6.1 | P1 | 部署服务器 URL 未提供（构建阻塞 B67-Q3 已修复，待合并后自动部署） | 用户 | 2026-08-02 |

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PM 计划 | [link](../batch-67-ai-acceptance-release-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-67-ai-acceptance-release-design-spec.md) | ✅ |
| QA 报告 | [link](../batch-67-ai-acceptance-release-qa-report.md) | 🔄 |
| Leader 判决 | [link](../batch-67-ai-acceptance-release-leader-verdict.md) | ✅ |
