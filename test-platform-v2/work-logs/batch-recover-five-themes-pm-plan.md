# batch-recover-five-themes — PM Plan

## 任务拆解 (每项 15–30 min)

### T1: 更新 `auth.ts` ColorTheme 类型 (5 min)
- 从 `@/lib/themes` 导入 `ColorTheme` 替代硬编码 union
- 验收：`useAuthStore` 的 `colorTheme` 字段接受五主题 ID

### T2: 重写 `theme-provider.tsx` (25 min)
- 导入 `normalizeColorTheme`, `getThemeCssPreset`, `DEFAULT_COLOR_THEME` from `@/lib/themes`
- 存储新五主题 ID
- localStorage 读取时用 `normalizeColorTheme` 兼容旧值
- 应用 `data-theme`(CSS preset) + `data-theme-id`(新 ID) 到 root
- 支持 reduced-motion 降级
- 验收：测试文件 `theme-provider.test.tsx` 通过

### T3: 补全 `globals.css` liquid 主题 CSS (20 min)
- 添加 `[data-theme="liquid"]` + `.dark[data-theme="liquid"]` 基础变量
- 添加 density/animation/glass/neon 变量
- 添加组件差异化样式（卡片/侧栏/表格/Tabs/弹窗/输入框/徽章/提示框/分割线/下拉菜单）
- 添加交互效果（悬停/选中行/分页/侧栏/骨架屏/闪烁）
- 验收：液境主题 CSS 覆盖所有 8 类组件

### T4: 更新 `MainLayout.tsx` 主题选择器 (15 min)
- 导入 `COLOR_THEMES`, `getThemeDefinition` from `@/lib/themes`
- 替换 `THEME_CONFIG` 硬编码为 `COLOR_THEMES` 驱动
- 五主题卡片网格
- 验收：主题切换器显示五套主题

### T5: git add + 验证 + commit (15 min)
- `git add` 所有文件
- TypeScript 类型检查
- vitest 测试
- vite build
- git commit
- 验收：CI 通过

## 涉及文件参考

| 任务 | 文件 | 参考 |
|------|------|------|
| T1 | `src/stores/auth.ts:5` | `src/lib/themes.ts` ColorTheme 类型 |
| T2 | `src/components/theme-provider.tsx` | `src/lib/themes.ts` normalizeColorTheme |
| T3 | `src/globals.css` | 现有 4 个主题块为模板 |
| T4 | `src/layouts/MainLayout.tsx:93-118` | `src/lib/themes.ts` COLOR_THEMES |
