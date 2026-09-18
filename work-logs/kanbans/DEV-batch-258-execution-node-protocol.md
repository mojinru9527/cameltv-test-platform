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
| 1 | `url_guard` 统一守卫 + 需求抓取/发布包导入接入（B1-1） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 71 例回归绿 |
| 2 | 令牌域名白名单（B1-2） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 12 例回归绿 |
| 3 | OCR 去 `shell=True`（B1-3） | ✅ | ✅ | ✅ | ⏳ | ⏳ | `rg shell=True app/` 为空 |
| 4 | `ExecutionJob` 协议 + 迁移 + 权限点（B1-4） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 迁移 from-base 演练通过 |
| 5 | `cameltv-node` CLI（B1-5） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 28 例回归绿；含最小证据端点 |
| 6 | 平台侧节点状态（B1-6） | ✅ | ✅ | ✅ | ✅ | ⏳ | 前端四门禁全绿 |
| 7 | B1 端到端证据 8 条（B1-7） | ✅ | ✅ | ✅ | ✅ | ⏳ | 本地替身 19/19；Test5 → C258-1 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 258 — 全部 Slice 完成，等一次总确认
├── 已完成: Slice 1..7（B1-1…B1-7）；QA 报告 + Leader 判决已出（有条件通过）
├── 未决（不阻塞合入）: C258-1 Test5 真机验收（需 VPN 机器）、C258-2 节点侧凭据隔离（B2-1）
├── ⏳ 待用户: 一次总确认（推送 feature/batch-258-execution-node-protocol + Draft PR + CI 绿后合入 main）
└── ⏳ 下一步: 收到总确认 → push → gh pr create --draft → audit-ai-pr → required checks → squash 合入 → 清理 worktree
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
| B1 与 B4-1 的证据口径重叠 | P2 | B1-7 要「证据可下载」，B4-1 才定型 EvidenceBundle(manifest+校验)；B1 只做最小上传/下载，B4-1 再补篡改检测与完整性门禁 | Leader 复核 | 2026-09-18 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [link](../batch-258-execution-node-protocol-prd-summary.md) | ✅ |
| PM 计划 | [link](../batch-258-execution-node-protocol-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-258-execution-node-protocol-design-spec.md) | ✅ |
| QA 报告 | [link](../batch-258-execution-node-protocol-qa-report.md) | ⏳ |
| Leader 判决 | [link](../batch-258-execution-node-protocol-leader-verdict.md) | ⏳ |
