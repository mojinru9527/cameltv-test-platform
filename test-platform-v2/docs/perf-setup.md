# 客户端性能采集 — 环境搭建指南

> 版本: v1.0 | 最后更新: 2026-07-19

## 概述

测试平台性能采集模块基于开源引擎 [SoloX](https://github.com/smart-test-ti/SoloX)，对标 PerfDog 数据口径，支持 Android/iOS 双端零侵入实时性能数据采集。

### 支持平台

| 平台 | 最低版本 | 采集方式 | 前置依赖 |
|------|---------|---------|---------|
| Android | 8.0+ | ADB (USB / WiFi) | ADB |
| iOS | 14.0+ | tidevice (USB) | iTunes (Win) / tidevice |
| Web (后续) | Chrome 80+ | Performance API | 浏览器 |

## 快速开始

### 1. 安装 SoloX

```bash
pip install solox>=2.9
```

### 2. 安装平台前置依赖

#### Android

1. 安装 [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) (ADB)
2. 开启手机「开发者选项」→「USB 调试」
3. 连接设备后验证：

```bash
adb devices
# 应看到设备列表，状态为 "device"
```

#### iOS (Windows)

1. 安装 [iTunes](https://www.apple.com/itunes/) (Win 版)——提供设备驱动
2. 安装 tidevice：

```bash
pip install tidevice
```

3. 连接设备后验证：

```bash
tidevice list
# 应看到设备 UDID
```

> ⚠️ iOS 17+ 在 Windows 上可能不被支持（tidevice 已知限制）。遇到问题请优先用 Android 设备验证。

#### iOS (macOS)

```bash
pip install tidevice
tidevice list
```

### 3. 启动测试平台

```bash
cd test-platform-v2/backend
uvicorn app.main:app --reload --port 8000
```

### 4. 验证

1. 访问 `http://localhost:5173/perftest`
2. 确认「已连接设备」列表显示你的设备
3. 选择设备 → 选择 App → 勾选指标 → 创建会话 → 开始采集

## Mock 模式

未安装 SoloX 或无设备连接时，系统自动进入 Mock 模式：

- 显示 2 台模拟设备 (Pixel 7 / iPhone 15 Pro)
- 采集生成模拟性能数据（随机波动 + 偶发 Jank/ANR）
- 所有功能（创建会话 / 实时监控 / 报告 / 对比）均可用

适用于：前端开发调试 / 演示 / 无真机环境的 CI

## 常见问题

### Q: `adb devices` 显示 "unauthorized"
**A**: 手机上会弹出「允许 USB 调试」对话框，点击「允许」。如未弹出，执行 `adb kill-server && adb start-server` 重试。

### Q: SoloX 安装报错
**A**: 确保 Python ≥ 3.10：`python --version`

### Q: iOS 设备不显示
**A**: Windows 需安装 iTunes；检查 `tidevice list` 是否能看到设备。

### Q: 采集数据看起来不准
**A**: 确保：
- 没有其他性能监控工具同时运行（会争抢系统资源）
- USB 连接稳定（避免使用延长线/Hub）
- App 在前台运行（后台 App 的 CPU/GPU 数据不完整）

## 指标参考标准

| 指标 | 阈值 | 参考来源 |
|------|------|---------|
| FPS | ≥ 30 fps | Google Android Vitals |
| CPU | ≤ 60% | 行业通用 |
| 内存 | ≤ 512 MB | PerfDog 推荐（视设备调整） |
| 启动耗时 | ≤ 2000 ms | Google Android Vitals (冷启动) |
| Jank | 0 次 | PerfDog Jank 判定 |
| ANR/崩溃 | 0 次 | Google Android Vitals |
