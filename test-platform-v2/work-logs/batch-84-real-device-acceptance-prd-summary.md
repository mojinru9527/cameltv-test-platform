# Batch 84 — PRD-lite（真机性能验收：CP-C1 Android 端到端采集）

> **Product (🟦)** | Date: 2026-08-04 | Status: Approved（用户确认执行器 Codex）

```markdown
mode: light
豁免理由: 本批为「验收/纯证据」批次——不引入新行为/新接口/新配置/新依赖（SoloX 采集链路 perf 模块已存在，仅做真机端到端验证与证据登记），符合 SKILL.md「批次模式」轻量判定。
非目标: 不新增/修改采集代码与接口；不引入新依赖（solox 为既有 perf_collector_service 的运行时依赖，仅在开发环境安装）；不做 iOS 采集（CP-C2 需 iPhone，用户未提供，保持 Open）。
```

## 1. 问题陈述

平台 perf 模块已实现 SoloX 真机采集封装（`perf_collector_service.py`），但从未用物理设备验证过
端到端链路（CP-C1/C2 自 2026-07-19 起 P0 Open，C74-3 待排期）。用户已提供 Android 真机
（OPPO Find X3 已 USB 连接），需完成：设备识别 → App 包名发现 → 采集会话 → 快照指标
（CPU/内存/FPS/电池/网络）→ 启动耗时 → 报告生成的全链路验证，并登记证据关闭 CP-C1。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 设备识别 | 无设备证据 | 平台 `/perf-sessions/devices` 返回 OPPO Find X3 | 本批 |
| App 发现 | 无 | adb 定位已安装 App 包名并登记 | 本批 |
| 采集链路 | 无 | 会话 start → 快照（≥4 项指标）→ stop → 报告 | 本批 |
| 启动耗时 | 无 | `am start -W` TotalTime 实测 | 本批 |
| 证据 | 无 | API 结果 JSON + 指标 + 设备信息入库 | 本批 |

## 3. 非目标

- 不做 iOS 真机采集（CP-C2）：需 iPhone + tidevice/iTunes，用户未提供，保持 Open。
- 不修改 perf 采集代码/接口/配置（验收批，若发现缺陷则登记为 C 条件或下批修复）。
- 不引入新依赖到 requirements（solox 仅在本地 venv 安装；如需入 requirements 属配置变更，走完整批次）。

## 4. 条件对账

- **纳入**：CP-C1（Android 真机采集端到端）、C74-3（真机性能验收排期）。
- **豁免/延后**：CP-C2（iOS，需 iPhone）；C79-1 等 WARN 消化与本批无关。

## 5. 前置条件（外部前置条件清单 4.1/4.2）

- 4.1 Android 真机：✅ OPPO Find X3（USB 已连接，待手机端 USB 调试授权）。
- 4.2 被测 App 包名：手机授权后经 `adb shell pm list packages` 按应用名定位登记。
