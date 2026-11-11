# Batch 288 — Design / Dev

## 接口

```python
with PlaywrightDriver(evidence_dir=out) as drv:
    drv.login(url, user, pwd, username_selector=..., password_selector=...,
              submit_selector=..., success_selector=...)
    drv.click(...); drv.fill(...); drv.wait_for(...)
    files = drv.capture_evidence()   # → run_artifacts
```

## 证据

| 文件 | type | 说明 |
|------|------|------|
| dom.html | dom | 页面 HTML |
| a11y.json | a11y | accessibility snapshot |
| console.json | log | console 消息 + pageerror |
| screenshot.png | screenshot | full_page |
| trace.zip | trace | Playwright tracing |

每项 `{name,type,path,size_bytes,sha256}`，与 `run_artifacts` 字段对齐。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-288-1 | 延迟导入 playwright | 单测/CI 无浏览器也能跑 |
| D-288-2 | factory 注入 | fake 可完整验证调用序列与资源释放 |
| D-288-3 | 错误带 step 名 | UI 时间线可定位首个失败步骤 |
| D-288-4 | trace 由 capture 时 stop | 一次执行一份完整 trace，避免多次 stop |

## 文件

- `scripts/node/cameltv_node/drivers/playwright_driver.py`
- `scripts/node/cameltv_node/drivers/__init__.py`
- `tests/test_aiqe_playwright_driver.py`（5 条）
