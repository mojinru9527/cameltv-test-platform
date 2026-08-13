---
title: "测试平台 v2 现状功能 PRD"
owner: "qa-team"
last_reviewed: "2026-08-09"
status: "active"
expires: "2026-12-26"
tags: ["PRD", "现状", "功能清单", "基线"]
related: ["test-platform-v2/docs/CamelTv测试平台-完整PRD.md", "test-platform-v2/docs/代码审查与产品重构PRD.md", "test-platform-v2/docs/改进任务backlog.md"]
---

# CamelTv 测试平台 v2 —— 现状功能 PRD（As-Built）

> 文档性质：**现状反向 PRD**——逆向梳理平台「当前已实现」的功能，逐模块给出目标 / 用户故事 / 功能点 / 字段 / 状态机 / 业务规则 / 接口 / 成熟度标注。
> 用途：作为后续功能增 / 删 / 改的**基线**。每节末尾「现状与局限」即改进入口。
> 依据：当前 worktree 的锁文件、FastAPI 路由/认证实现、React 路由、Batch 127 生产只读走查、本地真实后端矩阵与自动化资产核对；历史截图、脚本存在或候选用例数均不单独构成通过证据。
> 版本：后端应用版本 `2.3.0`；依赖基线 FastAPI `0.140.13`、React `19.2.8`　日期：2026-08-09

---

## 0. 阅读指南

- **成熟度标记**：✅ 本地受控链路有可复核证据｜🟡 真实实现但生产级矩阵不完整｜⛔ 缺外部条件或明确延期。该标记不是发布准入结论。
- 每个功能点尽量给出真实接口路径（前缀 `/api/v1`）与关键字段。
- 字段「状态枚举」均来自后端 Schema 默认值与注释，是改进时的事实口径。

---

## 1. 产品概述

### 1.1 定位
一体化**测试管理平台**：覆盖「需求 → AI 生成用例 → 用例库 → 测试计划 → 执行 → 报告 / 缺陷」主链路，并提供工作台看板、定时任务、以及音视频 / UI / API 三个专项测试入口。支持多项目隔离与 RBAC 权限。

### 1.2 目标用户与角色
| 角色 | 默认账号 | 典型职责 |
|------|---------|---------|
| 超级管理员 | 由部署环境创建 | 全局配置、用户角色、项目、所有数据（权限码 `*`） |
| 测试人员 | 由管理员创建 | 需求/用例/计划/执行/缺陷/报告日常操作 |
| 自定义角色 | — | 按权限点 + 数据范围（global/project/self）灵活配置 |

### 1.3 技术架构（一句话）
前端 React 19.2.8 + React Router 8.3.0 + TS + shadcn/ui（SPA），后端 FastAPI 0.140.13 + SQLAlchemy 2.0.51 + SQLite（可升 PostgreSQL）；浏览器会话以承载 JWT 的 httpOnly Cookie 为主，Bearer 仅作过渡回退，APScheduler 调度，外接 DeepSeek LLM / ELK / 蓝湖。

