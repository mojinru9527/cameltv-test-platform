# Batch client-perf — PRD Summary

> **Product (🟦)** | Date: 2026-07-19 | Status: Draft

## 1. 问题陈述

### 用户痛点

测试平台目前缺少**客户端性能采集能力**。现有专项测试模块（`/special`）仅覆盖音视频流媒体质量（ffprobe 探测 + 人工采样），无法回答以下关键问题：

- App 某个版本在指定设备上的帧率稳定性如何？
- 新版本相比上一版，CPU/内存是否有回归？
- 长时间直播播放是否导致内存泄漏/ OOM？
- 冷启动耗时是否满足体验基准（< 2s）？
- 弹幕密集滚动时是否产生 Jank 卡顿？

### 现状证据

- 团队之前使用腾讯 PerfDog，但因付费策略变化无法继续使用
- PerfDog 交互好、指标标准，但无法定制化扩展（如自定义采样间隔、自定义指标、与测试计划联动）
- 探索报告（2026-07-19）：仓库中 **零性能监控基础设施**——无性能相关 DB 模型、无 WebSocket、无设备采集 Agent

### 为什么用户关心

QA 需要一套**免费、可定制、与测试平台深度集成**的客户端性能采集工具，能：

1. 在测试计划执行时同步采集性能数据
2. 跨版本对比性能趋势（回归检测）
3. 生成符合行业标准的性能报告
4. 指标口径对标 PerfDog / Google Android Vitals / Apple MetricKit

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 支持的平台 | 0 | Android + iOS | V1 交付 |
| 支持的指标数 | 0 | 6 项（FPS/CPU/Mem/Jank/启动/ANR） | V1 交付 |
| 实时数据延迟 | 无 | < 500ms（与 SoloX 默认采集间隔一致） | 压测 10 分钟 |
| 性能报告生成 | 无 | 1 次采集 → 1 份报告（含统计摘要 + 图表） | 每次采集 |
| 历史趋势查询 | 无 | 同一 App+版本 可对比最近 5 次采集 | V1 交付 |
| 设备兼容性 | 无 | Android 8+ / iOS 14+ | 实测 ≥ 3 款设备 |
| 零侵入采集 | N/A | 无需 App 嵌入 SDK、无需 root/越狱 | 每次采集 |

## 3. 非目标（本次不做）

- **Web 端性能采集**（LCP/FID/CLS）——优先级低，Phase 3
- **Windows 客户端性能采集**——Phase 4
- **GPU 使用率采集**——仅 Qualcomm 平台可比较，Phase 2
- **电池/功耗采集**——依赖设备传感器可用性，Phase 2
- **屏幕录制/回放**——SoloX 支持但 MVP 暂不暴露
- **云设备农场对接**（STF / Device Farm）——MVP 仅支持本地 USB 设备
- **CI/CD Pipeline 自动性能回归门禁**——需性能基线积累后才有意义

## 4. 用户故事 + 验收标准

### US-1: 设备管理

**As a** QA 测试人员
**I want** 查看当前 PC 连接的 Android/iOS 设备列表及状态
**So that** 我能选择目标设备开始性能采集

**验收标准：**
- Given PC 连接了 1 台 Android 设备 + 1 台 iOS 设备
- When 进入「性能测试」页面
- Then 看到设备列表，显示设备名称、型号、系统版本、连接状态、已安装的目标 App 列表

### US-2: 性能采集会话

**As a** QA 测试人员
**I want** 选择设备 + App → 选择采集指标 → 启动/停止采集
**So that** 我能获取指定时长内的性能数据

**验收标准：**
- Given 已选择设备 `Pixel 7` + App `com.cameltv.app`
- When 勾选 FPS + CPU + Memory + Jank + 启动耗时，设置采集时长 300s，点击「开始采集」
- Then 实时展示各指标时序曲线图，采集结束后自动保存会话数据

### US-3: 实时数据可视化

**As a** QA 测试人员
**I want** 采集过程中实时看到 FPS、CPU、内存等指标的时序曲线
**So that** 我能快速发现性能异常点（如 FPS 骤降、内存突增）

**验收标准：**
- Given 采集正在运行中
- When 每 500ms 收到一次新数据点
- Then 曲线图滚动更新，显示最近 60s 数据窗口，滑动可查看历史全量

