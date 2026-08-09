# Batch 129 — PM Plan（访客功能浏览、项目引导与用例重分类）
> **PM (🟨)** | Date: 2026-08-09

## 规格摘要

**原始需求**：访客可进入所有功能模块查看能力；实际使用再登录；无项目时提示创建并停止缺 Project ID 请求；用例服务和脑图把旧“其他”数据归入正确端别和子模块。  
**目标时间**：单一完整批次完成实现、回归、三视口验收和 Leader 审查。

## 开发任务

### [ ] Task 1：访客模块说明路由

**描述**：新增模块能力目录与 `GuestModulePreview`；首页/侧栏的模块点击执行路由导航，说明页主操作才触发登录。

**验收标准**：
- 公开模块路径均能解析到名称、说明和能力点，未知路径有安全兜底。
- 直达或侧栏点击不弹登录；CTA 弹登录并保留原目标路径。
- 访客只调用公开访问配置，不挂载业务页。

**涉及文件**：
- `frontend/src/layouts/guestModuleCatalog.ts` — 模块说明事实表和解析器。
- `frontend/src/layouts/GuestModulePreview.tsx` — 模块说明页。
- `frontend/src/layouts/GuestPlatformHome.tsx` — 模块入口改为浏览导航。
- `frontend/src/layouts/MainLayout.tsx` — 访客路径渲染与登录动作分离。
- 对应 `layouts/__tests__/*` — 行为回归。

### [ ] Task 2：无项目布局边界

**描述**：在任何项目域 Outlet 挂载前检查项目上下文；无项目时渲染创建项目空状态，只放行项目/组织起步页面。

**验收标准**：
- `currentProjectId=null` 时项目域 Outlet 不挂载。
- 清晰展示原因、两步引导和“创建第一个项目”CTA。
- `/my-projects`、`/organizations` 可正常进入；选择项目后原业务路由恢复。

**涉及文件**：
- `frontend/src/layouts/ProjectRequiredState.tsx` — 无项目空状态。
- `frontend/src/layouts/MainLayout.tsx` — 路由白名单和边界。
- `frontend/src/layouts/__tests__/ProjectRequiredState.test.tsx`、`MainLayout.test.tsx` — 0 子页挂载/CTA 回归。

### [ ] Task 3：后端旧域重分类与单一 surface 契约

**描述**：把 31 个存量体育域纳入确定性用户端/运营后台映射；在 `TestCaseOut` 输出 `surface`，taxonomy 与列表共用同一分类器。

**验收标准**：
- 31/31 旧域无“其他”；API 类型优先归“接口测试”。
- 显式端别域保持现有结果；未知域仍归“其他”。
- `GET /test-cases` 和 `/test-cases/taxonomy` 对同一用例返回一致 surface。

**涉及文件**：
- `backend/app/services/test_case_service.py` — 旧域映射和响应字段。
- `backend/app/schemas/test_case.py` — `surface` 输出契约。
- `backend/tests/test_testcase.py` — 全域与 API 契约回归。
- `frontend/src/types/api.d.ts` — 锁定工具重生成 OpenAPI 类型。

### [ ] Task 4：脑图消费后端归类

**描述**：移除前端重复的业务域分类规则；脑图使用列表响应的 `surface`，筛选项由实际数据推导。

**验收标准**：
- 脑图和用例服务对同一数据集的端别一致。
- 没有未知域时不显示“其他”；未知域存在时显示并可筛选。
- 多级 module path、默认功能用例和现有渲染行为不回归。

**涉及文件**：
- `frontend/src/pages/mindmap/caseTaxonomy.ts` — 使用 surface 构建脑图与可用筛选。
- `frontend/src/pages/mindmap/index.tsx` — 动态界面筛选。
- `frontend/src/pages/mindmap/caseTaxonomy.test.ts` — 归类消费/模块树回归。

### [ ] Task 5：QA 与交付证据

**描述**：完成相关测试、双端硬门禁、Network 验证、三视口截图、Bug Scan、C 条件审计、QA/Leader 工件。

**验收标准**：
- 1440×900、768×1024、390×844 均无横向溢出，CTA 可达。
- 访客模块页业务请求为 0；无项目页面业务请求为 0。
- 前后端全量回归无新增失败；required checks 全绿后才允许 Leader APPROVED。

**涉及文件**：
- `work-logs/evidence/batch-129-guest-browse-project-taxonomy/**`
- `work-logs/batch-129-guest-browse-project-taxonomy-qa-report.md`
- `work-logs/batch-129-guest-browse-project-taxonomy-leader-verdict.md`
- `work-logs/kanbans/DEV-batch-129-guest-browse-project-taxonomy.md`

## 质量要求

- [ ] Desktop / Tablet / Mobile 响应式
- [ ] WCAG 标签、键盘焦点、44px 主触控目标
- [ ] OpenAPI/d.ts 同步
- [ ] useEffect 异步清理完整
- [ ] 访客与无项目 Network 证明无业务请求
- [ ] 相关单测 + 双端全量回归 + 构建门禁

