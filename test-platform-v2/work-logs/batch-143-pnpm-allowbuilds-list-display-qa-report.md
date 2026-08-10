# Batch 143 — pnpm 构建配置修复 + 列表展示问题修复 QA 报告
> **QA (🔍)** | Date: 2026-08-10 | Verdict: PASS

## 可执行门禁（前端域）
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:---:|------|
| 安装 | `pnpm install` | 0 | PASS（无 ERR_PNPM_IGNORED_BUILDS，esbuild postinstall 执行） |
| typecheck | `tsc -b` | 0 | PASS |
| build | `vite build` | 0 | PASS（8.5s） |
| 全量单测 | `vitest run` | 0 | 109 files / 444 tests 全通过 |
| 无调试遗留 | `rg "console.log|debugger|breakpoint"`（改动文件） | 0 | PASS |

## 变更验证
| 项 | 结果 | 证据 |
|---|---|---|
| pnpm-workspace.yaml allowBuilds | ✅ | `esbuild: true` / `chromedriver: false`，`pnpm install` 35.3s 完成无阻断 |
| 业务域表每页条数 8→20 | ✅ | `domainPageSize = 20` |
| 需求文档列表每页条数 10→20 | ✅ | `docPageSize = 20`；`RequirementPage.test.tsx` 断言同步更新（`page_size: 20`） |
| 关键截断单元格 title | ✅ | 12 个文件 20 处补 `title`（lanhu-evidence/DefectTable/dataset/environment/TaskTab/SourceListTab/EntityTab/perftest/project/report） |
| 全平台复扫（同类 v4 写法） | ✅ | 0 处残留 |

## 全平台扫描结论（本批排查范围）
| 类别 | 结论 |
|---|---|
| 同类 Tailwind v4 写法不编译 | 0 处（Batch 142 已全量修复，本批复扫确认） |
| 列表每页条数 < 10 | 仅 `requirement` 业务域表 8 条 → 已修 20；其余均 ≥20 |
| 固定高度截断（无滚动） | 未发现（容器均已带 overflow-y-auto/ScrollArea） |
| 文案重叠/绝对定位错位 | 未发现明显缺陷（仅输入框内图标/时间线圆点等正常绝对定位） |
| 截断后完整值不可达 | 关键单元格已补 title；其余装饰性/次要截断记录如下 |

## 已知基线失败
无（444 用例全通过）。本批唯一失败为 `RequirementPage.test.tsx` 断言旧 `page_size: 10`，已同步更新为 20。

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际 3h | 0/0/1/0 | 0 | 变更联动 | 改分页条数等常量时同步检索测试断言（rg page_size） |

## 备注（记录未纳入本批的次要项）
- `truncate` 无 `title` 的装饰性/次要截断（卡片标题、静态标签、已可点击进入详情的按钮等）约 30 处，未逐条补 title，属可接受设计；如后续需要可统一处理。
- 仓库 CI 使用 npm（package-lock.json），pnpm-lock.yaml 未纳入本批（本地生成不入库）。

**技能使用**: `cameltv-agent-team` / `cameltv-ui-conventions`。
