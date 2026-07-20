# batch-21 PM 任务拆解

> 日期：2026-07-20 | PM 部门 | 基准 PRD: batch-21-prd-summary.md

## 总览

| Slice | 模块 | 任务数 | 预估 |
|-------|------|--------|------|
| S1 | 后端软删除 + 搜索扩展 | 4 | ~90min |
| S2 | 前端用例列表重构 | 5 | ~90min |
| S3 | 前端新建弹窗规范化 | 3 | ~45min |
| S4 | 前端接口测试修复 | 5 | ~90min |
| S5 | 全栈测试验证 | 3 | ~60min |

---

## Slice 1：后端 — 软删除 + 搜索扩展

### T1 — TestCase Model 加 `is_deleted` 字段
- **描述**：在 `models/test_case.py` 的 TestCase 类中声明 `is_deleted` 列（Boolean, default=False, indexed），对齐迁移 `20260715_test_case_categories.py`
- **验收**：`hasattr(TestCase, 'is_deleted')` → True
- **涉及文件**：`backend/app/models/test_case.py`
- **参考**：迁移 line 24-28

### T2 — Service 层软删除
- **描述**：`test_case_service.py` 中 `list_cases` 加 `is_deleted == False` 过滤；`delete_case` 改 `row.is_deleted = True`；`batch_delete` 改循环设 `is_deleted = True`
- **验收**：删除后 list 不再出现；DB 中记录仍存在
- **涉及文件**：`backend/app/services/test_case_service.py`
- **参考**：PRD US-1

### T3 — 删除域/模块时级联软删除关联用例
- **描述**：`delete_domain` 设关联用例 `is_deleted=True`（`update(TestCase).where(TestCase.domain==domain.name)`）；`delete_module` 同理
- **验收**：删除域后该域所有用例 is_deleted=true
- **涉及文件**：`backend/app/services/test_case_service.py`
- **参考**：PRD US-1

### T4 — 用例搜索 + API 测试搜索扩展
- **描述**：
  - `list_cases` keyword 搜索扩展为 `title + case_id + api_endpoint + domain + module + preconditions + steps + expected_result`
  - `apitest.py:252` keyword 搜索扩展为 `path + summary + service_name + module`
- **验收**：搜「登录失败」匹配到步骤中含该词的用例；搜 service 名匹配到接口资产
- **涉及文件**：`backend/app/services/test_case_service.py`、`backend/app/api/v1/apitest.py`
- **参考**：PRD US-2、Item 7a

---

## Slice 2：前端用例列表页重构

### T5 — 表头重排 + 新列 + 去旧列
- **描述**：
  - 新列顺序：复选框 → 模块名称 → 用例标题 → 用例等级 → 前置条件 → 操作步骤 → 预期结果 → 状态 → 评审 → 操作
  - 用例等级为独立 `<TableCell>`（P0-P3 Badge 从标题 cell 移出）
  - 新增前置条件/操作步骤/预期结果列（单行省略 `truncate`）
  - 删除 API 列（含表头和数据 cell）
- **验收**：表头符合新顺序；API 列不存在；等级 Badge 独立
- **涉及文件**：`frontend/src/pages/testcase/index.tsx`
- **参考**：PRD US-3、Item 3

### T6 — 移除 Excel/Xmind 导出按钮
- **描述**：删除导出 Excel、导出 Xmind、导入按钮及对应的隐藏 `<input>` 和 `handleExport`/`handleImportClick` 处理函数
- **验收**：工具栏无导出/导入按钮
- **涉及文件**：`frontend/src/pages/testcase/index.tsx`
- **参考**：PRD US-3、Item 1 相关

### T7 — 域/模块/优先级下拉加「全部」选项
- **描述**：三个 `<Select>` 各加 `<SelectItem value="">全部</SelectItem>`
- **验收**：下拉菜单可见「全部」选项
- **涉及文件**：`frontend/src/pages/testcase/index.tsx`
- **参考**：PRD US-3

### T8 — 搜索 placeholder 更新
- **描述**：搜索框 placeholder 改为「搜索标题/关键字」（覆盖标题/域/模块/前置条件/步骤/预期结果）
- **验收**：placeholder 文本更新
- **涉及文件**：`frontend/src/pages/testcase/index.tsx`
- **参考**：PRD US-2

### T9 — 列表行渲染格式化步骤（单行省略）
- **描述**：前置条件/步骤/预期结果列使用 `caseListFormatters` 中的 `formatNumberedText`/`formatStepActions`/`formatStepExpectations` 渲染，`truncate` 单行省略
- **验收**：旧版 JSON 步骤显示为「1、打开页面 2、输入用户名…」
- **涉及文件**：`frontend/src/pages/testcase/index.tsx`、`frontend/src/pages/testcase/caseListFormatters.ts`
- **参考**：PRD US-3、Item 1k

