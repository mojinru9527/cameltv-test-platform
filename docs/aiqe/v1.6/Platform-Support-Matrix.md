# V1.6 平台支持矩阵与边界（V16-016）

> 原则：**声明 ≠ VERIFIED**。只有真实 Runner/设备/环境 + 执行记录 + Artifact 证据才能 VERIFIED。
> 未完成平台必须列入"V1.6 GA 不支持清单"，不得对客户宣称 VERIFIED。
> 最后核对：2026-11-20（V1.6 开发分支）

## 1. GA 支持矩阵

| Platform | 状态 | GA 支持 | 证据 | 说明 |
|---|---|---|---|---|
| Web / Playwright (Chromium 149) | **VERIFIED** | ✅ | V16-002 真实拦截/egress/redirect/WS 测试 + V16-015 验收 Run | 生产默认唯一 GA 平台 |
| Android / Appium | **AVAILABLE** | ❌ | 本机 Appium smoke；无真实设备池验收 | 需设备池 + Capability Verification Run 后升级 |
| iOS | **BLOCKED** | ❌ | `DeviceBroker.IOS_ENABLED=false`（C84-1） | 无签名/证书/WDA/设备池 |
| 微信小程序 | **BLOCKED** | ❌ | 无真机/微信容器 Runner | WebView 测试不等同小程序原生能力 |
| Desktop（Win/macOS） | **BLOCKED** | ❌ | 无 Adapter/Runner | 不纳入 GA |
| IoT / 硬件 | **BLOCKED** | ❌ | 无 Adapter/Runner | 不纳入 GA |

代码事实源：`app/aiqe/services/platform_support.py`（`PLATFORM_CLAIM` / `ga_matrix()`），Preflight 对未支持动作返回 `PLATFORM_ACTION_UNSUPPORTED`。

## 2. 动作粒度（Preflight 强制）

| Platform | 支持动作 |
|---|---|
| web | navigate, click, input, screenshot, assert, evaluate, wait, upload, download, cleanup |
| android | install, launch, permission, click, input, screenshot, performance, cleanup |
| ios / miniapp / desktop / iot | （无）任何动作 → BLOCKED |

未在表中的动作必须在 Preflight 阶段拒绝，禁止运行中静默跳过。

## 3. 设备与租约（DeviceBroker）

- 设备注册：platform 必须属于 `android/ios`；iOS 在 C84-1 解除前拒绝；
- 分配：单设备同一时刻只有一个 `busy` 租约；`lease_seconds` 默认 300s；
- 到期回收：`reap_expired(now)` 将过期 `busy` 释放为 `available`，原因 `LEASE_EXPIRED`；
- 断连：`mark_offline` → 不可分配；`recover` 后才恢复；
- 崩溃恢复：Reconciler/设备巡检必须周期性调用 `reap_expired`，避免永久占用。

## 4. PlatformBinding 字段

`project_id`、`environment_id`、`platform_id`、`device_pool`、`node_id`、`runner_version`、
`driver_name/version`、`device_model`、`os_version`、`browser_or_app_version`、
`capability_status`（服务端计算）、`evidence_refs_json`。

客户端不得自报 `VERIFIED`；状态由 Capability Registry 计算（V16-015）。

## 5. V1.6 GA 明确不支持清单

- iOS 真机自动化（签名、WDA、设备池未完成）
- 微信小程序原生自动化（仅可声明"WebView 页面测试"）
- Desktop / IoT 自动化
- Android 真机 VERIFIED 声明（仅 AVAILABLE）

以上平台在发布报告、销售材料、API Capability 响应中必须显示 BLOCKED/AVAILABLE，不得显示 VERIFIED。
