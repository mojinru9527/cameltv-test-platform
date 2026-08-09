# Batch 128 — PM Plan（公开访问、普通注册与用例分类体系）

> **PM (🟨)** | Date: 2026-08-09 | Mode: full

## 规格摘要

**目标**：闭环 PRD 的访客发现→登录、普通注册→项目创建、用例类型→端别/模块/子模块、脑图分层四条链路。
**范围原则**：不开放匿名业务数据、不做 DB 迁移、不改邀请链接既有语义。

## 开发任务

### [ ] Task 1：公开访问契约

**描述**：新增安全公开目录与注册策略响应；注册默认开放、邀请码默认可选。
**验收**：匿名 200；响应无用户/权限/项目数据；显式关闭或要求邀请码仍生效。
**文件**：`backend/app/api/v1/auth.py`、`schemas/auth.py`、`services/menu_service.py`、`core/config.py`、`tests/test_register.py`、新公开契约测试、运行配置示例。

### [ ] Task 2：游客平台壳与登录 Dialog

**描述**：根布局允许游客渲染公开目录；受保护 Outlet 不挂载；点击/直达受保护模块打开统一登录 Dialog。
**验收**：游客可见导航、登录、免费注册；点击模块弹窗；登录后进入原目标；无受保护 GET。
**文件**：`frontend/src/router/index.tsx`、`layouts/MainLayout.tsx`、`api/auth.ts`、`components/auth/*`、`pages/login/index.tsx`、对应测试。

### [ ] Task 3：普通注册入口

**描述**：注册页改为普通注册，邀请码按公开策略条件必填/可选，项目邀请 token 保持。
**验收**：无邀请码注册成功；显式要求邀请码时有字段级提示；成功进入我的项目。
**文件**：`frontend/src/pages/register/index.tsx`、`__tests__/RegisterPage.test.tsx`、登录页文案。

### [ ] Task 4：用例 taxonomy 契约

**描述**：新增端别分类与类型过滤；taxonomy 支持 `surface` 过滤；保留旧 domains 契约。
**验收**：canonical manual/functional 合并；用户端/后台/API/其他排序稳定；体育存量路径正确归类。
**文件**：`backend/app/services/test_case_service.py`、`schemas/test_case.py`、`api/v1/test_case.py`、`tests/test_testcase.py`、新 taxonomy 单测。

### [ ] Task 5：用例服务四类型与三级树

**描述**：加入接口/UI 页签；分类树改为端别→域→模块路径；各页签请求独立 taxonomy。
**验收**：默认 manual；切换页签只有一次列表与 taxonomy 请求；树选择能筛选 domain/叶子模块，端别节点作为分组入口。
**文件**：`frontend/src/api/testcase.ts`、`pages/testcase/index.tsx`、新 `caseTaxonomy.ts` 与测试、`index.test.tsx`。

### [ ] Task 6：脑图分层

**描述**：默认功能用例；增加类型/端别筛选；Markdown 层级消费模块路径。
**验收**：用户端/运营后台根清晰；`/` 路径拆成子模块；切换筛选正确请求且渲染清理安全。
**文件**：`frontend/src/pages/mindmap/index.tsx`、`index.test.tsx`、新纯函数测试。

### [ ] Task 7：QA 与交付

**验收**：相关/全量 Pytest、Vitest、typecheck/build、F821、Alembic、三视口 Playwright、GET 去重、C 条件和 common-bug 扫描全记录；QA/Leader/看板完成。

## 风险与依赖

- 生产 Railway 若仍显式设置旧注册变量，主干合入不会自动改外部环境；在 QA/Leader 中登记为发布配置动作，不伪装为已部署。
- taxonomy 是展示兼容层，未知旧数据归“其他”，避免过度推断导致错误归类。
- MainLayout 是高影响文件；用游客/登录两态组件测试和真实 Network 证据约束回归。