### 1.4 模块全景与成熟度
| # | 模块 | 路由 | 成熟度与证据边界 |
|---|------|------|------------------|
| 1 | 登录与鉴权 | `/login` `/register` `/change-password` | ✅ Cookie 主会话、首次强制改密、旧会话失效与受保护路由门禁有自动化证据 |
| 2 | 工作台看板 | `/workbench` | 🟡 本地真数据可见；跨项目/全角色/响应式矩阵不完整 |
| 3 | 项目管理 | `/project` | ✅ 成员、主题、停用与顶部项目刷新有本地证据 |
| 4 | 系统管理（用户/角色/权限/审计） | `/system` | 🟡 RBAC/审计存在；admin/tester/viewer 全能力矩阵待补 |
| 5 | 需求管理 + AI 用例生成 | `/requirement` | 🟡 / ⛔ 本地持久化链可用；真实 LLM、蓝湖和旧 PostgreSQL 快照受外部输入阻塞 |
| 6 | 用例管理 / 脑图 | `/testcase` `/mindmap` | 🟡 CRUD、批量、导入导出与版本能力存在；破坏性操作、权限与全浏览器证据待补 |
| 7 | 测试计划与执行 | `/testplan` `/testplan/:id` | 🟡 本地状态流可用；批量、并发、权限和外部回写矩阵不完整 |
| 8 | 测试报告 | `/report` | 🟡 快照/导出可用；全量分页、响应式与权限验收待补 |
| 9 | 定时任务 | `/schedule` | 🟡 调度、空状态与部分 RBAC 有证据；生产环境保护待统一 |
| 10 | 缺陷管理 | `/defect` `/defect/:id` | 🟡 内建状态流、评论、附件与深链存在；全权限/原子性矩阵待补 |
| 11 | API 测试 | `/apitest` | 🟡 OpenAPI/Swagger 导入和 httpx 真实执行存在；五入口一致性、生产保护与 Test5 当前契约待验收 |
| 12 | UI 自动化 | `/uitest` | 🟡 本地 Runner 真实执行和产物链可用；不代表体育业务 E2E 通过 |
| 13 | 音视频专项 | `/special` | 🟡 真实样本/ffprobe 指标链已取代随机数；外部真实流矩阵未完成 |
| 14 | 环境 / 数据集 | `/environment` `/dataset` | 🟡 项目级数据与加密变量存在；跨项目和生产目标安全矩阵待补 |
| 15 | 通知 / 集成 | `/notify` `/integration` | ⛔ 本地模型与错误路径可验；真实 SMTP/Webhook/Jira/TAPD/ELK 缺凭据和非生产端点 |
| 16 | 知识 / Agent / 发布包 | `/knowledge` `/agent-workbench` `/release-bundles` | 🟡 / ⛔ 前置条件缺失时已 fail closed；真实外部链和交互标注回归待补 |
| 17 | 性能监控 | `/perftest` | ⛔ 缺 SoloX、授权真机和采集窗口，页面存在不等于验收通过 |
| 18 | 开放 API | API-only `/api/v1/open` | 🟡 独立 API Token Bearer 鉴权；前端入口和生产级契约证据不完整 |
| 19 | 主题实验室 | `/theme-lab` | ✅ 本地设计/响应式验证工具，不是业务生产能力 |
| 20 | 运维发布控制 | `/operations-release` | 🟡 只读控制面已存在；store 未配置时为受控 503/未启用态，不提供发布、审批或回滚操作 |
| 21 | 我的项目 / 组织 | `/my-projects` `/organizations` | 🟡 项目加入、邀请与组织层已实现；跨组织管理写路径继续由 RBAC/隔离测试约束 |
| 22 | Playground / 蓝湖证据 | `/playground` `/lanhu-evidence` `/lanhu-evidence/:id` | 🟡 / ⛔ 页面、任务和详情存在；AI、蓝湖登录态、采集与 OCR 仍受真实 Provider 条件约束 |

---

## 2. 全局机制（跨模块通用规范）

### 2.1 登录与会话
- 账号密码登录签发 JWT（`access_token_expire_minutes` 默认 1440min/24h），同时写入名为 `cameltv_token` 的 `httpOnly` Cookie；默认 `SameSite=Lax`、`Path=/api`，production 配置必须启用 `Secure`。
- 登录响应依然返回 `access_token` 以兼容过渡期客户端。前端 Zustand `cameltv-auth` 只持久化用户、项目、权限和主题等非 Token 状态；Token 仅在当前内存会话中保留作 Bearer 回退，刷新后由 Cookie 继续鉴权。
- API 客户端使用 `withCredentials: true`，后端优先读 Cookie，仅在 Cookie 缺失时接受 `Authorization: Bearer` 并记录弃用回退告警；独立开放 API Token `tpat_*` 仍使用 Bearer，与浏览器 JWT Cookie 会话分离。
- Cookie 写请求受 Origin/Referer CSRF 中间件保护；`401` 由前端清理本地用户态并跳转 `/login`，显式登出先请求 `/api/v1/auth/logout` 清除 Cookie。

### 2.2 多项目隔离
- 登录后选择「当前项目」，前端在每个请求注入 `X-Project-Id`。
- 后端绝大多数业务接口以 `project_id` 做数据隔离；`require_project` 校验用户是该项目成员（超管放行）。
- 每个项目可独立设置主题色（前端 `projectThemeMap`，8 色可选）。

