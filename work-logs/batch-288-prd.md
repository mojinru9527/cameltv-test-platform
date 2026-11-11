# Batch 288（M2 / TA-013）— Playwright Driver：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-288-m2-playwright-driver · **基线**：origin/main `2e345d1a1`

## 1. 问题

Runner 侧只有"整份 spec 执行"（`run_spec_files`），缺少结构化步骤驱动：无法在同一 Run 里
串后台登录 → 配置实体 → 前台查询，也无法按步骤产出 DOM/A11y/console/trace 证据。

## 2. 目标

1. `PlaywrightDriver`：start/close、goto/fill/click/wait_for/text、`login()` 组合动作；
2. 证据：`dom.html`、`a11y.json`、`console.json`（含 pageerror）、`screenshot.png`、`trace.zip`；
3. 每份证据含 size/sha256，可直接对应 `run_artifacts`；
4. 每步失败抛 `PlaywrightStepError(step, message)`；
5. playwright 延迟导入，无浏览器环境也可单测（fake factory 注入）。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 登录动作序列正确 | `test_login_sequence` |
| A2 | 五类证据齐全 + hash | `test_capture_evidence_files_and_manifest` |
| A3 | console/pageerror 收集 | 同上（console.json） |
| A4 | 步骤错误包装 | `test_step_error_wrapped` |
| A5 | 资源释放 | `test_close_releases_resources` |
| A6 | trace/screenshot 调用 | `test_trace_and_screenshot_calls` |
| A7 | 全量 + ratchet | CI |

## 4. 非目标

- 真实浏览器 E2E（后续节点真机验收）；
- 多浏览器矩阵（TA-015 capability）；
- 驱动注册表接入（TA-015）。
