# 🗂️ Dev 部门项目看板 — Batch 99（真机性能验收）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 视频流双场景验收（C84-2 已关闭）+ iOS（CP-C2/C84-1 阻塞）（轻量批次） |
| **关联 PRD** | [batch-99-real-device-acceptance-prd-summary.md](../batch-99-real-device-acceptance-prd-summary.md) |
| **看板创建** | 2026-08-05 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-99-real-device-acceptance |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 环境探测（adb/tidevice/solox/venv） | ✅ | ✅ | ✅ | ✅ | ⏳ | Android ✅；iOS 驱动缺失 |
| 2 | 场景 A：Chrome www.camel1.tv 赛事视频流 10 分钟 | ✅ | ✅ | ✅ | ✅ | ⏳ | fps 85 / 600s / 11 点 |
| 3 | 场景 B：小象直播 App 直播间 10 分钟 | ✅ | ✅ | ✅ | ✅ | ⏳ | fps 31.2 / 600s / 60 点，用户确认画面 |
| 4 | iOS（Safari + 小象）或阻塞登记 | ✅ | ✅ | ✅ | ✅ | ⏳ | solox 缺 iOS26.5 DeviceSupport |
| 5 | 证据 + QA/Leader 工件 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

## 📍 当前位置

```
Batch 99 — 真机性能验收（完成）
├── ✅ 场景 A：Chrome 赛事流 600s（fps 85 / CPU 3.55% / mem 182MB）
├── ✅ 场景 B：小象直播间 600s 60 点（fps 31.2 / CPU 386.65% / mem 795MB）
├── ✅ B99-P1 系列修复（fps/cpu/WS 重试，54 测试）
└── ⏳ iOS：solox 缺 iOS 26.5 DeviceSupport（CP-C2/C84-1 Open）
```