### 2.3 RBAC 权限模型
- **用户—角色—权限点** 多对多；角色含**数据范围** `global / project / self`。
- 权限点 `type ∈ {menu, button, api}`；权限码示例 `case:list`、`plan:create`；超管持 `*` 通配。
- 角色分「全局角色（project_id=0）」与「项目内角色」，按当前项目合并计算权限码。
- 前端 `hasPerm(code)` 控制按钮级显隐；后端 `require_permission('xxx')` 控制接口级访问。

### 2.4 菜单
- 菜单由后端 `/system/menus` **动态下发**（非前端写死），含 code/name/path/icon/sort/children，前端按 icon 字符串映射 lucide 图标渲染侧边栏。

### 2.5 统一交互规范
- 统一响应体 `{code, msg, data}`；`code=0` 成功，前端拆 `data`；非 0 toast 报错。
- 列表统一分页（默认 `page_size=20`），支持关键词 + 多维筛选。
- 删除操作前端统一二次确认弹框；操作以 toast 反馈。
- 关键写操作记录**审计日志**（操作人/动作/对象/IP/时间）。

---

## 3. 功能模块 PRD（逐模块）

### 模块 1　登录与鉴权 ✅
**目标**：身份认证与会话建立。
**用户故事**：作为用户，我用账号密码登录后进入工作台，并能切换我参与的项目。
**功能点**
- 账号密码登录　`POST /auth/login` → Cookie + `{access_token, token_type, user, projects, permissions, must_change_password}`
- 获取当前用户　`GET /auth/me`
- 退出登录　`POST /auth/logout`（后端清 Cookie，前端清内存/持久化用户态）
- 修改/找回/重置密码　`POST /auth/change-password|forgot-password|reset-password`；`GET /auth/sso-config` 只返回 OIDC 配置状态
**业务规则**：用户 `status≠1`（禁用）拒绝登录；同 IP 登录有限频；Token 失效返回 401。
**现状与局限**：OIDC 是配置状态占位，未证明完整 SSO 登录链；Bearer 过渡回退尚未移除；`must_change_password` 用户只允许改密/登出的前后端强制门禁和旧会话失效仍属 Batch 61 验收项。

---

### 模块 2　工作台看板 ✅
**目标**：当前项目质量数据一屏概览。
**功能点**　`GET /dashboard/stats`
- 顶部卡片：用例总数 `total_cases`、计划总数 `total_plans`、接口用例数 `api_cases`、总体通过率 `pass_rate`。
- 按**用例类型**（功能 manual / 接口 api / 自动化 ui）统计：用例数、执行总次数、通过/失败次数、通过率/失败率（带配色）。
- 按**用例类型 × 优先级**（P0–P3）分布。
- 支持时间范围筛选 `time_range`。
- 前端用 Recharts 渲染图表。
**现状与局限**：维度固定（类型/优先级）；无趋势曲线、无缺陷收敛、无个人/团队维度、无自定义看板。

---

### 模块 3　项目管理 ✅
**目标**：多项目及成员管理，承载数据隔离。
**功能点**
| 操作 | 接口 |
|------|------|
| 我可见的项目 | `GET /project` |
| 校验当前项目 | `GET /project/current` |
| 全量项目（管理） | `GET /project/all` |
| 项目详情 | `GET /project/{id}` |
| 创建/编辑/删除（软删 status=0） | `POST` / `PUT` / `DELETE /project/{id}` |
| 成员增改/移除/列表 | `POST` `DELETE /project/{id}/members[/{user_id}]`、`GET /project/{id}/members` |
**字段**：name、描述、status(1 正常/0 删除)、成员(user_id+role)。
**现状与局限**：无项目模板/归档/克隆；成员仅「用户+角色」，无批量。

---

### 模块 4　系统管理 ✅
**目标**：用户、角色、权限、审计的后台管理（Tabs 页）。
**4.1 用户管理**　`/system/users`
- 列表/详情/新建/更新/删除（`GET/POST/PUT/DELETE`）。
- 字段：username、nickname、email、status(1/0)、role_codes[]、last_login_at；新建用户必须显式提供至少 6 位密码，无通用默认密码，更新时密码留空即不改。
**4.2 角色管理**　`/system/roles`
- 列表/详情/新建/更新/删除。
- 字段：code、name、data_scope(global/project/self)、remark、permission_codes[]。
**4.3 权限点**　`GET /system/permissions` 按 group 分组返回（前端 Checkbox 勾选授权）。
**4.4 审计日志**　`GET /system/audit-logs` 分页：user/username、project_id、action、target、detail、ip、time。
**现状与局限**：权限点与菜单混在一张表；无组织/部门树；审计无导出；无操作前后值 diff。

