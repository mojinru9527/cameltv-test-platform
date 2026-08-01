# Batch 60 三视口全路由首轮证据

执行日期：2026-07-30
代码 SHA：`d15ed2197e41bbcecfac733f059160a912373317`
环境：Batch 60 local，真实 FastAPI + SQLite，Playwright Chromium headed

## 执行范围

使用 `frontend/e2e/batch56-full-platform-real-backend.spec.ts`：

- 桌面 `1440×900`，`obsidian-flow/dark`
- 平板 `768×1024`，`obsidian-flow/dark`
- 移动 `390×844`，`obsidian-flow/dark`
- 显式路由、隐藏/直达路由、动态计划/发布包详情
- 主内容、导航高亮、控制台、pageerror、失败请求/响应、重复有效 GET、页面溢出、Axe serious/critical

## 首轮结果

| 视口 | 结果 | 说明 |
| --- | --- | --- |
| 桌面 | PASS | 1/1，通过，35.8 秒 |
| 平板 | FAIL | 需求页和 Agent 页各出现一次 contrast 信号；主题实验室测试定位器超时 |
| 移动 | FAIL | 缺陷页 `scrollable-region-focusable` serious |

原串行运行在平板失败后未执行移动端；已使用相同脚本单独补跑移动用例。

## 独立复核

### 平板需求页与 Agent 工作台

在新的浏览器上下文、相同主题和视口重新注入同版本 Axe：

- `/requirement` serious/critical：0
- `/agent-workbench` serious/critical：0

截图：

- `TC-B60-A09-TABLET-REQ-recheck.png`
- `TC-B60-A09-TABLET-AGENT-recheck.png`

因此首轮两个对比度信号暂定为“不稳定、尚未复现”，不直接登记产品缺陷。后续全主题矩阵若再次出现，将保存具体节点 HTML、前景/背景色与组件状态。

### 平板主题实验室

页面在 `/theme-lab` 正常可见，截图有完整主题实验室内容；但测试等待的旧文案“测试平台 · 主题实验室”在当前可见 DOM 中为 0，body 文本也不存在。

结论：产品页面未白屏，验收脚本定位器已经漂移。关联 `B60-P1-022`。

截图：`TC-B60-A09-TABLET-THEME-LAB-visible.png`

### 移动端缺陷表格

Axe 独立复跑稳定得到：

```text
id: scrollable-region-focusable
impact: serious
target: .overflow-x-auto
html: <div data-slot="table-container" class="relative w-full overflow-x-auto">
failure: Element should have focusable content / Element should be focusable
```

运行数据：

```text
scrollWidth = 397
clientWidth = 356
tabindex = null
role = null
```

结论：表格确实需要横向滚动，但键盘无法聚焦滚动容器。关联 `B60-P1-021`。

截图：`TC-B60-A09-MOBILE-DEFECT-scroll-region.png`

## 判定

A09 当前为失败：桌面路由 smoke 通过不能抵消移动端 serious 无障碍失败。主题实验室脚本漂移同时使全路由矩阵本身不可靠，修复后须重跑桌面、平板和移动三组。
