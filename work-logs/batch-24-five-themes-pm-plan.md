# Batch 24 PM Plan — 五套主题替换

> PM Department | 2026-07-20 | Est. 120 min

## 任务拆解

### Task 1: 更新 themes.ts 主题定义 (15 min)
- **描述**: 将 5 个主题的定义更新为 mockup 中的 5 套新主题
- **验收**: `COLOR_THEMES` 数组包含 5 个新主题（cyberpunk/apple/clay/xlab/liquid-glass），每个有正确的 id/label/description/preview/cssPreset/preferredMode
- **涉及文件**: `test-platform-v2/frontend/src/lib/themes.ts`

### Task 2: 重写 globals.css — 自定义属性层 (25 min)
- **描述**: 替换 5 套 CSS 预设的设计令牌块，将 mockup 中的 hex/rgba 颜色转换为 oklch
- **验收**: `[data-theme="cyberpunk"]`, `[data-theme="apple"]`, `[data-theme="clay"]`, `[data-theme="xlab"]`, `[data-theme="liquid-glass"]` 块全部替换，包含 light/dark 变体
- **涉及文件**: `test-platform-v2/frontend/src/globals.css` (lines 190-610)

### Task 3: 重写 globals.css — 组件差异化层 (25 min)
- **描述**: 替换 per-theme component styles，实现 mockup 中各主题的组件差异化
- **验收**: 卡片/侧栏/按钮/标签页/弹窗/Toast/进度条/骨架屏/徽章/表格/分页的 per-theme 样式正确
- **涉及文件**: `test-platform-v2/frontend/src/globals.css` (lines 612-1216)

### Task 4: 重写 globals.css — 交互效果层 (25 min)
- **描述**: 替换 per-theme interaction effects（7 个维度差异化）
- **验收**: 表格行 hover、标签页指示器、按钮按下反馈、选中行高亮、分页 active 态、侧栏菜单 hover、侧栏页脚的 per-theme 样式正确
- **涉及文件**: `test-platform-v2/frontend/src/globals.css` (lines 1217-1630)

### Task 5: 更新 theme-provider.tsx (10 min)
- **描述**: 更新 LEGACY_THEME_MAP 以保持向后兼容，确保旧用户 localStorage 中的主题 ID 能正确映射到新主题
- **验收**: 旧主题 ID (crystal/xlab/column/clay/liquid) 映射到最接近的新主题
- **涉及文件**: `test-platform-v2/frontend/src/components/theme-provider.tsx`

### Task 6: 更新 tests (10 min)
- **描述**: 更新 themes.test.ts 以匹配新的主题定义
- **验收**: 所有测试通过
- **涉及文件**: `test-platform-v2/frontend/src/lib/__tests__/themes.test.ts`

### Task 7: 视觉验证 (10 min)
- **描述**: 启动前端 dev server，切换 5 个主题验证视觉效果
- **验收**: 所有 5 个主题在浏览器中正确渲染，切换无闪烁

## 依赖关系

```
Task 1 → Task 2 → Task 3 → Task 4
Task 1 → Task 5
Task 1 → Task 6
Task 4 + Task 5 + Task 6 → Task 7
```

## 向后兼容映射

| 旧主题 ID | 旧 cssPreset | → 新主题 ID | 新 cssPreset |
|-----------|-------------|------------|-------------|
| crystal | blue | crystal | cyberpunk (暗) / apple (亮) |
| xlab | dark-minimal | xlab | xlab |
| column | warm | column | clay |
| clay | nature | clay-new | clay |
| liquid | liquid | liquid | liquid-glass |

策略：保留现有 5 个主题 ID 不变，仅替换 cssPreset 指向新的 CSS 实现。