---

### 模块 5　需求管理 + AI 用例生成 🟡（依赖外部 LLM）
**目标**：上传需求 → 功能拆分与确认 → AI 生成 → 持久审查 → 选择性导入用例库。
**主流程**
```
上传文档(MD/Word/Excel)或导入蓝湖证据包 → 功能拆分/确认 → AI 生成
→ 持久审查(编辑/通过/驳回) → 幂等导入 → 用例库
```
**功能点**
| 操作 | 接口 | 说明 |
|------|------|------|
| 文档列表/详情 | `GET /requirements`、`GET /requirements/{id}` | 服务端分页/搜索；列表不携带正文，详情按需读取 |
| 上传文档 | `POST /requirements/upload` | 20 MB 上限；识别 MD/Word/Excel；蓝湖正式导入先走证据包门禁 |
| 功能拆分/读取/确认 | `POST /requirements/{id}/extract`、`GET /requirements/{id}/extraction`、`POST /requirements/{id}/extraction/confirm` | 拆分结果持久化，支持确认/驳回与刷新恢复 |
| AI 生成 | `POST /requirements/{id}/generate` | `use_extraction=true` 时基于已确认拆分生成 |
| 审查 | `GET /requirements/{id}/review-state`、`POST /requirements/{id}/review/{case_index}` | 编辑、通过、驳回状态持久化 |
| 导入用例 | `POST /requirements/{id}/import` | 按全局 `indices[]` 选择；编辑值真实入库；事务、重复请求和计数受保护 |
| 查看已生成用例 | `GET /requirements/{id}/cases` | |
| 覆盖率/API 关联 | `GET /requirements/{id}/coverage`、`POST /requirements/{id}/match-api/confirm` | 关联持久化并可刷新恢复 |
| 删除文档 | `DELETE /requirements/{id}` | 关联审查状态与业务审计同事务清理/提交 |
**AI 输出结构**（`AIGenerateResult`）
- **需求分析** `requirement_analysis`：抽取的需求项（REQ-x，类型 functional/ui/data/integration）+ 每项**问题清单**（severity high/medium/low + 描述 + 建议）+ 总体评估。
- **功能用例** `functional_cases[]` 与 **接口用例** `api_cases[]`：title、case_type、priority(P0-P3)、domain、module、preconditions、steps(JSON)、expected_result、api_method/endpoint、remark、imported(是否已导入)。
- 导入结果：imported / skipped / total。
- 文档状态：uploaded；统计 imported_count / func / api。
**特色**：除生成用例外，AI 还会**反向评审需求**（指出需求文档自身的问题与建议）。
**现状与局限**：真实 LLM 和蓝湖 Provider 仍是外部依赖；从脱敏真实旧版 PostgreSQL 快照升级的证据尚未完成，不能据本地自动化直接判定生产就绪。

---

### 模块 6　用例管理 ✅
**目标**：测试用例全生命周期管理 + 域/模块树导航。
**功能点**
| 操作 | 接口 |
|------|------|
| 域树（domain→module→count） | `GET /testcase/domains` |
| 用例列表（分页+筛选） | `GET /testcase` |
| 详情/新建/编辑/删除 | `GET/POST/PUT/DELETE /testcase/{id}` |
**筛选维度**：domain、module、case_type、priority、status、keyword。
**核心字段**（`TestCaseOut`）
| 字段 | 枚举/说明 |
|------|----------|
| case_id | 用例编号（业务编号） |
| title | 标题 |
| domain / module | 域 / 模块（树形分类） |
| case_type | manual 功能 / api 接口 / ui 自动化 |
| priority | P0 / P1 / P2 / P3 |
| status | active（启用） |
| tags | JSON 字符串 |
| preconditions | 前置条件 |
| steps | 步骤（JSON 字符串） |
| expected_result | 预期结果 |
| api_method / api_endpoint / api_spec_ref | 接口用例专用 |
| source | manual / migration / ai（来源） |
**现状与局限**：已有提交/通过/驳回/撤回评审流及历史，版本列表/详情，Excel/Xmind 导入导出，批量优先级更新和批量删除。当前局限是批量破坏操作仍需完成真实浏览器 + DB + 审计 + 失败原子性回归，无回收站，需求↔用例追溯和脑图交互也尚未完成全矩阵生产验收。

