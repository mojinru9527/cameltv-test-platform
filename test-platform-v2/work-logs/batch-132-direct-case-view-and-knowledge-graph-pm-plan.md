# Batch 132 — PM Plan
> **PM (🟨)** | Date: 2026-08-10

## 规格摘要
**原始需求**:
1. 直属用例是真实用例，需可点击查看并可编辑（复用现有用例列表/抽屉链路）。
2. 知识图谱全量用例入图（7559），能关联的关联对应模块；计数口径与用例库一致。
3. 项目知识 / 平台研发分域隔离（孤儿实体不再双域重复，实体列表/统计支持分域）。
**目标时间**: 本批次（完整批次，前端 + 后端）

## 开发任务

### A. 直属用例可查看/可编辑（用例库）
#### [ ] Task A1: 后端列表/导出支持直属精确过滤
**描述**: `test_case_service.list_cases` 与导出接口（xmind/excel）新增 `taxonomy_direct` 参数；`taxonomy_location_matches` 增加 `direct_only` 语义（module_path 精确相等；域级直属=module_path 为空）。既有父级含后代语义保持不变。
**验收标准**:
- `GET /test-cases?taxonomy_domain=FAQ帮助&taxonomy_direct=true` 只返回 domain=FAQ帮助 且 module_path 为空的用例。
- `GET /test-cases?taxonomy_module=赛事详情/订单列表&taxonomy_direct=true` 只返回 module_path 精确等于该值的用例（不含子模块）。
- 不传 taxonomy_direct 时行为与现状完全一致（回归）。
**涉及文件**: `backend/app/services/test_case_service.py`、`backend/app/services/test_case_taxonomy.py`、`backend/app/api/v1/test_case.py`、`backend/tests/test_testcase.py`
**参考**: PRD §4/§5

#### [ ] Task A2: 前端直属核算行可点击进入列表并查看/编辑
**描述**: DomainTree 直属核算行从只读（selectable=false）改为可点击筛选项，保留视觉区分（muted/斜体 + aria 说明），点击后设置"直属过滤"状态（父级 + direct_only）并刷新列表；列表复用现有查看/编辑（CaseDrawer/批量操作）链路。
**验收标准**:
- 点击"直属用例 (18)" → 列表精确显示 18 条直属用例，URL/筛选状态正确。
- 列表内可打开详情、编辑保存、批量删除/更新，与普通用例一致；保存后 refetch 列表与 taxonomy。
- 视觉上仍与真实模块节点区分（防误触）；无 console 错误。
**涉及文件**: `frontend/src/components/DomainTree.tsx`、`frontend/src/pages/testcase/index.tsx`、`frontend/src/pages/testcase/index.test.tsx`、`frontend/src/components/__tests__/DomainTree.test.tsx`
**参考**: PRD §4/§5

### B. 知识图谱全量用例入图 + 计数口径
#### [ ] Task B1: 全量用例入图脚本/接口（含 source 回填）
**描述**: 新增用例全量入库能力：遍历项目 active 用例，落为 `test_case` 实体（entity_key 去重、幂等），按 C126-1 回填 `source_id`/`source_ref`（以用例库为来源）；复用 `test_case_linker` 策略为能关联模块的用例建立 `tested_by` 关联。
**验收标准**:
- 幂等：重复执行不产生重复实体（按 entity_key upsert）。
- 用例实体数 = 用例库全量（7559），全部有 source_id/source_ref（消除"来源待补"）。
- 能关联模块的用例建立 tested_by 关联；无关联用例保留实体且有明确归属。
**涉及文件**: `backend/app/services/knowledge/`（新 ingest_all_test_cases 服务/脚本）、`backend/app/api/v1/knowledge.py`（如加触发接口）、`backend/tests/`
**参考**: PRD §2/§5、C125-3、C126-1

#### [ ] Task B2: 图谱计数权威口径（后端）
**描述**: 图谱图例/实体统计的用例计数改为权威口径：返回用例库全量 + 已入图数（如 `test_case_entities` vs `test_case_total`），不再让前端用"已加载节点过滤数"冒充总量。
**验收标准**: 统计/图例数据含用例库全量数与已入图数；与用例库口径一致。
**涉及文件**: `backend/app/api/v1/knowledge.py`、`backend/app/schemas/knowledge.py`
**参考**: PRD §2

#### [ ] Task B3: 前端图谱计数展示与大数据量不崩溃
**描述**: 图谱图例/实体统计展示"已入库 X / 全量 Y"；7000+ 节点渲染不崩溃（承接 C126-4：分层/聚合或按需加载，至少图例计数不依赖已加载节点）。
**验收标准**: 图例显示权威计数；7000+ 节点页面不报错/不白屏（性能优化项按 C126-4 基础处理）。
**涉及文件**: `frontend/src/pages/knowledge/components/GraphTab.tsx`、`EntityTab.tsx`、`frontend/src/api/knowledge.ts`、`frontend/src/types/`
**参考**: PRD §2/§5、C126-4

### C. 项目知识 / 平台研发分域隔离
#### [ ] Task C1: 后端分域过滤修正（graph/view + entities + stats）
**描述**: `graph/view` 孤儿实体不再双域重复：按实体来源 knowledge_domain 归属；无来源实体归"未分类"并在无分域（全量）时可见，或在项目域可见（明确口径）。`/graph/entities`、`/graph/entities/stats` 支持 `knowledge_domain` 过滤。
**验收标准**: 项目知识 tab 与平台研发 tab 返回集合不重叠；无来源实体不双域出现；带 knowledge_domain 过滤的 entities/stats 返回正确计数。
**涉及文件**: `backend/app/api/v1/knowledge.py`、`backend/app/services/knowledge/`、`backend/tests/test_knowledge*.py`
**参考**: PRD §1.3/§5、C126-1

#### [ ] Task C2: 平台研发知识源接线
**描述**: 平台域知识源创建/分类入口支持 `knowledge_domain='platform'`（含 capture/classify 接口与来源展示），使平台研发有独立知识源。
**验收标准**: 可创建/分类 platform 域知识源；平台研发 tab 能展示其来源与实体。
**涉及文件**: `backend/app/api/v1/knowledge.py`、`backend/app/services/knowledge/source_service.py`、前端 PlatformTab/ProjectTab
**参考**: PRD §1.3/§5

## 质量要求
- [ ] 后端 `ruff check app --select F821`、相关 pytest 全过
- [ ] 前端 `npm run typecheck && npm run build`、相关 vitest 全过
- [ ] 全量回归无新增失败（pytest / npm test，记录退出码）
- [ ] 无 console.log/print/debugger；无 N+1（全量入图用批量 upsert，禁止逐条查询请求）
- [ ] 无障碍：直属核算行点击项有 aria-label；图谱计数文字可读
- [ ] OpenAPI schema 同步（新增 `taxonomy_direct`、`knowledge_domain` 参数）
