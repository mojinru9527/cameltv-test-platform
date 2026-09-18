# 🗂️ Dev 部门项目看板

> **用途**：追踪多批次开发的进度节点，防止上下文丢失。每次 Dev 部门启动时**必须先读取本看板**。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | batch-258-execution-node-protocol（B1 落地批次） |
| **关联 PM 计划** | [batch-258-execution-node-protocol-pm-plan.md](../batch-258-execution-node-protocol-pm-plan.md) |
| **关联 PRD** | [batch-258-execution-node-protocol-prd-summary.md](../batch-258-execution-node-protocol-prd-summary.md) |
| **批次档位** | 完整批次（六件） |
| **总预估工时** | 24h |
| **已用批次** | 1 批 |
| **看板创建** | 2026-09-18 |
| **最后更新** | 2026-09-18 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | `url_guard` 统一守卫 + 需求抓取/发布包导入接入（B1-1） | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | **当前位置** |
| 2 | 令牌域名白名单（B1-2） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 1 的守卫 |
| 3 | OCR 去 `shell=True`（B1-3） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 独立 |
| 4 | `ExecutionJob` 协议 + 迁移 + 权限点（B1-4） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 数据模型变更 |
| 5 | `cameltv-node` CLI（B1-5） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 4 |
| 6 | 平台侧节点状态（B1-6） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 4 |
| 7 | B1 端到端证据 8 条（B1-7） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 5/6 + Test5 可达 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 258 — Slice 1：url_guard 统一守卫
├── 已完成: worktree 验证；PRD/PM/Design 三份工件；审计 S1/S2/S3 证据位置复核
├── 🔄 进行中: app/core/url_guard.py 抽取 + outbound_policy 反向依赖 + 需求抓取接入
├── ⏳ 待审批: 本批次一次总确认（推送 + Draft PR + required checks 通过后合入）
└── ⏳ 下一步: Slice 2/3（白名单、OCR）→ Slice 4（ExecutionJob）
```

---

## 📜 批次记录

### Batch 258 — B1 落地（2026-09-18）
- **产出**: 待补（本批进行中）
- **审批**: 待一次总确认
- **耗时**: 进行中

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| GitHub 代理不可用 | P3 | 全局 git 配置 `http.https://github.com.proxy=http://127.0.0.1:7688` 未监听；直连 443 可用，已用 `GIT_CONFIG_*` 覆盖绕过（未改全局配置） | — | 2026-09-18 |
| Test5 内网可达性 | P1 | B1-7 的 8 条试点用例依赖内网 + VPN；不可达时按 Deferred 登记，不伪造通过 | 测试环境 | 2026-09-18 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [link](../batch-258-execution-node-protocol-prd-summary.md) | ✅ |
| PM 计划 | [link](../batch-258-execution-node-protocol-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-258-execution-node-protocol-design-spec.md) | ✅ |
| QA 报告 | [link](../batch-258-execution-node-protocol-qa-report.md) | ⏳ |
| Leader 判决 | [link](../batch-258-execution-node-protocol-leader-verdict.md) | ⏳ |