---

### 模块 7　测试计划与执行 ✅（管理闭环核心）
**目标**：组织用例成计划、逐条执行、沉淀执行记录与统计。
**7.1 计划管理**
| 操作 | 接口 |
|------|------|
| 计划列表（分页） | `GET /test_plan` |
| 创建/详情/编辑/删除 | `GET/POST/PUT/DELETE /test_plan/{id}` |
- 计划字段：plan_id、name、description、status(**draft/active/completed/archived**)、start_date、end_date、creator。
**7.2 计划内用例**
| 操作 | 接口 |
|------|------|
| 批量加入用例 | `POST /test_plan/{id}/cases`（case_ids[]） |
| 移除用例 | `DELETE /test_plan/{id}/cases` |
| 调整顺序 | `PUT /test_plan/{id}/cases/{pcase_id}/sort` |
- 计划内用例携带：sort_order、last_status(pending)、last_executed_at、executor，及用例摘要（标题/编号/域/模块/优先级/类型）。
**7.3 执行**
| 操作 | 接口 |
|------|------|
| 执行单条用例 | `POST /test_plan/{id}/cases/{pcase_id}/execute` |
| 执行记录（分页） | `GET /test_plan/{id}/executions` |
| 计划统计 | `GET /test_plan/{id}/stats` |
- 执行结果状态：**pass / fail / skip / block**；记录 actual_result、notes、executor、executed_at。
- **ELK 联动**：执行记录自动提取 `trace_id` 并生成 `kibana_link`（便于排障）。
- 统计 `PlanStats`：total / pending / pass / fail / skip / block。
**现状与局限**：执行为手工逐条；无批量执行、无执行指派/分配、无关联自动化用例自动回填结果。

---

### 模块 8　测试报告 ✅
**目标**：基于测试计划生成执行结果快照报告。
**功能点**
| 操作 | 接口 |
|------|------|
| 报告列表 | `GET /report` |
| 生成报告（计划快照） | `POST /report` |
| 报告详情 | `GET /report/{id}` |
| 删除报告 | `DELETE /report/{id}` |
- 报告以 **JSON 快照**保存生成时的执行统计；编号形如 `RP-YYYYMMDD-NNN`。
**现状与局限**：仅单计划快照；无多计划趋势、无质量门禁、无 PDF/Excel 导出、无自定义模板、无报告分享链接。

---

### 模块 9　定时任务 ✅
**目标**：按 Cron 周期自动触发测试计划。
**功能点**
| 操作 | 接口 |
|------|------|
| 列表 | `GET /schedule` |
| 创建/详情/编辑/删除 | `GET/POST/PUT/DELETE /schedule/{id}` |
| 立即触发 | `POST /schedule/{id}/trigger` |
| 执行历史 | `GET /schedule/{id}/runs` |
- 字段：name、plan_id（绑定计划）、cron_expression（**后端校验合法性**）、enabled、next_run、last_run。
- 运行记录：status、result、error_message、started/finished_at。
- 引擎：APScheduler，应用启动随生命周期初始化。
**现状与局限**：失败无重试/无告警通知；执行动作受限于计划本身能力。

---

### 模块 10　缺陷管理 🟡
**目标**：登记缺陷、关联用例/执行，并在平台内完成状态流转与审计。
**功能点**
| 操作 | 接口 |
|------|------|
| 缺陷统计 | `GET /defect/stats`（按 severity / status 分组） |
| 列表（分页+筛选） | `GET /defect` |
| 创建/详情/编辑/删除 | `GET/POST/PUT/DELETE /defect/{id}` |
- 字段：defect_id（自动编号）、title、description、severity(**P0/P1/P2/P3**)、status(默认 **open**)、case_id、execution_id、assignee、external_id、external_url、creator、resolved_at。
- 内建状态机：`open → confirmed → fixing → pending_review → closed`，支持合法的 `rejected` 与 reopen；每次流转记录前后状态、操作人、备注与时间。
- 关联：可挂到具体用例与执行记录；提供评论、附件上传/下载/删除和深链详情。
**现状与局限**：内建流转与本地评论/附件已实现，但批量破坏性操作的原子性、全角色权限和外部 Jira/TAPD 真实双向链仍未完成生产级验收。

