---
title: "测试平台 v2 现状功能 PRD"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["PRD", "现状", "功能清单", "基线"]
related: ["test-platform-v2/docs/CamelTv测试平台-完整PRD.md", "test-platform-v2/docs/代码审查与产品重构PRD.md", "test-platform-v2/docs/改进任务backlog.md"]
---

# CamelTv 测试平台 v2 —— 现状功能 PRD（As-Built）

> 文档性质：**现状反向 PRD**——逆向梳理平台「当前已实现」的功能，逐模块给出目标 / 用户故事 / 功能点 / 字段 / 状态机 / 业务规则 / 接口 / 成熟度标注。
> 用途：作为后续功能增 / 删 / 改的**基线**。每节末尾「现状与局限」即改进入口。
> 依据：`F:\CamelTv\test-platform-v2` 源码逐文件核对（后端 FastAPI / 前端 React），结论可在源码验证。
> 版本：对应后端 `app_version = 2.1.0`　日期：2026-06-22

---

## 0. 阅读指南

- **成熟度标记**：✅ 生产可用｜🟡 可用但能力有限｜🧪 **演示态（数据为模拟/前端本地，不具生产能力）**
- 每个功能点尽量给出真实接口路径（前缀 `/api/v1`）与关键字段。
- 字段「状态枚举」均来自后端 Schema 默认值与注释，是改进时的事实口径。

---

## 1. 产品概述

### 1.1 定位
一体化**测试管理平台**：覆盖「需求 → AI 生成用例 → 用例库 → 测试计划 → 执行 → 报告 / 缺陷」主链路，并提供工作台看板、定时任务、以及音视频 / UI / API 三个专项测试入口。支持多项目隔离与 RBAC 权限。

### 1.2 目标用户与角色
| 角色 | 默认账号 | 典型职责 |
|------|---------|---------|
| 超级管理员 | admin / admin123 | 全局配置、用户角色、项目、所有数据（权限码 `*`） |
| 测试人员 | tester / tester123 | 需求/用例/计划/执行/缺陷/报告日常操作 |
| 自定义角色 | — | 按权限点 + 数据范围（global/project/self）灵活配置 |

### 1.3 技术架构（一句话）
前端 React18 + TS + shadcn/ui（SPA），后端 FastAPI + SQLAlchemy2.0 + SQLite(可升 PostgreSQL)，JWT 鉴权，APScheduler 调度，外接 DeepSeek LLM / ELK / 蓝湖。

### 1.4 模块全景与成熟度
| # | 模块 | 路由 | 成熟度 |
|---|------|------|--------|
| 1 | 登录与鉴权 | `/login` | ✅ |
| 2 | 工作台看板 | `/workbench` | ✅ |
| 3 | 项目管理 | `/project` | ✅ |
| 4 | 系统管理（用户/角色/权限/审计） | `/system` | ✅ |
| 5 | 需求管理 + AI 用例生成 | `/requirement` | ✅（依赖外部 LLM） |
| 6 | 用例管理 | `/testcase` | ✅ |
| 7 | 测试计划与执行 | `/testplan` `/testplan/:id` | ✅ |
| 8 | 测试报告 | `/report` | ✅ |
| 9 | 定时任务 | `/schedule` | ✅ |
| 10 | 缺陷管理 | `/defect` | 🟡（仅外链，无内建工作流） |
| 11 | API 测试 | `/apitest` | 🟡（真实 httpx 执行，待补齐快照/取消/生产保护） |
| 12 | UI 自动化 | `/uitest` | 🟡（真实 Playwright 执行，待补齐异步/环境/产物） |
| 13 | 音视频专项 | `/special` | 🧪（检测指标为随机数模拟） |

---

## 2. 全局机制（跨模块通用规范）

