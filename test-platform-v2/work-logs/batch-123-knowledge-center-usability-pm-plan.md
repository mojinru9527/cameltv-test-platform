# Batch 123 — PM Plan（知识中心可用性 + 体育模块关联图谱）

> **PM (🟨)** | Date: 2026-08-08

## 规格摘要
**原始需求**: PRD Batch 123 — 修复知识中心 6 处可用性问题 + 用 Batch 122 用例结构建立体育模块关联图谱。
**目标时间**: 可用性 3 切片 + 图谱关联 2 切片 + 实体溯源/项目球 1 切片 + QA/Leader 1 切片。

## 开发任务

### [ ] Task 1: 知识源详情弹窗重构
**描述**: 将 `SourceListTab` 详情 Dialog 改为规范布局（Sheet 或受控 Dialog），按 概要/溯源/元数据/原始内容/切片 分段展示，滚动完整。
**验收标准**: 打开任意知识源弹窗，内容完整展示且可滚动到底；窄屏不溢出；截图走查无错乱。
**涉及文件**: `frontend/src/pages/knowledge/components/SourceListTab.tsx`

### [ ] Task 2: wiki 编译结果展示
**描述**: `WikiTab` 编译后展示任务状态面板（进行中/成功/失败/产物页面列表），成功后可直接打开生成页面查看内容；失败展示错误。
**验收标准**: 点「编译」→ 看到任务状态与产物页面；点页面 → 展示页面内容（markdown 渲染）。
**涉及文件**: `frontend/src/pages/knowledge/components/WikiTab.tsx`、`frontend/src/api/wiki.ts`（必要时补任务查询）

### [ ] Task 3: 差异对比结果展示
**描述**: `WikiDiffTab` 发起对比后展示差异项列表（维度/严重级/证据/左右值），可逐条展开查看；任务失败展示错误。
**验收标准**: 发起对比 → 任务成功 → 差异项列表可见；逐条查看证据；空差异与失败态明确。
**涉及文件**: `frontend/src/pages/knowledge/components/WikiDiffTab.tsx`、`WikiDiffDetailDrawer.tsx`

### [ ] Task 4: 图谱语义关系 + 体育模块关联入库
**描述**: 后端新增「模块关联导入」端点：消费 Batch 122 用例的 `闭环`/`关联:{模块}` 标签与 admin↔client 映射，生成 `knowledge_relation` 业务关系（tested_by/navigates_to/configures/links_to_admin/evolves_from 等）；图谱前端按关系类型着色/过滤并支持模块筛选。
**验收标准**: 图谱出现非 contains 语义关系；可按模块/入口筛选；关系来源可溯（evidence=用例 id/标签）。
**涉及文件**: `backend/app/api/v1/knowledge.py`、`backend/app/services/`（关系导入服务）、`frontend/src/pages/knowledge/components/GraphTab.tsx`

### [ ] Task 5: 实体溯源展示
**描述**: `EntityTab` 列表与详情展示实体来源（来源类型/标题/切片引用）；实体来源字段补齐。
**验收标准**: 任一实体可见来源；来源可点击溯源。
**涉及文件**: `frontend/src/pages/knowledge/components/EntityTab.tsx`、`backend/app/api/v1/knowledge.py`（实体详情返回来源）

### [ ] Task 6: 项目球决策与改造
**描述**: 评审 `SphereTab` 价值；若保留则改为「体育模块关联球」（按入口/模块聚合展示关联），否则移除入口。
**验收标准**: 项目球要么有明确价值（模块关联可操作），要么从导航移除。
**涉及文件**: `frontend/src/pages/knowledge/components/SphereTab.tsx`、`frontend/src/pages/knowledge/index.tsx`

### [ ] Task 7: QA + Leader + 合入
**描述**: 硬门禁（前端 typecheck/build/vitest、后端 F821/pytest/Alembic）、页面走查截图、QA 报告、Leader 判决。
**验收标准**: 门禁全绿；截图证据齐全；Leader 判决。

## 质量要求
- [ ] 前端 `npm ci && npm run typecheck && npm run build` 通过
- [ ] 后端 `ruff check app --select F821` + 相关 pytest 通过
- [ ] 新端点有单测；关系导入幂等
- [ ] 无 console 报错；页面走查截图