---

### 模块 11　API 测试 🟡（真实执行，能力待生产化）
**目标**：管理 API 资产、生成接口用例、批量/单次执行并产出结构化结果。
**现状实现**
- **服务端真实执行引擎**：后端通过 `httpx` 发起真实 HTTP 请求（`api_execution_service.py`），绕过浏览器跨域限制。
- **资产四层模型**：ApiService（分组）→ ApiEndpoint（接口定义，含 method/url/headers/body）→ TestCase（用例，含断言 JSONPath）→ ApiExecutionTask（执行批次，含 request/response 快照）。
- **完整接口**：`/api/v1/apitest/services|endpoints|tasks` CRUD + OpenAPI 导入预览/确认 + AI 用例生成（DeepSeek）+ 批量任务创建/取消/重试失败 + 失败分析 + curl 命令导出。
- **OpenAPI 导入边界**：解析 OpenAPI 3.x 与 Swagger 2.0 JSON/YAML，支持文本或 URL；Knife4j/Swagger 文档 URL 作为来源类型记录。预览不写库，确认后才建立服务/端点资产。平台自身的 FastAPI 运行时契约为 `/openapi.json`，与导入的被测系统契约是两类对象。
- **请求/响应快照**：每次执行保存结构化 `request_snapshot`（method/url/headers/body）和 `response_snapshot`（status_code/headers/body_preview/body_size_bytes/truncated/content_type），可回溯。
- **断言引擎**：支持 JSONPath 提取 + 比较运算符（equals/contains/regex/gte/lte），结果写入 `assertion_results`。
- **批量任务工作器**：独立 daemon 线程 `api_task_worker.py`，claim-based 抢占（locked_by/locked_at），支持 cancel 中途取消 + retry-failed 重试。
- **环境与变量注入**：通过 `environment_id` 关联环境（base_url），支持 AES-128 加密变量 `${VAR_NAME}` 解析；生产环境需 `apitest:execute_prod` 权限 + `confirm_prod` 二次确认。
- **SSRF 防护现状**：无环境时校验目标 URL 非内网/回环地址；关联环境后的 host allowlist、私有 Test5 策略与重定向逐跳复验是 Batch 61 待收紧项，不得因存在 `environment_id` 而宣称 SSRF 安全闭环。
- **前端四 Tab**：Assets（服务+接口管理）、Debug（即时调试，环境选择器+请求构建器+响应查看器）、Cases（用例列表+批量执行）、Tasks（任务列表+详情含请求/响应快照+分析）。
**局限/改进入口**：任务取消为轮询点协作取消；五个执行入口尚需统一 request builder、环境/变量解析、断言类型和生产拒绝语义。Batch 60 只用 5-path 本地 OpenAPI 完成了资产→用例→计划/报告的 R1 链；没有当前 Test5 六服务全量契约与授权执行，不能计为体育 API 业务回归通过。

---