### 2.1 登录与会话
- 账号密码登录 → 返回 JWT（`access_token_expire_minutes` 默认 1440min/24h）。
- 前端持久化于 localStorage（key `cameltv-auth`，Zustand）；每次请求自动注入 `Authorization: Bearer <token>`。
- `401` 由前端拦截器自动登出并跳转 `/login`。

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
- 账号密码登录　`POST /auth/login` → `{token, user, projects, permissions}`
- 获取当前用户　`GET /auth/me`
- 退出登录（前端清除本地态）
**业务规则**：用户 `status≠1`（禁用）拒绝登录；token 失效自动登出。
**现状与局限**：仅账号密码；无验证码/锁定/SSO/找回密码/刷新令牌。

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
- 字段：username、nickname、email、status(1/0)、role_codes[]、last_login_at；新建默认密码 `123456`，更新时密码留空即不改。
**4.2 角色管理**　`/system/roles`
- 列表/详情/新建/更新/删除。
- 字段：code、name、data_scope(global/project/self)、remark、permission_codes[]。
**4.3 权限点**　`GET /system/permissions` 按 group 分组返回（前端 Checkbox 勾选授权）。
**4.4 审计日志**　`GET /system/audit-logs` 分页：user/username、project_id、action、target、detail、ip、time。
**现状与局限**：权限点与菜单混在一张表；无组织/部门树；审计无导出；无操作前后值 diff。

---

### 模块 5　需求管理 + AI 用例生成 ✅（核心亮点，依赖外部 LLM）
**目标**：上传需求 → AI 解析并生成测试用例 → 选择性导入用例库。
**主流程**
```
上传文档(MD/Word/Excel/蓝湖链接) → AI 生成(两段式) → 预览(AiResultModal) → 勾选导入 → 用例库
```
**功能点**
| 操作 | 接口 | 说明 |
|------|------|------|
| 文档列表 | `GET /requirement` | |
| 上传文档 | `POST /requirement/upload` | file_type 自动识别；Excel 可直接解析为用例(`parsed_type=test_cases`) |
| AI 生成 | `POST /requirement/{id}/generate` | 两段式：需求分析 + 用例生成 |
| 导入用例 | `POST /requirement/{id}/import` | 按 `indices[]` 选择性导入 |
| 查看已生成用例 | `GET /requirement/{id}/cases` | |
| 删除文档 | `DELETE /requirement/{id}` | |
**AI 输出结构**（`AIGenerateResult`）
- **需求分析** `requirement_analysis`：抽取的需求项（REQ-x，类型 functional/ui/data/integration）+ 每项**问题清单**（severity high/medium/low + 描述 + 建议）+ 总体评估。
- **功能用例** `functional_cases[]` 与 **接口用例** `api_cases[]`：title、case_type、priority(P0-P3)、domain、module、preconditions、steps(JSON)、expected_result、api_method/endpoint、remark、imported(是否已导入)。
- 导入结果：imported / skipped / total。
- 文档状态：uploaded；统计 imported_count / func / api。
**特色**：除生成用例外，AI 还会**反向评审需求**（指出需求文档自身的问题与建议）。
**现状与局限**：强依赖 DeepSeek（端点/Key 写死）；蓝湖提取路径硬编码；导入无事务（中途失败留半成品）；无生成历史版本对比。

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
**现状与局限**：无用例评审流、无版本历史/变更对比、无 Xmind/脑图编辑、无批量编辑、无回收站、无用例与需求的双向追溯。

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
**目标**：登记缺陷并关联用例/执行，外链至禅道/Jira。
**功能点**
| 操作 | 接口 |
|------|------|
| 缺陷统计 | `GET /defect/stats`（按 severity / status 分组） |
| 列表（分页+筛选） | `GET /defect` |
| 创建/详情/编辑/删除 | `GET/POST/PUT/DELETE /defect/{id}` |
- 字段：defect_id（自动编号）、title、description、severity(**P0/P1/P2/P3**)、status(默认 **open**)、case_id、execution_id、assignee、external_id、external_url、creator、resolved_at。
- 关联：可挂到具体用例与执行记录；可外链外部缺陷系统。
**现状与局限**：**无内建状态机工作流**（仅 open/resolved 雏形，无确认→修复→回归→关闭流转与校验）；无评论/附件/变更历史；与禅道/Jira 仅为「外链」非「双向同步」。

---

### 模块 11　API 测试 🧪（演示态）
**目标**：手动发起 HTTP 请求做接口验证。
**现状实现**
- **纯前端**：浏览器 `fetch(values.url)` 直接发起请求；请求历史存 **localStorage**（key `STORAGE_KEY`）。
- **无后端接口、无落库、无团队共享**；受浏览器跨域限制。
**局限/改进入口**：未用例化、不能纳入测试计划、无环境/变量/断言/前后置脚本/数据驱动，无法被定时任务或 CI 触发。→ 建议升级为**服务端 API 测试引擎**。

