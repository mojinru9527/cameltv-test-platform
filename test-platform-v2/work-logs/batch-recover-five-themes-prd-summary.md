# batch-recover-five-themes — PRD Summary

## 问题陈述

2026-07-19 发现：前几天实现的五套主题（晶穹 Crystal Command / 黑域 X-Lab / 列阵 Column Pulse / 软体 Clay Studio / 液境 Liquid Spectrum）代码**从未提交到 Git**，部分文件仅存在于磁盘未跟踪状态。具体断裂点：

- `themes.ts`（未跟踪）定义了新五主题注册表 + 旧主题迁移
- `theme-provider.tsx`（已提交）仍用旧四主题类型 `"blue" | "dark-minimal" | "warm" | "nature"`
- `globals.css`（已提交）仅有旧四主题 CSS，缺少 `[data-theme="liquid"]` 全部样式
- `auth.ts`（已提交）`ColorTheme` 类型仍是旧四主题
- `MainLayout.tsx`（已提交）`THEME_CONFIG` 仍是旧四主题配置

**根因**：工作树被外部进程重置，未提交代码丢失（见 memory `[[worktree-reset-hazard]]`）。

## 成功指标

1. TypeScript 类型检查通过
2. 21 个测试文件、93 条测试全部通过
3. 生产构建成功
4. 五套主题在 `[data-theme]` 层面完整可用（包括 liquid）
5. 旧版 `blue/dark-minimal/warm/nature` 配置可自动迁移到新 ID
6. 所有文件提交到 Git

## 非目标

- 不修改后端接口
- 不修改业务流程
- 不新增 UI 功能

## 用户故事

### US1: 作为平台用户，我可以在五套主题间切换
**Given** 已登录测试平台，**When** 打开主题选择器，**Then** 看到五套主题卡片（晶穹/黑域/列阵/软体/液境），点击即可切换。

### US2: 作为已有偏好的用户，我的旧主题自动迁移
**Given** localStorage 存储了 `cameltv-theme-color: "nature"`，**When** 加载页面，**Then** 自动映射为 "clay"（软体），不出错。

### US3: 作为项目管理员，每个项目记住其主题
**Given** 项目 A 选择了液境、项目 B 选择了黑域，**When** 切换项目，**Then** 自动切换到对应主题。

### US4: 液境主题覆盖所有组件
**Given** 切换到液境主题，**When** 浏览侧栏/顶栏/卡片/表格/Tabs/弹窗/进度/Skeleton/Spinner/Snackbar，**Then** 全部展示液态玻璃风格。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/lib/themes.ts` | 保留（git add） | 五主题注册表 |
| `frontend/src/lib/__tests__/themes.test.ts` | 保留（git add） | 注册表测试 |
| `frontend/src/components/theme-provider.tsx` | **重写** | 接入五主题系统 |
| `frontend/src/components/__tests__/theme-provider.test.tsx` | 保留（git add） | Provider 测试 |
| `frontend/src/globals.css` | **补全** | 添加 liquid 主题全部 CSS |
| `frontend/src/stores/auth.ts` | **修改** | 更新 ColorTheme 类型 |
| `frontend/src/layouts/MainLayout.tsx` | **修改** | 五主题选择器 |
| `frontend/src/theme-lab/` | 保留（git add） | 主题实验室 |
