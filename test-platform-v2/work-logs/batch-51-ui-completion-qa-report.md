# Batch 51 — UI 遗留问题清零 QA 报告

> QA | Date: 2026-07-28 | Branch: `feature/batch-51-ui-completion`

## 结论

Batch 50 遗留的已识别 UI 问题已完成修复，前端本地质量门禁和三视口浏览器回归通过。当前状态可进入推送确认和 Draft PR 阶段。

## 交付范围

- 统一 `PageShell`：environment、defect、testcase、testplan、report、trace、requirement 均只渲染一个页面级 `h1`，移除主题路径的重复页头。
- 完成 `@/ui` 基元兼容：Button、Input、Badge、Progress、Card、Select、Label、Textarea、Skeleton。
- Badge 生产消费者统一使用 `tone`；`variant` 仅保留兼容回归测试。
- 修复缺失的 `/defect` 路由。
- 修复移动端用例页、工作台指标、报告/知识库抽屉、专项测试和集成表单布局。
- 修复 DataTable 排序与可点击行的键盘操作、筛选器/图标按钮可访问名称、质量链 ARIA 角色和文本对比度。
- 修复非有限统计值渲染 `NaN`、隐藏 PlanDrawer 的无效请求、菜单加载失败静默、进度条宽度动画和过度弹跳动效。
- 新增 Batch 51 浏览器回归脚本与 15 张本地视觉证据。

## 自动化结果

| 检查 | 结果 |
|---|---|
| `npm run typecheck` | ✅ 退出码 0 |
| `npm run build` | ✅ 退出码 0 |
| `npm test` | ✅ 34 个文件 / 137 个测试全部通过 |
| Batch 51 Playwright（Chromium headed） | ✅ 36 / 36 |
| Axe WCAG A/AA（7 个核心页桌面视口） | ✅ 0 violation |
| 1440×900 / 768×1024 / 390×844 | ✅ 唯一 `h1`、无全局横向溢出 |
| 浏览器运行时 | ✅ 无 console error、page error、失败请求 |
| `git diff --check` | ✅ 通过 |

后端测试未运行：本批次差异分类为 frontend + docs，无后端代码变更。

## 基线对比

- 开工基线：29 个测试文件 / 125 个测试通过，但存在 RequirementPage `NaN` React 警告。
- 当前结果：34 个测试文件 / 137 个测试通过，`NaN` 警告消失。
- 开工构建警告中的 `useObsidianPage` 循环引用、`duration-[180ms]` 歧义和 Wiki 动静态混合导入均已消除。

## 视觉证据

本地证据目录：`test-platform-v2/frontend/e2e/evidence/`。PNG 被 `.gitignore` 排除，避免把运行产物纳入提交；回归说明和命名规则保留在该目录 README。

## 风险

风险等级：低。

- 改动面较广，但 Badge 迁移为语义等价替换，并有兼容别名兜底。
- 关键页面均覆盖三种视口；桌面核心页额外执行 Axe。
- 未推送、未创建 PR；后续仍受逐次 push 确认与 CI 门禁约束。
