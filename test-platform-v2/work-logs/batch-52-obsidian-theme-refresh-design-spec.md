# Batch 52 — 黑曜流界主题收口 Design Spec

> Design | Date: 2026-07-28 | Theme contract: `1.1.0`

## 设计结论

黑曜流界（Obsidian Flow）从独立 UI 覆盖层升级为第 6 套正式主题，继续作为新用户默认主题。主题选择、明暗模式、项目偏好、首屏渲染、图表和通知全部读取同一个 `ThemeProvider` 状态，不再由两个 Provider 分别写入 DOM 和本地存储。

本批次只收口黑曜主题及其共用组件契约。用户要求的“再刷新现有 5 套主题”以黑曜已经全部完成为前提；审计确认前提不成立，因此未启动五主题视觉重制。

## 单一主题状态

```text
ThemeProvider
├─ mode: light | dark | system
├─ colorTheme: 01…06
├─ localStorage
│  ├─ cameltv-theme-mode
│  └─ cameltv-theme-color
└─ <html>
   ├─ class="light|dark"
   ├─ data-theme="{cssPreset}"
   ├─ data-theme-id="{themeId}"
   └─ data-ui-theme="obsidian-flow" 仅作为旧消费者兼容信号
```

- `UiThemeProvider` 只保留旧 API 适配，不再持有状态、存储或 DOM 属性。
- 黑曜流界声明 `supportedModes: ['dark']`；无论历史值或用户请求为何，都会归一到深色。
- 旧主题值 `blue/crystal/dark-minimal/warm/column/nature/liquid` 在首屏脚本和 React Provider 中使用同一映射迁移，并回写为正式主题 ID。
- 首屏内联脚本在 React 加载前写入根属性，避免闪回错误主题。

## 六主题注册表

| 编号 | ID | 名称 | 模式 |
|---|---|---|---|
| 01 | `cyberpunk` | Cyberpunk Terminal | light / dark / system |
| 02 | `apple` | Apple Minimal | light / dark / system |
| 03 | `clay` | Clay Studio | light / dark / system |
| 04 | `xlab` | X-Lab | light / dark / system |
| 05 | `liquid-glass` | Liquid Glass Panoramic | light / dark / system |
| 06 | `obsidian-flow` | Obsidian Flow | dark only |

## 黑曜视觉规则

- 画布：`#0b100d`；卡片：`#141c17`；主要文字：`#eef6f0`；次要文字：`#91a398`；操作色：`#35e68a`。
- 主要文字/画布对比度 17.43:1，次要文字/卡片对比度 6.54:1，均满足 WCAG AA。
- 玻璃材质只用于导航、检查器和空间链路等有层级价值的表面；数据卡片和表格保持稳定、克制的实色层级。
- Hover 使用 12% 主色混合，不再把整块表面刷成高亮绿；前景色通过 `--color-hover-text` 明确定义。
- 原生日期等表单控件通过 `color-scheme` 跟随 light/dark 根类。
- 动效遵循 reduced-motion；Liquid Glass 同时修复 reduced-transparency 同元素选择器，并提供不支持 `backdrop-filter` 时的实色回退。

## 共用组件规则

### SpatialChain

- 表面、边框、文本、状态、进度全部改用产品语义令牌。
- 链路序号使用 hover 前景语义色，修复黑曜主题下 6 个节点的对比度违规。
- 保留 chain/grid 两种布局，移动端继续横向滚动，不产生全局溢出。

### Inspector

- 宽度限制为 `min(100vw, 380px)`，自定义宽度仍受 `max-width: 100%` 约束。
- 支持 Escape 关闭、Tab 焦点闭环和关闭后焦点恢复。
- 关闭按钮和关键移动端顶栏操作的有效热区不小于 44×44px。

### 实时消费者

- 图表在主题或模式变化后的下一帧重新读取 CSS 变量，并在卸载时取消回调。
- Sonner 直接读取仓库主题上下文；system 模式监听系统配色并清理监听器。
- Theme Lab 样式只在实验室入口加载，不再进入生产首包。

## 无障碍与响应式

- 390×844、768×1024、1440×900 三档视口作为正式验收尺寸。
- 页面切换后焦点移动到 `main-content`。
- 已审计图标按钮补充中文可访问名称，装饰图标从可访问树隐藏。
- 黑曜桌面工作台及 7 个核心页面执行 Axe WCAG A/AA 扫描，要求 0 violation。
