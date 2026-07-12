---
title: "CamelTv 工程输出规范"
owner: "dev-team"
last_reviewed: "2026-07-07"
status: "active"
expires: "2027-01-07"
tags: ["engineering", "dev", "qa", "automation", "comments"]
related: ["testing-strategy.md", "../tests/CLAUDE.md", "../tests/automation/README.md"]
---

# CamelTv 工程输出规范

> 本文档定义 DEV 与 QA 在代码层面的交付要求。所有新增、修改、生成的代码和自动化测试均必须遵循。

## 1. DEV 代码注释要求

- DEV 部门后续所有代码层面的输出必须包含必要注释，说明代码块、函数、类、配置项或脚本的用途。
- 注释应回答“这段代码是干嘛用的 / 为什么需要这样做”，而不是重复语法本身。
- 业务规则、权限判断、状态流转、异常兜底、数据迁移、定时任务、外部系统对接、AI 调用、缓存策略必须写注释。
- 公共方法、服务类、复杂组件、CLI 脚本、CI 脚本必须在入口处写清职责。
- 自动生成代码也必须补齐用途注释后才能交付。
- 禁止提交无意义注释，例如“定义变量”“调用函数”“返回结果”。

## 2. 自动化测试注释要求

- 所有自动化测试代码必须注释说明测试目标、覆盖场景、前置数据、关键断言和清理逻辑。
- Playwright、pytest、API 自动化、CI 冒烟脚本都适用本规则。
- 当测试覆盖缺陷回归时，注释中必须标明缺陷编号、业务风险或历史问题背景。
- 当测试使用 mock、fixture、账号、环境变量或临时数据时，必须注释说明数据来源和隔离方式。

## 3. QA 自动化代码与数据分离

- QA 部门编写自动化测试时，测试逻辑与测试数据必须分离。
- 测试代码只保留流程编排、页面/接口操作、断言和清理逻辑。
- 测试数据必须放在 `tests/automation/fixtures/`、`tests/api-testing/environments/` 或对应模块的 fixture/data 文件中。
- 禁止在自动化脚本中硬编码账号、密码、Token、项目 ID、用户 ID、订单号、接口地址、环境名称等环境相关数据。
- 敏感数据必须通过环境变量或受控密钥配置注入。
- 场景数据应使用 JSON、YAML、CSV、fixture factory 或数据工厂生成，并用稳定命名表达用途。
- 测试运行前必须显式准备数据，运行后必须清理数据，避免污染共享环境。

## 4. React 副作用与 API 请求规范（强制）

> ⚠️ 本节约定了 React 组件中所有涉及 useEffect / useCallback / API 调用的铁律。违反即 Block PR。

### 4.1 useEffect 清理规则

**规则：每一个包含异步操作（API 调用、setTimeout、setInterval、订阅）的 useEffect 必须提供 cleanup 函数。**

```tsx
// ✅ 正确：cancelled 标志 + cleanup
useEffect(() => {
  let cancelled = false
  fetchData()
    .then((data) => { if (!cancelled) setData(data) })
    .catch(() => { if (!cancelled) setError(true) })
  return () => { cancelled = true }
}, [dep])

// ✅ 正确：AbortController（使用 useApi hook 的 signal）
const { data, refetch } = useApi(() => fetchX(id), [id])
// useApi 内部已有 AbortController 保护，无需额外 cancelled 标志

// ❌ 错误：异步操作无清理 — StrictMode 下必定重复请求
useEffect(() => {
  fetchData().then(setData)  // 卸载后仍然 setData → 内存泄漏 + 重复请求
}, [])
```

**为什么是铁律**：
- React 18 StrictMode 在开发模式下会 double-invoke 所有 effect（mount → unmount → mount），无 cleanup 的 effect 会产生两份重叠请求
- 快速切换页面/标签时，旧请求的回调可能覆盖新请求的结果（race condition）

### 4.2 useCallback 循环依赖禁止

**规则：useCallback 的依赖数组中禁止包含该 callback 内部会 SET 的状态变量。**