### 模块 12　UI 自动化 🟡（真实执行，能力待生产化）
**目标**：管理 UI 自动化 Job、真实驱动 Playwright 执行、产出并回看截图/视频/trace 产物。
**现状实现**
- **真实 Playwright 执行引擎**：后端 `playwright_executor.py` 通过 `subprocess.Popen` 启动 `npx playwright test {spec} --project {browser} --reporter json --output {artifact_dir}`，在独立 worker 线程中执行。
- **三层模型**：UiTestJob（任务定义：spec/browser/environment）→ UiTestRun（单次执行：status/result/artifacts/process_id）→ UiTestScript（脚本资产目录）。
- **完整接口**：`/api/v1/ui-tests/jobs|runs|scripts` CRUD + `/api/v1/ui-tests/jobs/{id}/trigger` 触发 + `/api/v1/ui-tests/runs/{run_id}/cancel` 取消 + `/api/v1/ui-tests/runs/{run_id}/artifacts` 产物列表/下载 + `/api/v1/ui-tests/runner/health` 健康检查。
- **产物捕获**：执行后自动收集 `artifact_dir` 下所有 `*.png`（截图）、`*.webm`（视频）、`*.zip`（trace），路径写入 `run.screenshots[]`/`video_url`/`trace_id`；支持 Playwright HTML report（`index.html`）在线浏览。
- **前端产物回看**：Run Detail 弹窗展示截图缩略图三列网格（`<img>` 直接加载）、HTML5 `<video controls>` 播放视频、trace `.zip` 下载链接 + Playwright Trace Viewer 引导、stdout/stderr 终端输出、HTML Report 在线链接。
- **实时状态追踪**：前端 3 秒轮询刷新 running/pending 状态；process_id 可追踪子进程；cancel_requested 标志 + `proc.kill()` 可中止执行。
- **并发控制**：`ui_runner_queue.py` ThreadPoolExecutor（max_workers=2）+ 信号量保护；支持重启后恢复 pending runs。
- **环境变量注入**：执行时注入 `BASE_URL`、解密后的环境变量（`EnvironmentVariable` AES-128），spec 可通过 `process.env` 读取。
- **任务工作器双通路**：`ui_runner_queue.enqueue_run()` 即时入队 + `task_worker._process_ui_runs()` APScheduler 每 5 秒兜底轮询。
- **失败分析与知识入库**：`failure_analyzer.analyze_ui_failure()` 分类错误；失败执行自动通过 `ingest_service` 入库知识中心。
- **内置 Spec**：`production-smoke.spec.ts`（首页/登录/导航/API 健康/性能）、`production-web-smoke.spec.ts`（轻量 Web smoke）。文件名中的 `production` 不决定实际目标；执行环境由 Job 绑定和 `BASE_URL` 决定。
- **用例编译链路**：`case_compiler_service.py` 支持 功能用例 JSON steps → LLM (DeepSeek) → TypeScript `.spec.ts` → tsc 类型检查 → playwright --dry-run 验证 → 可执行文件。
**局限/改进入口**：Runner 由本地队列/工作线程执行预置 spec，不是任意脚本上传服务；失败截图/video/trace 与受保护产物回看已实现，但每个正常成功功能的发布证据需要另行采集。Batch 60 Run #5 的 4 pass / 0 fail / 1 skip 只证明本地测试平台 Runner 能启动 Chromium、执行断言并持久化终态；它不证明 Test5/生产体育登录、赛事、文章、充值、退币、赠送或运营后台 E2E 通过。体育业务资产位于 `tests/automation/ui/`，必须在获授权目标上单独执行并与 Runner smoke 分开统计。

---

### 模块 13　音视频专项 🟡（真实样本链，验收待完整）
**目标**：对流地址做音视频质量检测。
**功能点**
| 操作 | 接口 |
|------|------|
| 任务列表 | `GET /av_check` |
| 创建/详情/删除 | `GET/POST/DELETE /av_check/{id}` |
| 触发检测 | `POST /av_check/{id}/trigger` |
| 指标明细 | `GET /av_check/{id}/metrics` |
- 字段：name、stream_url、protocol（前端可选 HLS/FLV/WebRTC/DASH/HTTP/HTTPS）、status、last_result。
- 指标：metric_name、metric_value、threshold、pass、detail（如「起播时延 ms/2000」「卡顿率 %/5」）。
**关键现状**：随机数指标已替换为真实媒体样本探测，Batch 60 以真实 HTTP MP4 与 ffprobe 完成六指标、幂率、统计、阈值、幂等性与前端终态回读的本地闭环。
**改进入口**：外部实时流、多协议、异常网络、长时窗和授权环境矩阵未完成，因此不能从本地 MP4 证据推导生产流质量已通过。

---

## 4. 数据字典（核心枚举速查）

| 域 | 枚举值 |
|----|--------|
| 用例类型 case_type | manual(功能) / api(接口) / ui(自动化) |
| 优先级 priority / severity | P0 / P1 / P2 / P3 |
| 用例来源 source | manual / migration / ai |
| 计划状态 plan.status | draft / active / completed / archived |
| 计划内用例 last_status | pending / pass / fail / skip / block |
| 执行结果 execution.status | pass / fail / skip / block |
| 缺陷状态 defect.status | open / confirmed / fixing / pending_review / closed / rejected（closed/rejected 可 reopen 至 open） |
| 角色数据范围 data_scope | global / project / self |
| 权限点类型 permission.type | menu / button / api |
| 音视频协议 protocol | HLS / FLV / WebRTC / DASH / HTTP / HTTPS |
| 浏览器 browser | chromium / firefox / webkit |
| 需求解析类型 parsed_type | requirement / test_cases |
| 需求项类型 | functional / ui / data / integration |

