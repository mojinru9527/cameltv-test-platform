# Batch 52 — 黑曜流界主题收口 QA 报告

> QA | Date: 2026-07-28 | Branch: `feature/batch-52-obsidian-theme-refresh`

## 结论

黑曜流界此前未完成的 P0/P1 项已关闭：双主题状态已移除，主题首屏与实时消费者一致，语义色、对比度、触控热区、检查器键盘行为和三档响应式均通过自动化验证。当前状态可进入提交、逐次 push 确认和 Draft PR 阶段。

由于黑曜主题在本批次开始时并未完成，用户设定的前置条件不成立；现有 5 套主题的全面视觉刷新未在本分支启动。六套主题仍已统一到同一生产注册表，并完成切换契约回归。

## 交付范围

- 将 Obsidian Flow 注册为第 6 套正式、深色专属主题，并维持为默认首屏主题。
- 移除双 Provider 主题所有权；旧 `UiThemeProvider` 降级为无状态兼容适配器。
- 统一首屏脚本、全局主题、项目主题、历史主题迁移和持久化回写。
- 图表、Sonner、Theme Lab 样式加载改为跟随实时主题。
- 重建黑曜语义令牌和单一 CSS 选择器，修复 hover、文本、原生控件、玻璃回退和 reduced-transparency。
- SpatialChain 与 Inspector 去除嵌入色值，补齐对比度、响应式宽度、Escape、焦点闭环与焦点恢复。
- 修复 API 调试、性能测试、发布包等已审计图标按钮名称；移动端顶栏关键操作满足 44×44px。
- 移除生产代码不再使用的 `next-themes` 依赖。
- 新增 10 个主题/组件测试文件或测试组，以及 Batch 52 六主题浏览器回归。

## 自动化结果

| 检查 | 结果 |
|---|---|
| `npm ci` | ✅ 退出码 0；锁文件一致 |
| `npm run typecheck` | ✅ 退出码 0 |
| `npm run build` | ✅ 退出码 0 |
| `npm test` | ✅ 42 个文件 / 171 个测试全部通过 |
| Batch 52 Playwright（Chromium headed） | ✅ 5 / 5 |
| Batch 51 核心页面回归（Chromium headed） | ✅ 36 / 36 |
| 六主题实时切换 | ✅ 6 个唯一生产令牌签名，根属性一致 |
| Axe WCAG A/AA | ✅ Batch 52 工作台与 7 个核心页均 0 violation |
| 390×844 / 768×1024 / 1440×900 | ✅ 无全局横向溢出 |
| 浏览器运行时 | ✅ 无 console error、page error |
| `git diff --check` | ✅ 通过 |
| 调试遗留/凭据扫描 | ✅ 无新增命中 |

浏览器视觉证据由 `e2e/batch52-theme-regression.spec.ts` 生成到 `frontend/e2e/evidence/`；PNG 受仓库忽略规则保护，不进入提交。

后端测试未运行：本批次差异分类为 frontend + work-logs，无后端代码、API 或数据库变更。

## 缺陷发现与回归

浏览器回归首次发现 SpatialChain 的 6 个序号节点在黑曜 hover 色上存在严重对比度违规。修复方式是把 hover 从实心主色调整为 12% 语义混合，并增加明确的 hover 前景令牌；定向 Axe 和完整 36 项核心页面回归随后全部通过。

移动端热区断言首次发现主题按钮受高特异性 `.ui-btn-sm` 规则限制为 32px。最终通过明确的 44px 最小尺寸覆盖修复，并在 390px 视口下加入主题、侧栏和用户菜单三个关键操作的像素级断言。

## 基线与已知债务

- `npm audit` 仍报告 2 个 moderate 依赖问题，为开工基线；本批次未使用破坏性 `--force` 升级。
- Vitest 仍输出 React Router v7 future-flag 提示，不影响测试结果。
- 主干审计记录到 32 个既有文件中有 43 个异步 `useEffect` 未统一采用清理模式，集成模块另有 2 个 `page_size: 1` 探测请求；这些不由本分支引入。本批次新增或修改的主题异步 effect 均有清理。
- 全量五主题组件视觉重制属于后续版本候选，需在本批次合入主干并通过 CI 后重新立项。

## 风险

风险等级：低至中。

- 主题根契约是全局改动，但有首屏、Provider、六主题切换、完整单测和 41 项浏览器回归共同覆盖。
- 黑曜为深色专属，历史浅色偏好会被归一并持久化；这是明确设计，不是静默丢失。
- 未推送、未创建 PR；后续仍受每次 push 的用户确认、required checks 和 Agent Team 最终审计约束。