```tsx
// ❌ 错误：循环依赖触发 cascade effect
const loadItems = useCallback(async () => {
  const rows = await fetchItems()
  setItems(rows)
  if (rows.length > 0) setSelectedId(rows[0].id)  // 内部 SET selectedId
}, [projectId, selectedId])  // ← selectedId 又在 deps 中 → 循环！

// ✅ 正确：移除被 SET 的变量，用 ref 守卫自动选择
const loadItems = useCallback(async () => {
  const rows = await fetchItems()
  setItems(rows)
}, [projectId])  // 只依赖外部输入

const initialSelectDone = useRef(false)
useEffect(() => {
  if (items.length > 0 && !initialSelectDone.current) {
    initialSelectDone.current = true
    setSelectedId(items[0].id)  // 自动选择只执行一次
  }
}, [items])
```

**为什么是铁律**：
- 状态变量在 callback 中被 SET → callback 引用变化 → 依赖该 callback 的 useEffect 重新执行 → 再次 SET → 无限 cascade
- StrictMode 下每一轮都 ×2，导致 4-6 次重复请求

### 4.3 N+1 查询禁止（前端侧）

**规则：禁止在循环/遍历中对每个 item 单独发起 API 请求获取计数或详情。必须在后端提供批量接口。**

```tsx
// ❌ 错误：每个 service 发一次 page_size=1 请求拿 endpoint 数量
services.forEach(svc => {
  fetchEndpoints({ service_id: svc.id, page_size: 1 })  // N 个请求！
})

// ✅ 正确：后端 list 接口直接返回 count 字段
const rows = await fetchApiServices(projectId)
// rows 每个 item 已有 endpoint_count 字段，一次请求搞定
```

**后端对应的正确做法**：
```python
# 一条 SQL GROUP BY 替代 N 条 COUNT
counts = db.query(Model.service_id, func.count(Model.id)) \
    .filter(Model.service_id.in_(service_ids)) \
    .group_by(Model.service_id).all()
```

### 4.4 TabsContent 条件渲染规则

**规则：使用 shadcn/ui TabsContent 时，必须加 `forceMount` + 条件渲染，防止非活跃 tab 的子组件挂载并发起请求。**

```tsx
// ❌ 错误：所有 tab 的 children 都会挂载，即使不活跃
<TabsContent value="tab1"><HeavyComponent /></TabsContent>
<TabsContent value="tab2"><AnotherComponent /></TabsContent>

// ✅ 正确：只渲染当前活跃 tab
<TabsContent value="tab1" forceMount>
  {activeTab === 'tab1' && <HeavyComponent />}
</TabsContent>
<TabsContent value="tab2" forceMount>
  {activeTab === 'tab2' && <AnotherComponent />}
</TabsContent>
```

### 4.5 请求合并检查清单

在提交 PR 前，打开浏览器 DevTools Network 标签，刷新页面后确认：

- [ ] 每个 GET 请求只出现 **1 次**（开发模式 StrictMode + cancelled 标志下仍为 1 次有效请求；浏览器可能显示 2 次但只有 1 次完成数据更新）
- [ ] 不存在 `page_size=1` 的探针式请求（用于获取总数的）
- [ ] 切换 tab 时，非活跃 tab 不发起任何网络请求
- [ ] 分页/筛选只在用户手动操作时触发，不在页面加载时自动触发
- [ ] 列表项的自动选中不会触发级联的数据加载

### 4.6 自检脚本

```bash
# 启动前端后运行，统计每个 API 路径的请求次数
# 如果同一路径出现 >2 次（StrictMode 上限），则有 bug
curl -s http://localhost:5173/apitest > /dev/null
# 在 DevTools Network 面板手动验证
```

## 5. 交付检查

代码层面交付前必须自查：

- 是否为新增/修改的业务逻辑和自动化测试补充了用途注释。
- 是否避免了只解释语法的低价值注释。
- QA 自动化是否已经做到代码与数据分离。
- 测试数据是否可复用、可替换、可清理。
- 是否没有把敏感信息或环境绑定数据写死在代码里。
- **（新增）useEffect 是否有 cleanup（cancelled 标志或 AbortController）。**
- **（新增）useCallback 依赖数组是否包含内部会 SET 的状态变量 — 如有，必须重构。**
- **（新增）是否存在循环中的 API 请求（N+1）— 如有，必须改为后端批量接口。**
- **（新增）TabsContent 是否加了 forceMount + 条件渲染。**
- **（新增）Network 面板是否确认了每接口只请求 1 次。**
