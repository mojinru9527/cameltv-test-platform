# Batch 24 PRD Summary — 五套主题替换

> Product Department | 2026-07-20

## 问题陈述

当前测试平台的 5 套主题（晶穹/黑域/列阵/软体/液境）的 CSS 实现与设计标签存在显著差距：
- `crystal`(晶穹) 声称 "Apple × Liquid Glass" → 实际是企业蓝
- `xlab`(黑域) 声称 "xAI × 轻赛博" → 实际是建筑单色暗黑
- `column`(列阵) 声称 "ClickHouse 工业数据" → 实际是温暖琥珀
- `clay`(软体) 声称 "企业黏土拟态" → 实际是自然绿色
- `liquid`(液境) 是唯一实现正确的（液态玻璃）

用户已在 `theme-mockup-v3.html` 中审阅并通过了 5 套全新主题的交互设计稿。

## 成功指标

1. 5 套新主题完整替换旧主题的 CSS 预设，视觉效果与 mockup 一致
2. 主题切换流畅（250ms transition），无闪烁
3. 所有现有组件在新主题下正确渲染（shadcn/ui + Radix）
4. 现有主题 ID 保持向后兼容（用户 localStorage 中的主题选择不丢失）

## 非目标

- 不新增 Progress Ring / Text Scramble 等新组件（由后续 batch 实现）
- 不修改主题选择器 UI（已有 ThemeLab）
- 不改变 light/dark mode 切换机制

## 用户故事

### US-1: 一键切换到赛博朋克终端风格
**Given** 测试工程师在夜间深度工作时
**When** 选择「赛博朋克」主题
**Then** 界面立即切换为暗黑终端美学：霓虹青主色、等宽字体、2px 锐利圆角、扫描线卡片高光、120ms steps 动画

### US-2: 日间管理使用 Apple 极简风格
**Given** 项目经理在日间审阅报告
**When** 选择「Apple」主题
**Then** 界面切换为亮色极简风格：大留白、10px 圆角、SF 式字体排版、微妙阴影、300ms iOS 缓动

### US-3: 演示场景使用黏土拟态
**Given** 对外演示测试平台能力
**When** 选择「黏土拟态」主题
**Then** 界面呈现柔和 3D 膨胀感：粉彩配色、14px 大圆角、双层阴影(外阴影+内高光)、280ms 弹性动画、按下内陷反馈

### US-4: Agent 工作台使用 AI 实验室风格
**Given** 开发人员在 Agent 工作台
**When** 选择「AI 实验室」主题
**Then** 界面切换为深色科技感：电光青主色、6px 精确圆角、等宽数据字体、180ms Material 缓动、IR 扫描线 Skeleton

### US-5: 沉浸式液态玻璃体验
**Given** 用户偏好丝滑连续操作的视觉体验
**When** 选择「液境·全景液态玻璃」主题
**Then** 界面呈现多层毛玻璃深度：侧栏 blur(28px)、卡片 blur(14px)、弹窗 blur(30px)、全景渐变 morphing 背景(18s 周期)、350ms 流体缓动

## 验收标准

- [ ] 5 套 CSS 预设 (`cyberpunk`, `apple`, `clay`, `xlab`, `liquid-glass`) 在 `globals.css` 中完整实现
- [ ] `themes.ts` 中的 5 个主题定义更新为新的 ID/label/description/preview/cssPreset
- [ ] `theme-provider.tsx` 中的 `LEGACY_THEME_MAP` 更新以保持向后兼容
- [ ] `DEFAULT_COLOR_THEME` 保持为向后兼容值
- [ ] CSS 变量体系与 shadcn/ui 兼容（--background, --foreground, --primary, 等）
- [ ] 每套主题的 dark/light 变体正确实现
- [ ] 所有 per-theme component styles 更新匹配新主题
