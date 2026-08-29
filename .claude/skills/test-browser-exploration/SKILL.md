---
name: test-browser-exploration
description: 用于 AITDE V3.3 Browser Explore 模式（浏览器探索/首访理解）。Use when a browser session is in EXPLORE mode to discover paths/behaviours for first-time understanding, or when the AI needs to record navigation/click/input/XHR observations without affecting the frozen regression baseline. Triggers: "浏览器探索", "Explore 模式", "观测页面路径", "browser explore".
---

# 浏览器探索（Browser Exploration）

> AITDE V3.3 Browser Driver 四种模式之一（§5）。Explore 用于 AI 动态查找页面/路径以**首访理解**，不作为默认持续回归策略。

## 目标

- 动态理解页面结构、可用路径与关键交互
- 产出可复用的观测（Observation），供后续压缩成 Action Plan 候选

## 模式边界

| 模式 | 用途 | 是否产生 Command IR |
|---|---|---|
| EXPLORE | 首访理解页面/路径 | 只产出观测事件 |
| REGRESSION | 只执行已批准 CommandPlan | 否 |
| OBSERVE | Tester 操作，系统记录 | 压缩为 ActionPlan 候选 |
| MANUAL_ASSIST | Tester 手工操作，后台捕获 Oracle | 否 |

## 操作要求

- 会话经 `POST /api/v2/browser-sessions`（`mode=EXPLORE`）启动，`browser_type` 默认 `chromium`。
- 记录统一方法：`goto / click / fill / select / upload(Test only) / wait_for / capture_dom / capture_screenshot / capture_network`。
- Locator 优先级（§4）：data-testid → role+名字 → stable label → stable semantic text → CSS（最后）。**视觉坐标点击不作为默认策略。**
- 凭据脱敏是硬不变量：密码、token、authorization、cookie、secret 在写入语义/payload JSON 前必须 `<REDACTED>`。
- Explore 结论仅供理解，后续正式回归必须走 `REGRESSION` 模式的已批准 CommandPlan。

## Evidence

每次关键动作应能捕获 DOM / screenshot / network 证据，作为 Explore 结论的回放支撑；证据引用事件 id，保持可溯源。
