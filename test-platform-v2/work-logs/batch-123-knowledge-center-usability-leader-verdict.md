# Batch 123 — Leader Verdict（知识中心可用性 + 体育模块关联图谱）

> **Leader (🎯)** | Date: 2026-08-08 | Decision: 有条件通过（C123-1/2 部署后闭环）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 4.5/5 | 6 切片全落地；门禁全绿（typecheck/build/vitest 17/17/ruff/pytest 77/77） |
| 风险 | 低 | 无 schema 变更；后端仅新增端点；前端为知识中心组件改造 |
| 覆盖 | 4/5 | 用户反馈的 6 处可用性问题全部处理；图谱模块关联为新增核心价值；生产走查待部署后执行 |

## 关键决策（已批准）

1. **知识源弹窗 → Sheet**：右侧抽屉 95vw/42rem 分段展示（概要/溯源/元数据/原始内容/切片），解决"歪七扭八展示不全"。
2. **wiki 编译/差异对比去黑盒**：编译任务状态面板 + 自动打开生成页面；对比轮询修复（瞬时失败继续、上限 150×2s）+ 失败态展示。
3. **图谱语义 + 模块关联**：新增 `POST /knowledge/graph/module-associations` 幂等端点；脚本从 Batch 122 的 507 条用例结构计算 **925 实体 + 888 业务关系**（contains/tested_by/navigates_to/links_to_admin/configures），体现 用户端↔运营后台↔konfi、用例↔接口、闭环链路；前端图谱增加关系类型图例。
4. **实体溯源**：实体列表/详情展示来源（source_title/source_type），来源不明实体标注"来源待补"。
5. **项目球移除**：与图谱模块关联功能重复，移除入口（代码保留），图谱 Tab 承担模块关联展示。

## 抽检通过

- ✅ `WikiTab.tsx` — compile 轮询 + 状态面板 + 自动打开（fetchWikiIngestJob）
- ✅ `WikiDiffTab.tsx` — 轮询修复（瞬时失败 continue）+ failed 态
- ✅ `knowledge.py` module-associations 端点 + `test_knowledge_module_associations.py` 2/2（幂等/可见/503 门禁）
- ✅ `import-module-associations.py` dry-run 925 实体/888 关系
- ✅ 门禁：typecheck/build/vitest 17/17/ruff F821/pytest 77/77

## 判决

**有条件通过**。合入后：C123-1 部署后执行模块关联导入并图谱验证；C123-2 知识中心生产走查截图；C123-3/4 P3 建议（markdown 渲染/图谱性能）。

## 下一批次 Leader 条件

- **C123-1**: 生产部署后执行 `scripts/knowledge/import-module-associations.py` 导入 925 实体/888 关系，图谱验证模块关联可见
- **C123-2**: 知识中心生产走查（弹窗/编译/对比/图谱/实体 截图证据）
- **C123-3**: wiki 页面 markdown 渲染（新增依赖评估后落地，P3）
- **C123-4**: 图谱大数据量性能优化（分层/聚合，P3）

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 前端轮询 8 次即停 + 瞬时失败终止轮询 → 用户感知"发起对比用不了" | 轮询改为 150×2s + 瞬时失败 continue + 失败态 | WikiDiffTab.tsx（已实现） |
| Python 脚本循环变量与 httpx 客户端同名导致 AttributeError | 脚本循环变量命名规范（case 而非 c） | 本批复盘卡；脚本已修正 |
| 项目球与图谱模块关联功能重复 | 移除入口，图谱承担 | knowledge/index.tsx |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1.5d / 实际 1d | 0/0/2/2 | 1 | 轮询边界 + 变量遮蔽 | 轮询处理瞬时失败与上限；变量命名避客户端同名 |