---

## Slice 3：前端新建/编辑弹窗规范化

### T10 — 移除「关联引用」字段
- **描述**：从 Zod schema 删除 `api_spec_ref`，从 JSX 删除对应 label+Input
- **验收**：弹窗中无「关联引用」字段
- **涉及文件**：`frontend/src/pages/testcase/CaseDrawer.tsx`
- **参考**：PRD US-5、Item 4

### T11 — 模块/步骤/预期结果设为必填
- **描述**：Zod schema 中 `domain`、`module`、`steps`、`expected_result` 改为 `.min(1, '请填写/选择 xxx')`
- **验收**：空值提交时显示校验错误
- **涉及文件**：`frontend/src/pages/testcase/CaseDrawer.tsx`
- **参考**：PRD US-5

### T12 — 更新 CaseDrawer 测试
- **描述**：同步调整 `CaseDrawer.test.tsx` 中断言（移除 api_spec_ref 相关、新增必填校验测试）
- **验收**：测试通过
- **涉及文件**：`frontend/src/pages/testcase/__tests__/CaseDrawer.test.tsx`（如存在）
- **参考**：PRD US-5

---

## Slice 4：前端接口测试模块修复

### T13 — 默认 Tab 改为「接口资产」
- **描述**：`apitest/index.tsx:15` 中 `useState('quick')` → `useState('assets')`
- **验收**：打开接口测试页面默认显示接口资产 Tab
- **涉及文件**：`frontend/src/pages/apitest/index.tsx`
- **参考**：PRD US-4、Item 6

### T14 — 接线 DebugTab `endpoint` prop
- **描述**：`apitest/index.tsx:68` 中 `<DebugTab />` → `<DebugTab endpoint={debugEndpoint} />`
- **验收**：从接口资产点击「调试」→ DebugTab 预填 Method/Path/Query/Body
- **涉及文件**：`frontend/src/pages/apitest/index.tsx`
- **参考**：PRD US-4、Item 7c/7g

### T15 — 默认环境「测试5」
- **描述**：`DebugTab.tsx` 中环境加载完成后自动查找 `name === '测试5'` 的环境并设为默认 `envId` 和 `baseUrl`
- **验收**：打开 DebugTab，环境下拉默认选中「测试5」
- **涉及文件**：`frontend/src/pages/apitest/components/DebugTab.tsx`
- **参考**：PRD US-4、Item 7d

### T16 — 路径显示 + 备注列
- **描述**：
  - AssetTab 路径渲染 `ep.path.replace(/\//g, '-')`
  - AssetTab 新增「备注」列（从 `ep.remark` 字段读取）
- **验收**：路径中 `/` 显示为 `-`；表格有备注列
- **涉及文件**：`frontend/src/pages/apitest/components/AssetTab.tsx`
- **参考**：Item 7b、Item 8

### T17 — 前端搜索 placeholder + 后端 API 对齐
- **描述**：AssetTab 搜索框 placeholder 改为「搜索服务/模块/路径/描述...」；与 T4 后端搜索扩展对齐
- **验收**：placeholder 更新
- **涉及文件**：`frontend/src/pages/apitest/components/AssetTab.tsx`
- **参考**：PRD US-4、Item 7a

---

## Slice 5：全栈测试验证

### T18 — 后端测试套件
- **描述**：运行 `pytest test-platform-v2/backend/tests/ -x -q`，验证 ≥617 通过，软删除逻辑正确
- **验收**：≥617 passed, 0 failed (regression)
- **涉及文件**：全部后端改动
- **参考**：PRD 成功指标

### T19 — 前端测试 + 类型检查
- **描述**：`npm run test -- --run` + `tsc --noEmit`，验证 ≥74 通过，0 TS 错误
- **验收**：≥74 passed, tsc 0 errors
- **涉及文件**：全部前端改动
- **参考**：PRD 成功指标

### T20 — 生产构建验证
- **描述**：`npm run build`，验证 Vite 生产构建无错误
- **验收**：build 成功
- **涉及文件**：全部前端改动
- **参考**：PRD 成功指标

---

## 依赖关系

```
S1 (后端) ──→ S2 (列表页) ──→ S3 (弹窗) ──→ S5 (测试)
         └──→ S4 (API测试) ──→ S5 (测试)
```

S2/S3/S4 可并行开发（三块独立前端模块），但所有前端依赖 S1 后端改动完成。

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 旧测试断言软删除时检查物理删除 | 测试失败 | 逐条检查并更新测试断言 |
| CaseDrawer 必填字段导致现有表单提交失败 | 用户体验退化 | 只在新建时强制必填，编辑已有记录保持可选 |
| `is_deleted` 列在迁移中存在但模型未映射 | 列已存在→无 schema 变更风险 | 模型加字段即可，无需新迁移 |
