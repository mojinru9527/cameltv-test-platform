# 🗂️ Dev 部门项目看板 — Batch 99（真机性能验收）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 视频流双场景验收（C84-2：Chrome 赛事 / 小象直播间 各 10 分钟）+ iOS（CP-C2/C84-1）（轻量批次） |
| **关联 PRD** | [batch-99-real-device-acceptance-prd-summary.md](../batch-99-real-device-acceptance-prd-summary.md) |
| **看板创建** | 2026-08-05 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-99-real-device-acceptance |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 环境探测（adb/tidevice/solox/venv） | ✅ | ✅ | ✅ | ✅ | ⏳ | Android ✅；iOS 驱动缺失 |
| 2 | 场景 A：Chrome www.camel1.tv 赛事视频流 10 分钟 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ | **当前位置**：等设备重连 |
| 3 | 场景 B：小象直播 App 直播间 10 分钟 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 待确认包名 |
| 4 | iOS（Safari + 小象）或阻塞登记 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 待 Apple 驱动 |
| 5 | 证据 + QA/Leader 工件 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |

## 📍 当前位置

```
Batch 99 — 真机性能验收（口径重定义后）
├── ✅ B99-P1 修复：自实现 SurfaceFlinger fps 解析（8 单测，保留）
├── 🔄 场景 A/B 待设备重连后各采集 10 分钟
└── ⏳ iOS：缺 Apple Mobile Device 驱动
```