### US-4: 采集报告

**As a** QA 测试人员
**I want** 每次采集结束后自动生成统计报告
**So that** 我能拿到平均值/P95/最小值/最大值/标准差等统计数据

**验收标准：**
- Given 一次 300s 采集刚结束
- When 点击「查看报告」
- Then 显示每个指标的统计摘要（样本数/均值/中位数/P95/最小/最大/标准差），含异常点标注（如 Jank 次数、FPS 低于阈值时段）

### US-5: 历史对比

**As a** QA 测试人员
**I want** 对比同一 App 两次采集的性能数据
**So that** 我能判断新版本是否有性能回归

**验收标准：**
- Given 同一设备上有 v1.0 和 v1.1 两次采集记录
- When 选择两者进行对比
- Then 并排显示两次采集的关键指标差异（Δ FPS、Δ CPU%、Δ 内存 MB），差异 > 阈值时红色高亮

### US-6: ANR/崩溃记录

**As a** QA 测试人员
**I want** 采集过程中自动捕获 ANR 和崩溃事件
**So that** 我能关联崩溃时间点与性能曲线

**验收标准：**
- Given 采集过程中 App 发生 ANR 或崩溃
- When 采集结束
- Then 报告中在对应时间轴标注崩溃/ANR 事件，含时间戳和 logcat 摘录

## 5. 技术考量

### 依赖项

| 依赖 | 用途 | 风险 | 缓解 |
|------|------|------|------|
| **SoloX** (PyPI: `solox`) | Android/iOS 性能采集引擎 | 社区项目，可能停更 | 锁定版本，评估 fork 能力 |
| **ADB** | Android 设备通信 | PC 已安装 | 检测 `adb --version`，无则提示安装 |
| **tidevice** | iOS 设备通信（Windows/Linux 可用） | iTunes 驱动依赖（Win） | 检测 tidevice 是否可用 |
| **WebSocket** (FastAPI built-in) | 实时数据推送前端 | 需新增基础设施 | MVP 用 500ms 轮询兜底 |

### 架构决策

```
┌──────────────┐     USB/WiFi      ┌──────────────────┐
│ Android/iOS  │ ←───────────────→ │ PC (测试执行机)    │
│   设备        │   ADB / tidevice  │                  │
└──────────────┘                   │ SoloX Python API │
                                   │   ↓              │
                                   │ FastAPI Service  │
                                   │   ↓         ↓    │
                                   │ SQLite    WebSocket
                                   │ (时序)    (实时)  │
                                   └──────┬──────┬────┘
                                          │      │
                                   ┌──────┴──────┴────┐
                                   │  前端 (React)     │
                                   │  Recharts 曲线图  │
                                   └──────────────────┘
```

集成策略：**Wrap, not Fork** ——不修改 SoloX 源码，通过 `solox` 包提供的 `AppPerformanceMonitor` Python API 做轻量封装。

### 已知风险

1. **iOS 17+ 在 Windows 上不支持**（SoloX FAQ 已注明）——需文档说明
2. **GPU 指标仅限 Qualcomm 平台**——MVP 不纳入
3. **`tidevice` + iTunes 安装配置对 Windows 用户有一定门槛**——需提供 setup 脚本

## 6. 上线计划

| 阶段 | 受众 | 关键交付 | 成功门槛 |
|------|------|---------|---------|
| Slice 1: 后端基础设施 | Dev 团队 | DB 模型 + WebSocket + SoloX 封装服务 | SoloX API 调用成功返回指标数据 |
| Slice 2: 前端 + 实时展示 | QA 团队 | 设备选择 + 采集控制 + Recharts 实时曲线 | 1 台 Android 设备成功采集并展示 |
| Slice 3: 报告 + 历史对比 | QA 团队 | 统计摘要 + 历史对比 + ANR 检测 | 2 次采集可对比出差异 |
| Slice 4: iOS 适配 | QA 团队 | tidevice 集成 + iOS 设备实测 | 1 台 iOS 设备成功采集（Win/Linux） |
| Slice 5: 文档 + 上线 | 全员 | setup 脚本 + 用户文档 + ADR | 团队成员可独立完成一次采集 |
