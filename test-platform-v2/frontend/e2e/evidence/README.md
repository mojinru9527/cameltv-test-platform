# Batch 51 UI 回归证据

`batch51-ui-regression.spec.ts` 使用浏览器内 mock 数据检查 Batch 51 页面壳，不依赖后端或可复用账号。测试仍需要一个正在运行的前端 Vite 服务。

## 覆盖范围

- `/environment`、`/defect`、`/testcase`、`/testplan`、`/report`、`/trace`、`/requirement`
  - 1440×900、768×1024、390×844 三个视口
  - 每页只有一个可见 `h1`
  - 页面使用 Obsidian Flow 主题
  - 页面根节点无横向溢出
  - 无 `console.error`、`pageerror` 或失败请求
  - 桌面视口通过 WCAG A/AA axe 扫描
- `/workbench`、`/trace`、`/testcase`、`/environment`、`/theme-lab`
  - 三个视口各生成一张全页截图，共 15 张

## 本地执行

先在前端目录启动 Vite。当前 Agent Team worktree 的 `.env.local` 会使用 `5174` 端口：

```powershell
npm run dev -- --host 127.0.0.1
```

在另一个 PowerShell 窗口执行：

```powershell
$env:BASE_URL = 'http://127.0.0.1:5174'
$env:E2E_EVIDENCE_DIR = (Join-Path (Get-Location) 'test-results\batch51-ui-evidence')
.\node_modules\.bin\playwright.cmd test batch51-ui-regression.spec.ts --project=chromium
```

若不设置 `E2E_EVIDENCE_DIR`，截图会写入 Playwright 为每条测试创建的 `test-results` 输出目录。

## 证据命名

截图采用 `{page}-{viewport}-{width}x{height}.png`，例如：

```text
workbench-desktop-1440x900.png
trace-tablet-768x1024.png
theme-lab-mobile-390x844.png
```

回归失败时保留 Playwright trace、失败截图和视频，并在 QA 报告中记录失败页面、视口、axe 规则或运行时错误。
