# Batch 277b-3 — 节点 spec 执行器修复（本地 E2E）：PRD-lite

> **部门**：🟦 Product（lite） · **日期**：2026-11-09 · **Executor**：DeepSeek Harness
> **批次模式**：light（修复 + 证据） · **分支**：fix/batch-277b-3-node-spec-runner-fix（基线 `e7d744952`）

## 1. 问题

277b-1 合入后发现节点 `run_spec_files` 在真实 Playwright 下跑不起来：

1. `_playwright_root()` 指向不存在的 `test-platform-v2/tests/playwright`（实际在 `backend/tests/playwright`）；
2. spec 文件名 `x.spec.node<id>.ts` 不匹配 Playwright `*.spec.ts` glob → `No tests found`；
3. 子进程 `text=True` 在 Windows 用 GBK 解码 → `UnicodeDecodeError`；
4. 未传 `--project/--reporter` → 3 个 project 里 firefox/webkit 未安装，用例"失败"。

## 2. 成功指标

| 指标 | 阈值 | 结果 |
|------|------|:----:|
| 真实 Chromium 跑通节点 spec | 1/1 pass | ✅ |
| 本地 `/uitest` 全链路（HTTP → ExecutionJob → node → UiTestRun） | status=done | ✅ |
| 单测不污染仓库（spec 写临时目录） | 0 残留 | ✅ |
| 单测/质量 ratchet | 全绿 | ✅ |

## 3. 非目标

- 不改控制面 Dockerfile / 默认模式（仍 local）；
- 不处理蓝湖截图 / XHR 采集 / Playground 的浏览器依赖；
- 未上生产。

## 4. DoD

- [x] 4 个缺陷修复 + 12 条单测；
- [x] 本地 E2E 证据（`work-logs/p0-evidence/P0-4-local-e2e.md`）；
- [ ] PR checks 绿后合入。
