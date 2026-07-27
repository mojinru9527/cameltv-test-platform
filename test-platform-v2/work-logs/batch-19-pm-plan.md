# Batch 19 — PM Plan

> PM 项目管理 · 2026-07-19 · 回顾性文档（代码已合入 PR #36）

## 批次范围

两个独立的优化专题合并为一个批次交付，覆盖用例服务和接口测试模块：

| 专题 | 文件 | 状态 |
|------|------|------|
| 测试用例服务优化 | [2026-07-15-test-case-service-optimization.md](../docs/superpowers/plans/2026-07-15-test-case-service-optimization.md) | ✅ 已合入 |
| 接口测试模块优化 | [2026-07-17-api-test-module-optimization.md](../docs/superpowers/plans/2026-07-17-api-test-module-optimization.md) | ✅ 已合入 |

## 任务拆解

### A. 测试用例服务（5 Tasks, ~3h）

| Task | 描述 | 涉及文件 | 验收标准 |
|------|------|---------|---------|
| T1 | 分类与逻辑删除数据模型 | `test_case_category.py`, `test_case.py`, migration | 两张分类表创建，TestCase 加 is_deleted |
| T2 | 分类 API + 级联删除 + 列表查询 | service + router + tests | 6 个端点（GET/POST/DELETE domain + module），搜索/排序正确 |
| T3 | 分类管理界面 + 筛选 | `CategoryManagerDialog.tsx`, `index.tsx` | 弹窗可新增/删除域和模块 |
| T4 | 新增用例弹窗 + 分页 | `CaseDrawer.tsx`, `Pagination.tsx` | 草稿默认、必填校验、20/50/100 分页 |
| T5 | 回归验证 | 前后端测试 + 构建 | 全部通过 |

### B. 接口测试模块（5 Tasks, ~3h）

| Task | 描述 | 涉及文件 | 验收标准 |
|------|------|---------|---------|
| T6 | 资产 Tab 层级 | `AssetTab.tsx` | 服务 Tab → 模块 Collapsible → 接口列表 |
| T7 | 调试面板拆分 | `DebugTab.tsx` | 服务器/服务/模块/路径四段式 |
| T8 | 用例按接口分组 | `ApiCaseTab.tsx`, `apiCaseGroups.ts` | 按 api_spec_ref 聚合 |
| T9 | 生成覆盖所有参数 | `api_case_generation_service.py` | Body/Query/Path/Header 逐参数 |
| T10 | 全量回归 | 前后端测试 + 构建 + Playwright | 全部通过 |

## 技术风险

| 风险 | 缓解措施 |
|------|---------|
| 分类表迁移回填已有数据 | `SELECT DISTINCT project_id, domain, module FROM test_case` 回填 |
| 新增 API 路由与现有 `/{id}` 冲突 | 静态路径 `/domains` 注册在 `/{case_id}` 之前 |
| 前端组件与未实现的 API 耦合 | 先定义 API 函数签名，再写组件 |

## 交付标准

- [x] 后端测试全部通过 (621/621 核心)
- [x] 前端构建无 TypeScript 错误
- [x] 迁移脚本可独立运行（`alembic upgrade head`）
- [x] 前后端 API 契约一致
- [x] Leader APPROVED
