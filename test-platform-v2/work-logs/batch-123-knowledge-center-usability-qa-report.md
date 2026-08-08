# Batch 123 — QA 报告（知识中心可用性 + 体育模块关联图谱）

> **QA (🔍)** | Date: 2026-08-08 | Verdict: 有条件通过（C123-1 生产导入验证、C123-2 生产走查待部署）

## 1. 交付与证据

| # | 交付 | 证据 |
|---|------|------|
| 1 | 知识源详情弹窗重构（Dialog → Sheet，95vw/42rem 分段展示，滚动完整） | `SourceListTab.tsx` |
| 2 | wiki 编译结果展示（任务状态面板：进行中/成功/失败 + 自动打开生成页面） | `WikiTab.tsx`（fetchWikiIngestJob 轮询） |
| 3 | 差异对比结果展示（轮询修复：瞬时失败继续、150 次×2s；失败态/错误展示；summary 解析保护） | `WikiDiffTab.tsx` |
| 4 | 图谱语义 + 体育模块关联入库（端点 `POST /knowledge/graph/module-associations` 幂等；脚本计算 **925 实体 + 888 关系**；端点测试 2/2；前端图谱关系类型图例） | `knowledge.py`、`import-module-associations.py`、`test_knowledge_module_associations.py`、`GraphTab.tsx` |
| 5 | 实体来源溯源（后端回填 source_title/source_type；前端列表「来源」列 + 详情溯源块） | `schemas/knowledge.py`、`knowledge.py`、`EntityTab.tsx` |
| 6 | 项目球决策（移除入口，图谱承担模块关联展示） | `knowledge/index.tsx` |

## 2. 可执行门禁

| 门禁 | 结果 |
|------|------|
| 前端 `npm ci` | ✅ 559 包 |
| 前端 `npm run typecheck` | ✅ 0 错误 |
| 前端 `npm run build` | ✅ built in 8.63s |
| 前端 vitest（knowledge 域） | ✅ 6 文件 17/17 passed |
| 后端 ruff F821（changed 文件） | ✅ All checks passed |
| 后端 pytest（test_knowledge + 新端点测试） | ✅ 77/77 passed |
| app 导入（knowledge router） | ✅ OK |
| Alembic 迁移 | ✅ 无需（无 schema 变更，复用 knowledge_entity/relation） |

## 3. 缺陷/障碍（P0–P3）

| # | 级别 | 问题 | 处理 |
|---|:----:|------|------|
| B123-1 | P2 | 模块关联入库需生产部署后执行（当前为本地计算 dry-run 925/888 + 端点测试通过） | 登记 C123-1，部署后导入并图谱验证 |
| B123-2 | P2 | 知识中心可用性修复需生产走查确认（弹窗/编译/对比/图谱/实体截图） | 登记 C123-2 |
| B123-3 | P3 | wiki 页面内容仍为纯文本 `<pre>`（markdown 渲染需新增依赖，待评估） | 登记 C123-3 |
| B123-4 | P3 | 图谱节点多时性能（vis-network） | 现有 limit 200 + 分层，登记建议 |

## 4. 发布建议

状态: **有条件通过** ｜ 必修复: 0 ｜ 条件: C123-1/2（部署后导入+生产走查）、C123-3/4（P3 建议）

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1.5d / 实际 1d | 0/0/2/2 | 1 | 前端轮询边界 + 变量遮蔽（后端脚本） | 轮询循环需处理瞬时失败与上限；Python 循环变量避免与客户端同名 |

**技能使用**: `cameltv-ui-conventions`（Sheet/布局规范）、`test-case-design`（用例结构解读）、`cameltv-bug-guard`（前端/后端避坑）。
