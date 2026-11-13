# Batch 347b：UI / Android 设备执行器（2026-11-13）

> 在 batch-347 http 执行器基础上，为 AIQE 进程内执行器补充 `playwright`（UI）与 `appium`（Android 设备）分支，
> 并在本机用真实 Chromium 与已连接真机完成验证。

## 1. 能力

| driver | 输入（NodeRun.input_ref） | 结果语义 |
|--------|---------------------------|----------|
| `playwright` / `web` / `ui` | `url`、`click_text`/`click_selector`、`expect_text`、`inject_overlay`、`timeout_ms` | `PASSED`；点击不可用 → `CLICK_FAILED`；注入浮层后不可点 → `OVERLAY_INTERCEPTED`；文本不符 → `TEXT_MISMATCH`；无 Chromium → `BLOCKED/BROWSER_UNAVAILABLE` |
| `appium` / `android` / `mobile` | `appium_url`、`device_name`、`app_package`、`app_activity`、`expect_text`、`click_text` | `PASSED`；Appium 不可达 → `BLOCKED/APPIUM_UNAVAILABLE`；点击失败 → `DEVICE_CLICK_FAILED`；文本不符 → `TEXT_MISMATCH` |
| `http`（既有） | `url`、`method`、`expected_status` 等 | 不变 |

浮层注入用于 TC-004：执行器在页面内插入 `#aiqe-injected-overlay`（覆盖全屏），再对目标元素做 `click(trial=True)`，
被拦截即判定 `OVERLAY_INTERCEPTED`，不产生真实点击副作用。

## 2. 本机真实验证（Chromium）

固定 fixture 页（本地 HTML，含 `LIVE` 按钮）：

```json
[
  {"case": "core", "status": "PASSED", "detail": {"clickable": true, "expect_text_found": true}},
  {"case": "overlay", "status": "FAILED", "error": "OVERLAY_INTERCEPTED", "detail": {"clickable": false}},
  {"case": "text_mismatch", "status": "FAILED", "error": "TEXT_MISMATCH"}
]
```

## 3. 本机真实验证（Android 真机）

设备 `9f0564ba`（ONEPLUS A6010 / Android 11 / `com.camelrn`），Appium 3.9.0 + UiAutomator2：

```json
[
  {"case": "read_only", "status": "PASSED", "detail": {"source_len": 58667, "expect_text_found": true}},
  {"case": "click", "status": "PASSED", "detail": {"clicked": true, "expect_text_found": true}},
  {"case": "text_mismatch", "status": "FAILED", "error": "TEXT_MISMATCH"}
]
```

## 4. 边界

- Test 云主机当前**没有** Chromium/Appium/设备，UI/设备节点要在具备这些依赖的执行环境运行（本机已验证）；
- camel1.tv 的 WAF 仍拦截脚本化访问（见 `work-logs/aiqe/tc-004-camel1-waf-20261113.md`）；
  白名单或内部 Test 入口就绪后，用 `inject_overlay` 跑 TC-004 的 Core/Integration 两条 Run；
- 单元测试 7 条覆盖 dispatch、缺浏览器、缺 URL、Appium 会话/点击/文本/不可达、未知 driver。
