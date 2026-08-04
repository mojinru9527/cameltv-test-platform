# 🗂️ Dev 部门项目看板 — Batch 84（真机性能验收：CP-C1 Android 端到端采集）

> **用途**：追踪 Batch 84 进度节点。Dev 部门启动时必须先读本看板。

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | CamelTv 测试平台 v2 — 真机性能验收（轻量批次） |
| **关联 PM 计划** | 轻量批次无 PM/Design 工件（mode: light） |
| **关联 PRD** | [batch-84-real-device-acceptance-prd-summary.md](../batch-84-real-device-acceptance-prd-summary.md) |
| **看板创建** | 2026-08-04 |
| **执行器** | codex（用户确认 2026-08-04） |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | PRD-lite + 看板 | ✅ | ✅ | ⏳ | ⏳ | ⏳ | **当前位置** |
| 1 | 环境：adb + SoloX + venv | ✅ | ✅ | 🔄 | ⏳ | ⏳ | adb 37.0.1 已装、solox 已装；等手机 USB 调试授权 |
| 2 | 设备识别 + App 包名发现 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | OPPO Find X3 待授权 |
| 3 | 采集会话 E2E（快照 + 启动 + 报告） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 平台 perf API 链路 |
| 4 | 证据 + QA + Leader + 条件关闭 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 复盘卡 + 流程回写 |
| 5 | 一次总确认 → push → PR → 合入 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | audit-cconditions + scan-common-bugs |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 📍 当前位置

```
Batch 84 — 真机性能验收（轻量）
├── ✅ PRD-lite + 看板
├── ✅ 环境（adb 37.0.1 / solox / venv）
├── 🔄 等 OPPO Find X3 USB 调试授权（adb unauthorized）
├── ⏳ Slice 2: 设备识别 + App 包名
├── ⏳ Slice 3: 采集会话 E2E
└── ⏳ Slice 4/5: 证据 + QA/Leader + 总确认合入
```
