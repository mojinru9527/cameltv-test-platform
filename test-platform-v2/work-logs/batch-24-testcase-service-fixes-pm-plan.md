# Batch 24 — PM Plan
> **PM (🟨)** | Date: 2026-07-20

## 规格摘要
**原始需求**: 用例服务模块 10 个问题修复（用户反馈列表）  **目标时间**: 当天完成

## 开发任务

### [x] Task 1: 后端响应体修复（P0 阻断）
**描述**: 为 `R` 类添加 `err()` 类方法，修复 9 处 `R.err()` 调用导致的 AttributeError→500
**验收标准**:
- `R.err(code=400, msg="test")` 返回 `{code:400, msg:"test", data:null}` 而非抛异常
- `POST /api/v1/test-cases/domains` 新建域正常返回
- `POST /api/v1/test-cases/domains/{id}/modules` 新建模块正常返回
- `DELETE /api/v1/test-cases/domains/{id}` 删除域正常返回
**涉及文件**: `backend/app/schemas/common.py` — 添加 err() 方法
**参考**: PRD §US3

### [x] Task 2: 列表排序改为最新优先
**描述**: 修改 `list_cases` 排序，从 `domain, module, id ASC` → `id DESC`
**验收标准**:
- 新增用例出现在列表第一页第一条
- 分页功能不受影响
**涉及文件**: `backend/app/services/test_case_service.py:138` — order_by 改为 `TestCase.id.desc()`
**参考**: PRD §US2

### [x] Task 3: 隐藏接口测试域
**描述**: 在 `get_domain_tree` 和 `get_category_tree` 中过滤 `domain == "接口测试"` 的条目
**验收标准**:
- 左侧模块分类树不含"接口测试"
- 域筛选下拉不含"接口测试"
- 模块分类管理弹窗不含"接口测试"
**涉及文件**: `backend/app/services/test_case_service.py:224-228, 477-479` — 添加过滤
**参考**: PRD §US3

### [x] Task 4: 步骤信息分步展示
**描述**: 表格中前置条件/操作步骤/预期结果改为每步独立行渲染，带编号 1、2、3、
**验收标准**:
- 前置条件每步一个 `<div>`，换行显示
- 操作步骤每步一个 `<div>`，换行显示
- 预期结果每步一个 `<div>`，换行显示
- 无内容时显示 "-"
**涉及文件**: `frontend/src/pages/testcase/index.tsx:406-430` — 改为多行渲染
**参考**: PRD §US1

### [x] Task 5: 筛选下拉默认值
**描述**: 域/模块/优先级下拉默认显示"全部域/全部模块/全部优先级"
**验收标准**:
- 初始加载时三个下拉均显示"全部X"而非空白
- 选择"全部X"后正确显示"全部X"
- 选择具体值后筛选生效
**涉及文件**: `frontend/src/pages/testcase/index.tsx:267-301` — Select placeholder + value 处理
**参考**: PRD §US4

### [x] Task 6: 删除域/模块 API 防护
**描述**: 在 API 调用函数中加入 ID 校验，防止 `undefined` 传入 URL
**验收标准**:
- `deleteDomain(undefined)` → 抛出 "domainId 无效" 错误（不发 HTTP 请求）
- `deleteModule(0, 1)` → 抛出 "domainId 无效"
- `createModule(undefined, "test")` → 抛出 "domainId 无效"
**涉及文件**: `frontend/src/api/testcase.ts:39-49` — 添加校验；`frontend/src/pages/testcase/CategoryManagerDialog.tsx:50-52` — categoryId 优化
**参考**: PRD §US3

### [x] Task 7: 搜索按钮行为修正
**描述**: 搜索按钮同时调用 `setPage(1)` 和 `refetch()` 确保首次点击即搜索
**验收标准**: 已在第 1 页时，点击搜索按钮仍触发查询
**涉及文件**: `frontend/src/pages/testcase/index.tsx:315` — 添加 refetch()
**参考**: PRD §US4

## 质量要求
- [x] 后端 pytest 全绿（653 tests）
- [ ] OpenAPI 响应 schema 保持兼容
- [x] 前端 TypeScript 编译无新增错误
- [x] 无 console 报错/告警
- [ ] 3 个下拉选择器值在空/非空切换时无闪烁
