# Batch 19 — Design Spec

> Design 设计部门 · 2026-07-19 · 回顾性文档（代码已合入 PR #36）

## 组件设计

### 1. CategoryManagerDialog（分类管理弹窗）

**位置**: [CategoryManagerDialog.tsx](../frontend/src/pages/testcase/CategoryManagerDialog.tsx)

**功能**：
- 左侧"新增域"输入区 + 右侧"新增模块"输入区（需先选域）
- 域以 Collapsible 呈现，展开显示模块列表
- 每项右侧有删除按钮（需有效 ID）
- 删除前弹出 AlertDialog 确认

**交互规范**：
- 域无 ID 时禁用删除（显示 tooltip："分类接口尚未更新"）
- 模块下拉使用 `position="popper"` + `align="start"` 避免遮挡
- 新增成功后自动刷新列表
- 输入框支持 Enter 提交

**技术栈**: Radix Collapsible + Select + AlertDialog，Tailwind `divide-y`, `bg-muted/40`

### 2. AssetTab（接口资产 Tab）

**位置**: [AssetTab.tsx](../frontend/src/pages/apitest/components/AssetTab.tsx)

**功能**：
- **服务作为 Tabs**：每个服务一个 Tab，切换显示对应服务的内容
- **模块作为 Collapsible**：每个模块默认关闭，展开显示接口列表
- TabList 支持横向滚动：`overflow-x-auto`

**关键设计决策**：
- 服务 Tab 使用 `Tabs` + `TabsContent` 条件渲染（遵循 `cameltv-bug-guard` React 铁律：`forceMount + {activeTab==='x' && <Comp/>}` 防重复 mount）
- 路径显示做 `/` → `-` 视觉替换

### 3. DebugTab（快速调试 Tab）

**位置**: [DebugTab.tsx](../frontend/src/pages/apitest/components/DebugTab.tsx)

**功能**：
- **四段式地址**：服务器地址 + 服务名 + 模块路径 + 接口路径
- 切换环境仅更新服务器地址
- 默认选中"测试5"环境
- 响应结果移至请求配置下方

**关键设计决策**：
- 请求组装：`composeAssetUrl(baseUrl, serviceName, modulePath, endpointPath)`
- URL 参数拼接：`applyPathAndQueryParams(requestUrl, paramRows)`

### 4. ApiCaseTab（接口用例 Tab）

**位置**: [ApiCaseTab.tsx](../frontend/src/pages/apitest/components/ApiCaseTab.tsx)

**功能**：
- 用例按 `api_spec_ref` 分组聚合
- 每组以 Collapsible 呈现，默认关闭
- 支持单条/接口组/全量执行

**分组逻辑** (`apiCaseGroups.ts`):
```ts
groupApiCases(cases) → Array<{ key, name, cases }>
```
- 优先按 `api_spec_ref` 分组
- 无引用的旧用例按 HTTP 方法和去除 Query 的路径分组

### 5. Pagination 增强

**位置**: [Pagination.tsx](../frontend/src/components/Pagination.tsx)

**新增 props**：
- `pageSize?: number` — 当前每页条数
- `pageSizeOptions?: number[]` — 可选条数列表
- `onPageSizeChange?: (size: number) => void` — 切换回调
- 页码输入跳转（带边界校验）

## 后端设计

### 分类 API

```text
GET    /api/v1/test-cases/domains                             → 域树
POST   /api/v1/test-cases/domains      { name }               → 新增域
DELETE /api/v1/test-cases/domains/{id}                         → 删除域（级联）
POST   /api/v1/test-cases/domains/{id}/modules  { name }       → 新增模块
DELETE /api/v1/test-cases/domains/{did}/modules/{mid}           → 删除模块
```

### API 生成器增强

**位置**: [api_case_generation_service.py](../backend/app/services/api_case_generation_service.py)

- 覆盖范围从 Query first-3 扩展到 **Body/Query/Path/Header 逐参数**
- 每种类型参数生成：空值用例 + 类型错误用例 + 边界覆盖
- 生成上限从 30 调整为 200

### 技术约束

- 分类操作需项目隔离（`project_id` 过滤）
- 级联删除使用单事务
- 同名域/模块在删除后可恢复（`is_deleted` 标记）
