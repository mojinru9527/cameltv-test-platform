# Batch 50 — QA 报告

> **QA (🔍)** | Date: 2026-07-28 | Verdict: **PASS**

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 15 | 15 | 0 | 0 |

## 可执行门禁

### 前端

| 检查项 | 命令 | 退出码 | 结果 |
|--------|------|--------|------|
| TypeScript 类型检查 | `npx tsc --noEmit` | 2 | ✅ 仅预存 `deep-eql` 类型定义缺失（vitest 依赖），零新增类型错误 |
| Vite 构建 | `npx vite build` | 0 | ✅ 9.01s，所有 chunk 正确打包（含 ThemeLab 39.10 kB） |
| 前端服务 | `curl localhost:5173` | 0 | ✅ HTTP 200 |

### 后端

| 检查项 | 命令 | 退出码 | 结果 |
|--------|------|--------|------|
| Health 端点 | `curl localhost:8002/health` | 0 | ✅ `{"status":"ok","version":"2.1.0"}` |
| Environments API | `curl /api/v1/environments?project_id=1` | 0 | ✅ 401（需认证）— 非 500 |
| TestCases API | `curl /api/v1/test-cases` | 0 | ✅ 401 — 非 500 |
| Requirements API | `curl /api/v1/requirements` | 0 | ✅ 401 — 非 500 |
| TestPlans API | `curl /api/v1/test-plans` | 0 | ✅ 401 — 非 500 |

## 逐条件验证

### C1: Badge 组件替换 (PRD US-1)
**变更文件**: 10 个页面文件
| 检查项 | 结果 | 说明 |
|--------|------|------|
| shadcn Badge import 已替换为 @/ui | ✅ PASS | 所有核心页面 Badge 走 @/ui |
| variant 映射正确 (default→neutral, destructive→danger, outline→neutral, secondary→neutral) | ✅ PASS | 语义映射：status=success, priority=danger, review=info |
| TypeScript 类型通过 | ✅ PASS | 零新增错误 |
| BadgeTone 类型导入正确 | ✅ PASS | 页面级 STATUS_MAP 类型从 variant 迁移到 tone |

### C2: CSS 类强化 (PRD US-1)
**变更文件**: 所有页面 Card/Table 元素
| 检查项 | 结果 | 说明 |
|--------|------|------|
| .ui-surface 应用于 Card 组件 | ✅ PASS | trace(3), report(6), requirement(5), environment(1), testcase(1) |
| .ui-table 应用于 Table 组件 | ✅ PASS | report, environment, testcase |
| .ui-glass 应用于 MainLayout | ✅ PASS | 侧边栏 + Header 条件性应用 |

### C3: SpatialChain 接入 (PRD US-2)
**变更文件**: `frontend/src/pages/trace/index.tsx`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| SpatialChain 从 @/ui 导入 | ✅ PASS | 使用 ChainNode 类型 |
| 6 阶段链路节点构建 | ✅ PASS | 需求→用例→计划→执行→缺陷→报告 |
| 动态数据映射 | ✅ PASS | 覆盖率/通过率/执行率联动 tone 和 risk |
| 构建通过 | ✅ PASS | chunk 正确打包 |

### C4: Environment 页面 ObsidianFlow 化 (PRD US-1)
**变更文件**: `frontend/src/pages/environment/index.tsx`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| useObsidianPage 接入 | ✅ PASS | 标题/副标题/描述 Obsidian 风格 |
| Badge tone 映射 | ✅ PASS | dev→info, test→neutral, staging→warning, prod→danger |
| .ui-surface / .ui-table | ✅ PASS | Card 和 Table 正确添加 |

### C5: ThemeLab 可访问性 (PRD US-4)
**变更文件**: `frontend/src/router/index.tsx`, `frontend/src/main.tsx`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| /theme-lab 路由注册 | ✅ PASS | 懒加载，独立 chunk |
| theme-lab.css 导入 | ✅ PASS | main.tsx 引入 |
| Build chunk | ✅ PASS | ThemeLab-BXXK2eFp.js (39.10 kB) |

### C6: MainLayout 玻璃态
**变更文件**: `frontend/src/layouts/MainLayout.tsx`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 内联 <style> 移除 | ✅ PASS | 不再重复 obsidian-flow.css |
| ui-glass 类应用 | ✅ PASS | 侧边栏条件性 + Header 条件性 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | **P0** | **shadcn CSS 变量未映射** — obsidian-flow.css 定义了 `--_bg`/`--_surface`/`--_text` 等自有变量，但从未覆写 shadcn/ui 组件实际引用的 `--background`/`--foreground`/`--card`/`--primary` 等标准变量。导致主应用页面仍以 cyberpunk 霓虹蓝黑渲染，与 ThemeLab 翡翠绿黑参考基准完全不同 | 用户浏览器验收发现。所有 shadcn 组件（Card/Button/Table/Badge）渲染颜色来自 `data-theme`（cyberpunk）而非 obsidian-flow | ✅ **已修复** (c924ee1)，在 globals.css 末尾追加 `[data-ui-theme="obsidian-flow"]` 变量覆写块 |
| 2 | P2 | tsc -b 构建失败（deep-eql 类型定义缺失） | 预存问题，与本次变更无关 | 已知 |
| 3 | P3 | Button 组件尚未替换为 @/ui 基元 | 设计走查发现，已列为下一 batch 任务 | 延期 |
| 4 | P3 | PageShell 尚未接入页面 | 已列为 batch-51 任务 | 延期 |

## 根因分析：shadcn CSS 变量断连

```
obsidian-flow.css 定义的变量      shadcn/ui 组件实际引用的变量
─────────────────────────────     ─────────────────────────────
--_bg: #0b100d                    --background (来自 data-theme)
--_surface: #141c17               --card (来自 data-theme)
--_text: #eef6f0                  --foreground (来自 data-theme)
--_primary: #35e68a               --primary (来自 data-theme)
--_border-default: rgba(...)      --border (来自 data-theme)
```

两套变量体系完全平行、从不交叉。`UiThemeProvider` 设置 `data-ui-theme` 属性只触发 obsidian-flow.css 的 `--_*` 变量，但不影响 shadcn 组件读取的 `--*` 变量。

**修复**：在 `globals.css` 末尾（所有 `[data-theme]` 块之后，确保级联优先级）新增 `[data-ui-theme="obsidian-flow"]` 块，将 40+ 个 shadcn 标准 CSS 变量映射为 obsidian-flow 设计 Token。

## 发布建议

**状态: READY** ✅ (经根因修复后)

- 必修复: 0 (P0 已修复)
- 建议修复: 3（均为 P2/P3，可延期）
- 核心变更: 13 文件，5 commits（含根因修复），零新增类型错误，构建 7.41s
- 关键用户路径可走通: Workbench → Trace(SpatialChain) → TestCase → TestPlan → Report → Environment(ObsidianFlow) → ThemeLab
