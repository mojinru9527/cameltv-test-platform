# 🗂️ Dev 部门项目看板 — Batch 99（真机性能验收）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | Android 滚动 fps 复测（C84-2）+ iOS 端到端（CP-C2/C84-1）（轻量批次） |
| **关联 PRD** | [batch-99-real-device-acceptance-prd-summary.md](../batch-99-real-device-acceptance-prd-summary.md) |
| **看板创建** | 2026-08-05 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-99-real-device-acceptance |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 环境探测（adb/tidevice/solox/venv） | ✅ | ✅ | ✅ | ✅ | ⏳ | Android ✅；iOS 驱动缺失 |
| 2 | Android 滚动场景采集 E2E | ✅ | ✅ | ✅ | ✅ | ⏳ | fps mean 59.38 PASS |
| 3 | iOS 采集（或阻塞登记） | ✅ | ✅ | ✅ | ✅ | ⏳ | 阻塞原因登记 |
| 4 | 证据 + QA/Leader 工件 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

## 📍 当前位置

```
Batch 99 — 真机性能验收（完成）
├── ✅ Android：fps mean 59.38 / max 117（120Hz），启动 314ms，C84-2 关闭
├── ✅ B99-P1 修复：自实现 SurfaceFlinger fps 解析（8 单测）
└── ⏳ iOS：CP-C2/C84-1 Open（缺 Apple Mobile Device 驱动，待安装）
```