---

## 5. 现状总结与改进基线

### 5.1 已有的本地真实链
需求/资产 → 用例库 → 测试计划 → 执行 → 报告/缺陷/追溯的本地链存在，RBAC、多项目和审计也有真实实现。API 测试是后端 httpx 真实执行，UI Runner 是真实 Playwright 子进程，音视频已有真实媒体样本指标链。这些结论仅限具体已执行的 R1/本地证据。

### 5.2 生产级结论与边界
Batch 60 最终结论是 `NEEDS WORK`，production 发布是 `DEFERRED`。平台本地 Runner 成功不是体育业务 E2E；OpenAPI 导入成功不是 Test5 六服务契约回归；脚本可收集、历史截图、892 个资产或 1323 条候选用例也不是本轮通过数。真实 LLM/蓝湖/通知/集成/真机/旧 PostgreSQL 快照缺授权输入时必须保持 `BLOCKED` 或 fail closed。

### 5.3 Batch 61 事实源对应的待闭环项
1. 统一 API/UI/发布包/集成等执行入口的目标环境、请求性质、生产拒绝与审计语义。
2. 完成全模块 A→B→A 项目隔离和 admin/tester/viewer 能力矩阵，补破坏性操作、强制改密、无障碍与响应式证据。
3. 将运行时数据库、备份、Playwright 结果/报告和原始流量产物排除在版本库外，已跟踪产物需在明确授权后单独移除。
4. 取得当前 Test5 六服务契约、最小权限账号、稳定数据和清理授权后，才能单独签发体育 API/UI R2 结论。
5. 解决体育 UI 自动化供应链高危依赖，并获取完整后端依赖审计结果。
6. 在仓库独立项目 `deploy/release-control/` 实现 test-only 不可变发布、回滚和防篡改证据；Batch 61 没有产品控制台 UI，production 操作必须返回 `PRODUCTION_NOT_CONFIGURED`，控制面 API/UI 是 Batch 62 消费者。

---

*配套文档：本目录另有《代码审查与产品重构PRD.md》（技术债 + 重构优先级 + 未来路线图）。本文聚焦「现在有什么」，可据「5.3」逐条拆分为改进需求 / issue。*

## 6. Batch 167 能力增补（版本级三类型覆盖主链路 Phase 0–3）

> 状态：已落地（本分支），生产走查待真实版本数据（见 C167-2）。

- **版本覆盖矩阵（Phase 0）**：`GET /release-bundles/{id}/coverage` 按模块 × 功能/接口/UI × 执行状态计算覆盖。口径：模块被覆盖 = 三类用例同时存在；执行覆盖 = API 与 UI 均已执行；分母 = 版本全部模块，60% 门禁，P0/P1 单独统计。
- **需求源适配（Phase 1）**：`/requirements/upload` 新增 `source_url`（generic HTML / PingCode / Confluence），token 走环境变量、缺凭据 fail closed；`GET /requirements/{id}/extraction-quality` 透出 分块/截断/降级 状态；大文档自动分块提取合并。
- **接口真实绑定（Phase 2）**：`POST /requirements/{id}/generate-api-from-endpoints` 对 integration 功能点匹配已导入 ApiEndpoint，确定性生成接口用例并回填 `requirement_module_id`，重复生成幂等。
- **功能→UI 与 auto_ui（Phase 3）**：导入功能用例可选生成 UI 变体并三类关联计划；`POST /test-plans/{id}/execute-all` 支持 `auto_ui`，manual P0/P1 有步骤用例自动 LLM 优先编译执行（规则引擎兜底），无步骤仍 skip。
- 发布包新增接入字段：需求地址、用户端地址、OpenAPI/Swagger 地址、运营后台地址、账号环境 ID；`POST /release-bundles/{id}/import-requirement` 从需求地址创建需求文档。
