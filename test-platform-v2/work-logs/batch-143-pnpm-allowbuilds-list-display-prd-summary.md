# Batch 143 — pnpm 构建配置修复 + 列表展示问题修复 PRD-lite
> **Product (🟦)** | Date: 2026-08-10 | Status: Approved

mode: light
豁免理由: 纯前端修复：构建基础设施占位符配置 + 列表分页条数 + 截断单元格补 title，无新接口/新依赖/新行为（分页条数属展示参数调整）。
非目标: 不新增/删除功能，不调整业务逻辑，不改后端接口；不逐条为全部 50+ 截断处补 title（仅覆盖关键数据单元格，其余记录在 QA 报告）。

## 1. 问题陈述
1. **pnpm-workspace.yaml `allowBuilds` 占位符未配置**：`chromedriver: set this to true or false` / `esbuild: set this to true or false`，pnpm 11 下 `pnpm install` 被 `ERR_PNPM_IGNORED_BUILDS` 阻断（esbuild 构建脚本被忽略，vite 构建不可用）。
2. **列表每页条数 < 10**：需求文档页业务域表 `domainPageSize = 8`，每页仅 8 条就分页；同页需求文档列表 `docPageSize = 10`（平台其余列表默认 20）。
3. **截断后完整值不可达（展示不全）**：多张列表/表格对长文本 `truncate` 截断但无 `title` 提示，悬停无法查看完整内容（蓝湖链接、缺陷编号/标题/负责人、数据集列名/单元格、环境变量值、接口调试 URL、知识来源标题/引用、实体描述、性能设备名/包名、项目/报告列等）。

### 全平台扫描结论（Batch 142 之后复扫）
- 同类「Tailwind v4 写法在 v3 下不编译」的类：**0 处残留**（Batch 142 已全量修复）。
- 固定高度容器均带滚动（`overflow-y-auto`/`ScrollArea`），无底部截断。
- 未发现绝对定位文案重叠/负边距错位等明显缺陷。
- 后端分页默认值均为 20+，无小于 10 的默认。
- 客户端分页每页条数：仅 `requirement/index.tsx` 的 domain 表为 8；其余（迭代 50、评审 50、缺口 50、审计 50、知识 20/50、来源 20、发布包 20 等）均 ≥20。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| pnpm install | ERR_PNPM_IGNORED_BUILDS 阻断 | 无阻断，esbuild 构建脚本执行 | 本批验收 |
| 业务域表每页条数 | 8 | 20（平台默认） | 本批验收 |
| 需求文档列表每页条数 | 10 | 20（平台默认） | 本批验收 |
| 关键截断单元格 | 无 title，完整值不可达 | 悬停可查看完整值 | 本批验收 |
| 回归 | - | typecheck/build/vitest 全绿 | 本批验收 |

## 3. 用户故事与验收标准
- As 开发者, I want pnpm install 不因 allowBuilds 占位符失败, so that 新环境能正常安装并构建。
  - Given 干净环境 / When 执行 pnpm install / Then 无 ERR_PNPM_IGNORED_BUILDS，esbuild 正常构建。
- As 用户, I want 列表每页展示足够多数据, so that 少量数据不需要频繁翻页。
  - Given 需求文档页业务域表 / Then 每页展示 20 条业务域。
- As 用户, I want 被截断的关键数据能查看完整值, so that 信息不丢失。
  - Given 蓝湖链接/缺陷标题/环境变量值等截断单元格 / Then 悬停显示完整内容（title）。

## 4. 技术方案要点
- `pnpm-workspace.yaml`：`allowBuilds` 设为 `chromedriver: false`、`esbuild: true`。
- `requirement/index.tsx`：`domainPageSize 8→20`、`docPageSize 10→20`。
- 关键截断单元格补 `title`：lanhu-evidence 链接、DefectTable（defect_id/assignee_name/case_title）、dataset（列名/单元格）、environment（变量值）、apitest TaskTab（请求 URL）、SourceListTab（title/source_ref）、EntityTab（description）、perftest（device_name/pkg_name）、project/report DataTable 列（code/name/description、report_id/name/plan_name）。
- 验证：`pnpm install` 无阻断；`tsc -b`、`vite build`、`vitest run` 全绿。
