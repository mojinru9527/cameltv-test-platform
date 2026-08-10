# Batch 142 — 全平台表单控件 / 弹窗 / 抽屉 UI 修复 PRD-lite
> **Product (🟦)** | Date: 2026-08-10 | Status: Approved

mode: light
豁免理由: 纯前端 UI 修复（含共享组件样式与弹窗/抽屉尺寸），无后端/接口/数据库变更，无新依赖（未引入新包，仅本地验证时修正 pnpm 构建脚本白名单，未纳入本批提交）。
非目标: 不新增/删除功能，不调整业务逻辑，不引入新接口或新配置项；构建脚本白名单（pnpm-workspace.yaml allowBuilds 占位符）记录为发现、不纳入本批。

## 1. 问题陈述
用户反馈「需求文档」页采集链路的三处显示问题：
1. **采集任务弹窗太小 / OCR 显示不全**：证据包 OCR 导入弹窗固定 560px、无最大高度与滚动，内容一高底部被截断；原型截图预览弹窗（含 OCR 文字）在部分视口下内容显示不全。
2. **采集选项勾选无任何变化、无法选择**：弹窗内的 Switch / Checkbox 点击后视觉不变。
3. **右侧边栏显示不全**：证据包任务右侧抽屉长链接溢出、内容显示不全；用户推断「整个平台所有右侧边栏 / 居中弹窗都有问题」。

### 审查结论（同类低级错误全量盘点）
对 `src/components/ui/**` 与构建产物（`dist/assets/index-*.css`）做比对，确认一批 **Tailwind v4 语法在 v3.4.17 下静默不编译** 的类，均属同一类低级错误，影响全平台：

| 失效写法（v4） | 影响组件 | 影响 |
|---|---|---|
| `data-checked:` / `data-unchecked:` | switch、checkbox | **开关/复选勾选视觉完全不响应（问题 2 根因）** |
| `data-disabled:` | switch、select、dropdown-menu | 禁用态透明度/指针样式缺失 |
| `data-inset:` | dropdown-menu | 菜单 inset 缩进失效 |
| `data-placeholder:` | select | 占位符灰色文字失效 |
| `data-selected:` / `group-data-selected:` | command | 命令项选中高亮失效 |
| `not-data-[...]:` | dropdown-menu、select、button(`not-aria-`) | 非破坏性项 focus 文字色失效 |
| `in-[[...]]:`（祖先选择器变体） | command、input-group、calendar、sidebar | 弹窗内圆角/焦点环/光标/透明背景失效 |
| `has-data-[...]:` / `has-disabled:` / `group-has-data-[...]:` | button、badge、tabs、tooltip、card、avatar、input-group、sidebar | 图标内边距、徽标、头像组尺寸、禁用态等失效 |
| `xxx!`（后缀 important，v3 需前缀 `!`） | command、badge、sidebar | 强制覆盖不生效 |
| `outline-hidden`（v3 无此工具类） | command、dropdown-menu、select、sidebar、popover | 焦点轮廓隐藏失效 |
| `*:[span]:last` | select | 选项文本布局失效 |

弹窗/抽屉系统性尺寸问题：
- `dialog.tsx` 基础 `DialogContent` 无 `max-h` + 滚动 → 高内容弹窗底部被截断（全平台居中弹窗）。
- `sheet.tsx` 基础 `SheetContent` 无纵向滚动、默认宽度 `sm:max-w-sm`(384px) 偏窄 → 全平台右侧边栏内容显示不全。
- `LanhuEvidenceDialog` / 新建采集任务弹窗 560px 无滚动 → 采集弹窗太小。
- `LanhuEvidenceJobDrawer` 长链接未断行溢出。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| Switch/Checkbox 勾选视觉 | 无变化 | 勾选有明确视觉反馈（颜色+滑块位移） | 本批验收 |
| 弹窗内容完整性 | 高内容底部截断 | 弹窗最大高度受限且内容可滚动，不超出视口 | 本批验收 |
| 右侧抽屉 | 长链接溢出/内容截断 | 内容纵向可滚动、长链接断行不溢出 | 本批验收 |
| 失效类样式编译 | 上述类全部 MISSING | 构建产物含对应规则（PRESENT） | 构建产物比对 |
| 回归 | - | typecheck/build/vitest 全绿，无新增失败 | 本批验收 |

## 3. 用户故事与验收标准
- As 用户, I want 采集弹窗中的开关/复选框勾选有明显变化, so that 我能确认采集选项已选中。
  - Given 打开证据包 OCR 导入弹窗 / When 点击任一采集选项开关 / Then 开关滑块移动且主色高亮、复选出现勾选标记。
- As 用户, I want 弹窗/抽屉内容完整可见, so that 截图、OCR、任务详情不被截断。
  - Given 任意居中弹窗或右侧抽屉 / When 内容高度超过视口 / Then 弹窗/抽屉内可滚动查看全部内容。
- As 用户, I want 长链接正常展示, so that 证据包任务链接不溢出面板。
  - Given 证据包任务抽屉 / Then 链接自动断行，不超出面板边界。

## 4. 技术方案要点
- 共享组件：`switch/checkbox/select/dropdown-menu/command/button/badge/tabs/tooltip/card/avatar/input-group/popover/sidebar/calendar` 将 v4 写法替换为 v3 等价写法（`data-[state=checked]:`、`data-[selected=true]:`、`data-[disabled]:`、`has-[[data-icon=...]]:`、`group-has-[[...]]:`、前缀 `!`、`outline-none` 等）；`in-[...]` 祖先变体改用命名组（`group/dialog-content` + `group-data-[slot=dialog-content]/...`）或按实际 DOM 用 `group-data-[side=...]` 等价表达，无对应 DOM 的死规则直接移除。
- 弹窗：`dialog.tsx` 基础加 `max-h-[calc(100dvh-2rem)] overflow-y-auto`；采集弹窗加宽到 `sm:max-w-[640px]` 并加 `max-h-[85vh] overflow-y-auto`；`LanhuEvidenceJobDrawer` 长链接 `break-all`。
- 原型预览：`PrototypePreview` 右侧 OCR/交互面板改为单一可滚动容器，避免交互说明被裁切。
- 验证：`pnpm run typecheck`、`pnpm run build`、受影响模块 vitest；构建产物比对确认先前 MISSING 类变为 PRESENT；必要时 dev server + 浏览器抽查。
