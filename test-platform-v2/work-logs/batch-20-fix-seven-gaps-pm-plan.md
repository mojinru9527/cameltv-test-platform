# Batch 20 — PM Plan
> **PM (🟨)** | Date: 2026-07-20

## 规格摘要
**原始需求**: Batch-19 10 项优化中 7 项未/部分落地，需逐项修复
**目标时间**: 1 个 session（约 90 分钟实现，已拆分 9 个 Slice）

## 开发任务

### Slice 1: 后端 — 逻辑删除 Model 层补齐
**描述**: TestCase Model 加 `is_deleted` 映射列，TestCaseDomain/TestCaseModule 确认字段已声明
**验收标准**:
- `test_case.py` ORM model 包含 `is_deleted: Mapped[bool]` 列，默认 `False`
- Alembic 迁移已验证列存在（不新增迁移）
**涉及文件**:
- `backend/app/models/test_case.py` — 加 `is_deleted` mapped_column
- `backend/app/models/test_case_category.py` — 确认 is_deleted 已声明
**参考**: PRD US-1

### Slice 2: 后端 — 逻辑删除 Service 层改造
**描述**: `list_cases` 过滤 `is_deleted=false`；`delete_case`/`batch_delete` 改为软删除；`get_domain_tree` 过滤已删除分类
**验收标准**:
- `list_cases()` 查询加 `WHERE is_deleted = 0`
- `delete_case()` 设 `case.is_deleted = True` + `db.flush()`
- `batch_delete()` 批量设 `is_deleted = True`
- `get_domain_tree()` 排除 `is_deleted=true` 的域/模块/用例
**涉及文件**:
- `backend/app/services/test_case_service.py` — 4 处修改
**参考**: PRD US-1, US-2

### Slice 3: 后端 — 分类 CRUD API 端点
**描述**: 补充域/模块的 POST/PUT/DELETE 端点，使前端 CategoryManagerDialog 可用
**验收标准**:
- `POST /test-cases/domains` — 创建域
- `POST /test-cases/modules` — 创建模块
- `PUT /test-cases/domains/{id}` — 更新域
- `PUT /test-cases/modules/{id}` — 更新模块
- `DELETE /test-cases/domains/{id}` — 逻辑删除域（含级联标记模块+用例）
- `DELETE /test-cases/modules/{id}` — 逻辑删除模块（含级联标记用例）
**涉及文件**:
- `backend/app/api/v1/test_case.py` — 6 个新端点
**参考**: PRD US-1

### Slice 4: 前端 — 补全分类 API + 移除关联引用
**描述**: 前端 `@/api/testcase` 补全 domain/module CRUD 函数；CaseDrawer 移除 api_spec_ref
**验收标准**:
- `createDomain`/`createModule`/`deleteDomain`/`deleteModule` API 函数可用
- CaseDrawer 表单无「关联引用」标签和输入框
- Zod schema 无 `api_spec_ref` 字段
- `CaseDrawer.test.tsx` 断言与实际一致
**涉及文件**:
- `frontend/src/api/testcase.ts` — 加 4 个 API 函数
- `frontend/src/pages/testcase/CaseDrawer.tsx` — 删 label+Input+schema field
- `frontend/src/pages/testcase/__tests__/CaseDrawer.test.tsx` — 修正断言
**参考**: PRD US-4

### Slice 5: 前端 — 用例列表优先级独立列
**描述**: 表头加「优先级」列，从标题 cell 移出 Priority Badge 到独立列
**验收标准**:
- 表头 checkbox 和编号之间插入「优先级」列
- 优先级 Badge 在独立 TableCell 中
- 标题 cell 不再含优先级 Badge
**涉及文件**:
- `frontend/src/pages/testcase/index.tsx` — 表头+渲染行
**参考**: PRD US-3

### Slice 6: 前端 — 接口测试默认 Tab + DebugTab 接线
**描述**: apitest/index.tsx 默认 Tab 改为 assets；DebugTab 接收 endpoint prop
**验收标准**:
- `useState('assets')` 替代 `useState('quick')`
- `<DebugTab endpoint={debugEndpoint} />` 传递 prop
- 从资产列表点击调试 → 参数预填成功
**涉及文件**:
- `frontend/src/pages/apitest/index.tsx` — 2 行修改
**参考**: PRD US-5, US-6

### Slice 7: 接口资产 — 搜索扩展 + 路径显示 + 默认环境
**描述**: 后端搜索加 service_name/module；前端路径 `/`→`-`；DebugTab 默认环境「测试5」
**验收标准**:
- `apitest.py:252` 搜索范围含 `ApiEndpoint.service_name.ilike(like)` 和 `ApiEndpoint.module.ilike(like)`
- AssetTab 路径显示 `path.replace(/\//g, '-')` 或等效
- DebugTab 初始化时自动查找 name="测试5" 的环境并选中
**涉及文件**:
- `backend/app/api/v1/apitest.py` — 扩展 ILIKE
- `frontend/src/pages/apitest/components/AssetTab.tsx` — 路径显示转换
- `frontend/src/pages/apitest/components/DebugTab.tsx` — 默认环境逻辑
**参考**: PRD US-7, US-8, US-6

### Slice 8: 接口资产 — 备注字段全链路
**描述**: Model → Schema → Type → AssetTab 加 remark 字段
**验收标准**:
- `ApiEndpoint` model 有 `remark: Mapped[Optional[str]]`
- `ApiEndpointOut` schema 有 `remark: Optional[str]`
- 前端 `ApiEndpoint` 类型有 `remark?: string`
- AssetTab 列表行展示备注（或 DetailPanel）
- Alembic 迁移加列
**涉及文件**:
- `backend/app/models/api_asset.py` — 加列
- `backend/app/schemas/api_asset.py` — 加字段
- `frontend/src/types/index.ts` — 加字段
- `frontend/src/pages/apitest/components/AssetTab.tsx` — 展示备注
- Alembic 新迁移脚本
**参考**: PRD US-9

### Slice 9: QA 全量验证
**描述**: 前后端测试全跑 + 真实浏览器验证 9 项
**验收标准**:
- 后端 610 项测试全通过
- 前端 67 项测试全通过
- 类型检查通过
- 生产构建通过
- 浏览器手动验证 9 项全部通过
**涉及文件**: 所有
**参考**: PRD §2 成功指标

## 质量要求
- [x] 每个 Slice 即刻 commit
- [x] TDD：先看测试再改代码
- [x] 后端 Alembic 迁移安全
- [x] 前端无 console 报错
- [x] OpenAPI 同步（新增端点）
