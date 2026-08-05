# Batch 99 — PRD-lite（真机性能验收：Android 复测 + iOS 端到端）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

```markdown
mode: light
豁免理由: 验收/证据批次（CP-C2/C84-1/C84-2 真机采集），无新接口/配置/依赖（solox/tidevice 为既有文档前置）；
按 pipeline-modes.md 判定轻量批次（PRD-lite + QA + Leader + 看板）。若发现平台缺陷则按缺陷处理并附修复切片。
非目标: 不引入新性能指标；不改采集引擎；不处理 V1 退役（顺延 Batch 100）；
滚动压测不作为完成证据（用户 2026-08-05 重定义：以视频流观看为验收口径）。
```

## 1. 问题陈述

性能监控模块（`/perftest`）依赖真实设备验收：

- **C84-2**：Android 复测（滚动/播放场景 fps 采样）——Batch 84 采集时 App 处于静态页，fps=0，登记待复测；
- **CP-C2 / C84-1**：iOS 真机采集端到端（tidevice 链）——此前用户未提供 iPhone，保持 Open；
- 用户 2026-08-05 反馈 Android + iOS 设备已连接，本批执行采集、登记证据并关闭或转缺陷。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| Android 设备识别 | Batch 84：OPPO Find X3（PEDM00/Android 14） | 复测识别 + com.camelrn 包名 |
| 场景 A：浏览器赛事视频流 | 未按此口径验收 | 安卓 Chrome 打开 www.camel1.tv → 任选有视频流比赛 → 观看 **10 分钟** fps/cpu/内存采样 |
| 场景 B：小象直播 App | 未按此口径验收 | 任选一个视频流直播间观看 **10 分钟** 采样 |
| iOS 采集 | 未执行 | 若 Apple 驱动可用：Safari + 小象 iOS 同口径；不可用则如实登记阻塞 |
| 证据 | — | `real-device-collection-batch99.json` + 截图/日志 |

## 3. 用户故事 + 验收标准

- As a **性能验收负责人**, I want 真实视频流观看场景（浏览器赛事 / 小象直播间）各 10 分钟采样，so that C84-2 按用户口径关闭。
- As a **iOS 验收负责人**, I want iPhone 端到端采集，so that CP-C2/C84-1 可关闭；驱动缺失时如实登记阻塞。

Given 设备已连接且采集会话完成，When 读取样本与报告，Then fps 场景数据可复核且无伪造。
