# Batch 246 — Design Spec

> **Design (🎨)** | Date: 2026-09-15 | Status: 就绪

## 0. 技术体系确认

本批没有新增业务页面，设计对象是 **CI 门禁的开发者体验**：状态可见、失败可诊断、历史债可追踪、不得用假成功掩盖问题。

## 1. 门禁规格表

| 门禁 | 输入 | 失败条件 | 输出 |
|------|------|----------|------|
| Ruff ratchet | `ruff check app/ --output-format=json` | 新增 file/code/message occurrence | GitHub step 失败 + 新 finding 明细 |
| mypy ratchet | mypy 2.3.1 fixed command | 新增 occurrence | 同上 |
| pip-audit | backend requirements | 任一 known vulnerability | required backend 失败 |
| npm production audit | package-lock + prod deps | high/critical | required frontend 失败 |
| axe | Playwright WCAG A/AA | violation | required frontend 失败 |
| Lighthouse | `/login` accessibility | score < 0.9 | required frontend 失败 |

## 2. 布局与响应式

| 场景 | 规则 |
|------|------|
| scope 跳过 | job 仍返回明确的 success + skip reason，不留下 MISSING |
| 失败 | step 名称、命令、退出码、关键 finding 可见 |
| baseline 更新 | 只能通过显式 `--update`，输出各工具旧/新计数 |
| 开发依赖漏洞 | 生产审计必须 0；LHCI 开发链漏洞单独记录，不宣称全仓库 0 |

## 3. 状态设计核对（四态）

| 状态 | 展示 |
|------|------|
| 未触发 | “skipped: scope reason”摘要，不阻塞固定 required context |
| 运行中 | 标准 GitHub Actions 进度 |
| 失败 | 阻断，列出新增 finding / audit advisory / Lighthouse score |
| 成功 | 显示 baseline/current/new/removed 计数 |

## 4. 设计走查发现

### 🟠 P1-1 壳 fallback 吞错
事实：`lighthouse:a11y` 和 pr-check 的 Ruff/mypy 使用 `|| echo`，失败实际退出 0。
**建议**：删除 fallback，改用 ratchet 与 LHCI 配置固定失败语义。

### 🟠 P1-2 required 覆盖不足
事实：axe/Lighthouse、完整 Ruff/mypy、依赖审计不在 required job。
**建议**：直接在既有 required backend/frontend job 增加步骤，保持固定 context，不新增易漏配置的 job 名。

### 🟡 P2-1 行号漂移触发假回归
事实：静态分析 finding 常因新增代码导致行号整体移动。
**建议**：baseline 使用 file/code/message + occurrence count，而非 line/column。

### 🟡 P2-2 开发依赖审计噪声
事实：LHCI 工具链本身引入若干 dev-only advisory。
**建议**：required 门禁聚焦生产依赖；开发工具链风险在 QA 报告记录并持续跟踪上游升级。

## 5. 设计签核

结论：通过。门禁必须 fail closed，历史债务必须有精确 baseline，所有跳过态必须继续产出固定 required context。
