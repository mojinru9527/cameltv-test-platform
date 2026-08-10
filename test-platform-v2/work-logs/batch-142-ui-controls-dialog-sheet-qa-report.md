# Batch 142 — 全平台表单控件 / 弹窗 / 抽屉 UI 修复 QA 报告
> **QA (🔍)** | Date: 2026-08-10 | Verdict: PASS

## 可执行门禁（前端域）
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:---:|------|
| typecheck | `tsc -b` | 0 | PASS（无类型错误） |
| build | `vite build` | 0 | PASS（8.3s，产物生成） |
| 全量单测 | `vitest run` | 0 | 109 files / 444 tests 全通过，0 失败 |
| 无调试遗留 | `rg "console.log|debugger|breakpoint"`（改动文件） | 0 | PASS |

## 根因验证（构建产物比对）
以 main 分支 dist 为基线，比对本次构建产物 `dist/assets/*.css`：

| 失效类（v4 写法） | 基线 dist | 本次 dist |
|---|---|---|
| `data-checked:bg-primary`（switch/checkbox） | MISSING | PRESENT（`data-[state=checked]:bg-primary`） |
| `data-unchecked:bg-input`（switch） | MISSING | PRESENT |
| `data-disabled:opacity-50`（switch/select/dropdown） | MISSING | PRESENT（`data-[disabled]:`） |
| `data-inset:pl-7`（dropdown） | MISSING | PRESENT |
| `data-placeholder:text-muted-foreground`（select） | MISSING | PRESENT |
| `data-selected:bg-muted` / `group-data-selected`（command） | MISSING | PRESENT |
| `not-data-[...]:`（dropdown/select） | MISSING | PRESENT（`[&:not([data-variant=destructive])]:`） |
| `in-[[...]]:`（command/sidebar 等祖先变体） | MISSING | PRESENT（命名组/group-data 等价） |
| `has-data-[...]:` / `has-disabled:` / `group-has-data-[...]:` | MISSING | PRESENT（`has-[[...]]:` / `has-[:disabled]:` / `group-has-[[...]]:`） |
| `xxx!`（后缀 important） | MISSING | PRESENT（前缀 `!`） |
| `outline-hidden` | MISSING | PRESENT（`outline-none`） |
| `*:[span]:last` / `*:[svg]` | MISSING | PRESENT（`[&>span:last-child]` / `[&_svg]`） |
| dialog `max-h-[calc(100dvh-2rem)] overflow-y-auto` | 无 | PRESENT |
| sheet `overflow-y-auto overflow-x-hidden` / `sm:max-w-md` | 无 | PRESENT |

## 浏览器验收（Playwright，1440x900，临时验证页）
| 验收项 | 结果 | 证据 |
|---|---|---|
| Switch 点击后滑块移动 + 主色高亮 | ✅ | `data-state: unchecked→checked`；bg `oklch(0.17...)→oklch(0.72 0.15 205)`（主色）；thumb `matrix(...,14,0)`（右移 14px） |
| Checkbox 点击后勾选 + 主色 | ✅ | `data-state: unchecked→checked`；bg → 主色 |
| Select 占位符灰字 | ✅ | 计算色 `oklch(0.62 0.02 230)`（muted-foreground） |
| 居中弹窗高内容可滚动 | ✅ | `overflow-y:auto`，`max-height:765px`（calc(100dvh-2rem)） |
| 右侧抽屉可滚动 + 宽 448px | ✅ | `overflow-y:auto`，width 448px（sm:max-w-md） |
| 抽屉长链接断行不溢出 | ✅ | `break-all`，截图无溢出 |
| 命令面板（CommandDialog）可打开 | ✅ | 修复前 pageerror `Cannot read properties of undefined (reading subscribe)`（cmdk 缺 `<Command>` 包裹）；修复后正常渲染 2 个命令项 |

## 缺陷清单（本次审计发现并修复）
| 级别 | 问题 | 状态 |
|---|---|---|
| P0 | Switch/Checkbox 全平台勾选无视觉反馈（Tailwind v3 不编译 `data-checked:`） | 已修复 |
| P1 | 居中弹窗高内容底部截断（无 max-h/滚动） | 已修复 |
| P1 | 右侧抽屉长链接溢出、内容截断 | 已修复 |
| P1 | CommandDialog 缺 `<Command>` 包裹，打开即崩溃 | 已修复（审计发现） |
| P2 | Select/Dropdown/Command 等 11 个共享组件共 20+ 处 v4 变体不编译 | 已修复 |
| P3 | 采集弹窗过窄（560px）无滚动 | 已修复（640px + max-h + 滚动） |
| P3 | PrototypePreview 交互说明超出滚动区被裁切 | 已修复（并入 ScrollArea） |

## 已知基线失败
无（444 用例全通过，无基线失败）。

## 复盘点（复盘卡）
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h / 实际 5h | 1/2/1/2 | 0 | 代码质量（v4 语法误用于 v3 栈） | 共享组件用 class 前先核对该工具类/变体在项目 Tailwind 版本可用；引入新 UI 组件时先跑一次构建并抽查构建产物 |

**技能使用**: `cameltv-agent-team` / `cameltv-ui-conventions` / `cameltv-bug-guard`。

## 备注（本批未纳入的发现）
- `test-platform-v2/frontend/pnpm-workspace.yaml` 中 `allowBuilds` 仍为占位符 `set this to true or false`，pnpm 11 下 `pnpm install` 会被 `ERR_PNPM_IGNORED_BUILDS` 阻断（本次验证时临时置 `esbuild: true` 后还原）。属构建基础设施配置，未纳入本批，建议后续单独处理。