---

### 模块 12　UI 自动化 🧪（演示态）
**目标**：管理 UI 自动化任务并查看运行结果。
**功能点**
| 操作 | 接口 |
|------|------|
| 任务列表 | `GET /ui_test` |
| 创建/详情/编辑/删除 | `GET/POST/PUT/DELETE /ui_test/{id}` |
| 触发运行 | `POST /ui_test/{id}/trigger` |
| 运行历史 | `GET /ui_test/{id}/runs` |
- 字段：name、description、test_spec（Playwright 规范文本）、browser(chromium/firefox/webkit)、status(idle)；运行含 result、screenshots[]、video_url、trace_id。
**关键现状**：**运行结果为随机数模拟**（`ui_test_service.py:147` 用 `random.randint/uniform` 伪造 total/pass/duration），**未真实驱动 Playwright**。截图/视频/trace 字段为占位。
**改进入口**：对接真实 Playwright 执行器，产出真实结果与产物。

---

### 模块 13　音视频专项 🧪（演示态）
**目标**：对流地址做音视频质量检测。
**功能点**
| 操作 | 接口 |
|------|------|
| 任务列表 | `GET /av_check` |
| 创建/详情/删除 | `GET/POST/DELETE /av_check/{id}` |
| 触发检测 | `POST /av_check/{id}/trigger` |
| 指标明细 | `GET /av_check/{id}/metrics` |
- 字段：name、stream_url、protocol(**HLS/FLV/WebRTC/DASH**)、status(idle)、last_result。
- 指标：metric_name、metric_value、threshold、pass、detail（如「起播时延 ms/2000」「卡顿率 %/5」）。
**关键现状**：**检测指标为随机数模拟**（`av_check_service.py:130` `random.uniform` 伪造 value），**未真实拉流探测**。
**改进入口**：接入真实拉流/探测能力替换随机值。

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
| 缺陷状态 defect.status | open（→ resolved，工作流未完善） |
| 角色数据范围 data_scope | global / project / self |
| 权限点类型 permission.type | menu / button / api |
| 音视频协议 protocol | HLS / FLV / WebRTC / DASH |
| 浏览器 browser | chromium / firefox / webkit |
| 需求解析类型 parsed_type | requirement / test_cases |
| 需求项类型 | functional / ui / data / integration |

---

## 5. 现状总结与改进基线

### 5.1 已闭环的核心价值（建议「做深」而非推翻）
需求 →（AI 生成 + 需求反向评审）→ 用例库（域树）→ 测试计划 → 逐条执行（含 ELK 排障）→ 报告快照 / 缺陷登记 / 工作台看板，并由定时任务驱动周期化。RBAC + 多项目 + 审计构成企业级底座。

### 5.2 三类「演示态」功能（改进时优先决策：做真 or 降级标注）
- API 测试（纯前端）、UI 自动化（随机数）、音视频专项（随机数）——当前不具备真实测试能力，对外需明确标注，避免信任落差。

### 5.3 已知能力缺口（改进候选清单，来自各模块「现状与局限」）
1. 需求-用例-缺陷**追溯矩阵 / 需求覆盖率**（数据模型已具备，仅缺聚合视图）。
2. 缺陷**内建工作流**（状态机 + 流转记录 + 评论/附件）。
3. **消息通知**（执行完成 / 缺陷指派 / 定时失败 → 邮件/企业微信/钉钉/飞书）。
4. 报告**增强**（趋势、质量门禁、PDF/Excel 导出、模板）。
5. 用例**评审流 / 版本历史 / 脑图编辑 / Xmind 导入导出 / 批量操作**。
6. **CI/CD 集成**（Jenkins/GitHub Actions 触发与回写）。
7. **环境/变量管理**（供 API/UI 用例引用）。
8. 工程化：密钥外置、消除 N+1、补事务、补自动化测试、文档与代码对齐（README 仍写 Ant Design，实为 shadcn/ui）。

---

*配套文档：本目录另有《代码审查与产品重构PRD.md》（技术债 + 重构优先级 + 未来路线图）。本文聚焦「现在有什么」，可据「5.3」逐条拆分为改进需求 / issue。*
