---
title: "测试平台 v2 代码审查与产品重构 PRD"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["代码审查", "架构", "重构", "PRD", "技术债"]
related: ["test-platform-v2/docs/现状功能PRD.md", "test-platform-v2/docs/改进任务backlog.md", "test-platform-v2/docs/CamelTv测试平台-完整PRD.md"]
---

# CamelTv 测试平台 v2 —— 代码审查 + 架构提取 + 产品重构 PRD

> 文档类型：技术审查报告 + 架构基线 + 产品需求文档（PRD）
> 评审范围：`F:\CamelTv\test-platform-v2`（后端 FastAPI ~7.2k 行 / 前端 React+TS ~14.4k 行）
> 视角：资深架构师（可移植性/可复用性） + 资深产品经理（功能增删与重构）
> 日期：2026-06-22

---

# 第一部分　代码审查报告（可移植性 / 可复用性）

## 1.1 总体评价

| 维度 | 评分 | 结论 |
|------|------|------|
| 分层清晰度 | ★★★★☆ | 后端 api/service/model/schema/core 四层分明；前端 api/pages/components/stores 分层合理 |
| 技术栈现代性 | ★★★★★ | FastAPI + SQLAlchemy 2.0 + React 18 + shadcn/ui + Zustand + TanStack Table，均为当下主流 |
| 可复用性 | ★★☆☆☆ | **核心短板**：后端无 BaseService、前端无通用列表 Hook，CRUD 模式大面积复制粘贴 |
| 可移植性 | ★★☆☆☆ | **核心短板**：密钥/路径/业务常量硬编码，外部系统（AI/ELK/蓝湖）强耦合不可插拔 |
| 安全性 | ★★☆☆☆ | **存在 P0 级泄露**：真实 LLM API Key 明文入库 |
| 工程化 | ★★☆☆☆ | 0 自动化测试、文档与代码脱节、无 CI 质量门禁 |

一句话：**这是一套"架构骨架优秀、复用抽象缺失、关键功能尚为演示态"的早期平台**。骨架值得保留，需在其上补三件事——抽象复用层、外部依赖可插拔、把"假功能"做成"真功能"。

---

## 1.2 🔴 P0 必须立即处理（安全 / 数据正确性）

### P0-1　真实 LLM API Key 明文硬编码（安全事故）
`backend/app/core/config.py:30`
```python
ai_api_key: str = "sk-17abf5e3018b44f7b755caa1d390ae20"   # ❌ 真实 DeepSeek 密钥写死在源码默认值
secret_key: str = "dev-secret-change-me"                  # ❌ JWT 签名默认弱密钥
admin_password: str = "admin123"                          # ❌ 默认管理员口令入库
```
**风险**：源码一旦外泄即密钥泄露、可伪造任意 JWT。
**整改**：敏感项默认值置空，启动时校验"生产环境必填"；立即吊销并轮换该 DeepSeek Key；密钥统一走环境变量 / Secret 管理。

### P0-2　N+1 查询（列表性能随数据量线性劣化）
`defect_service.py`、`av_check_service.py:63-69`、`ui_test_service.py:63-69`、`test_plan_service.py:290-292` 均在循环内 `db.get(User, ...)` 逐条查询。
**对照正确写法**：`requirement_service.py:74-89` 已用 `in_()` 批量取 user_map——应推广为统一工具。

### P0-3　缺事务原子性
`requirement_service.import_cases()`（`requirement_service.py:198-272`）循环逐条创建用例、无事务包裹，中途失败将留下半成品数据。
**整改**：提供 `@transactional` / `with db.begin()` 上下文，导入类批量操作整体提交或整体回滚。

---

## 1.3 🟠 P1 可移植性问题（硬编码 / 强耦合）

| 位置 | 硬编码内容 | 影响 | 建议 |
|------|-----------|------|------|
| `ai_service.py:14-16` | 蓝湖技能目录 `.claude/skills/...` 绝对路径推算 | 换机/换部署即失效 | 路径走配置；技能内容内聚到后端 |
| `config.py:29` | DeepSeek 端点 + 模型写死 | 无法切换 LLM 供应商 | 抽象 `AIProvider` 接口 |
| `elk_service.py:10-22` | Kibana 链接格式写死 | 换日志系统即重写 | 抽象 `LogProvider` 接口 |
| `test_case_service.py:142` | 域排序 `{"用户端":0,"运营后台":1}` | 业务术语写进代码 | 配置化 / 字典表 |
| `av_check_service.py:122` | 指标定义 `("起播时延","ms",2000)` | 指标不可配 | 指标元数据落库 |
| 前端各页面 | 优先级色/状态标签/Badge 类（≥5 处重复） | 改一处需改五处 | 统一 `lib/constants.ts` |

**外部耦合可插拔性**：AI、ELK、蓝湖三处目前为"硬连线"，均应抽象为 Provider 接口 + 工厂，方便替换与本地 mock。

---

## 1.4 🟡 P1 可复用性问题（重复代码）

### 后端：缺 BaseService / 分页器（重复 ~200 行）
8 个 service 各写一套"`select → 逐条 where → count → offset/limit → _to_dict`"。建议抽取：
```python
class BaseService:
    model = None
    def list_paginated(self, db, *, project_id, filters, page, page_size) -> tuple[list, int]: ...
    def get_or_404(self, db, id, project_id): ...
    def soft_delete(self, db, id): ...

def paginate(query, page, page_size) -> tuple[list, int]: ...
```
另：每个 service 手写 `_to_dict()`（`test_case_service.py:161`、`defect_service.py:26` 等）——应改用 Pydantic `from_attributes=True` 直接由 ORM 映射，消除"ORM→dict→Schema"三重转换。

### 后端：基类缺软删除 / 审计 / 统一时区
`models/base.py` 仅有 `TimestampMixin`。问题：软删除靠各表 `status=0` 散落实现、查询易漏过滤；时区不统一（`user.py` 用 `datetime.now()` 本地，`defect.py` 用 UTC）。建议补 `SoftDeleteMixin`、`AuditMixin`，全库统一 UTC。

### 前端：无通用列表 Hook（CRUD 重复率 > 60%）
testcase/testplan/report/defect/uitest/schedule 每页都复刻"分页 state + load() + 筛选 + 表格 + 删除确认框"。建议抽取：
```ts
const { data, loading, query, setFilters, reload, pagination } =
  usePaginatedList((page, filters) => api.list(page, filters), { pageSize: 20 })
```
并封装 `<CrudPage>` / `<CrudDrawer>` 壳组件。**强烈建议引入 TanStack Query** 统一缓存——当前各页 useState 孤岛，用例改动后计划/报告页无法感知。

### 前端：类型与一致性债
- 105 处 `as any`，根因是 API 返回时而数组、时而 `{items}`，应统一响应契约。
- 无 `ErrorBoundary`，子组件报错即整页白屏。
- 6 个 >500 行巨型组件（`requirement/index.tsx` 736、`AiResultModal.tsx` 832）应拆分。

---

## 1.5 重构优先级总表

| 级别 | 后端 | 前端 |
|------|------|------|
| **P0** | 移除硬编码密钥、修复 N+1、补事务 | 引入 ErrorBoundary、统一响应契约消除 `as any` |
| **P1** | 抽 BaseService/分页器、Pydantic 直映、软删除/审计 Mixin、统一 UTC | 抽 `usePaginatedList`、`lib/constants.ts`、引入 TanStack Query |
| **P2** | AI/ELK/蓝湖 Provider 化、权限缓存、补单测 | 拆巨型组件、列表虚拟化、i18n、补测试 |

---

# 第二部分　架构与核心流程提取

## 2.1 系统全景

```
┌─────────────── 前端 (Vite SPA, /api/v1 代理) ───────────────┐
│ React18 + TS + shadcn/ui + Zustand + TanStack Table + Recharts │
│ api/(axios封装) · pages/(13业务页) · components/ui(30+原子)     │
│ stores/auth · router(懒加载+守卫) · layouts/MainLayout(动态菜单)│
└──────────────────────────┬─────────────────────────────────┘
                           │ JWT(Bearer) + X-Project-Id  统一响应 {code,msg,data}
┌──────────────────────────┴─────────────────────────────────┐
│ 后端 FastAPI                                                  │
│  api/v1(路由+鉴权) → services(业务,纯函数) → models(ORM2.0)   │
│  schemas(Pydantic) · core(config/db/deps/security/exc/sched) │
│  外部：DeepSeek LLM · ELK/Kibana · 蓝湖/Axure · APScheduler   │
└──────────────────────────┬─────────────────────────────────┘
                           │ SQLAlchemy
                  SQLite(WAL，可升 PostgreSQL)
```

**技术栈实况**（README 已过时，称 Ant Design 5，**实为 shadcn/ui**）：

| 层 | 实际技术 |
|----|---------|
| 后端 | FastAPI 0.110+ · SQLAlchemy 2.0 · Pydantic v2 · Alembic · APScheduler · JWT+bcrypt |
| DB | SQLite(WAL) 默认，`database_url` 可切 PostgreSQL |
| 前端 | React 18.3 · TS 5.6 · React Router 6 · Zustand 4(持久化) · shadcn/ui(Radix+Tailwind) · TanStack Table 8 · Recharts · react-hook-form+zod · axios · sonner |

## 2.2 核心横切机制

1. **鉴权链**（`core/deps.py`）：`HTTPBearer → decode_token → get User → rbac.permission_codes(user, X-Project-Id) → CurrentUser{user, permissions, project_id}`。
2. **多项目隔离**：请求头 `X-Project-Id` 贯穿全程；`require_project` 校验成员身份（超管 `*` 放行）；service 普遍以 `project_id` 入参做数据隔离。
3. **RBAC**（`models/rbac.py`）：User—Role—Permission 多对多；角色含数据范围 `global/project/self`；权限点 `type ∈ {menu,button,api}`（**菜单与权限混表，建议拆分**）；权限工厂 `require_permission('case:list')`。
4. **统一响应/异常**（`core/exceptions.py`）：全局 `{code,msg,data}`；`APIException(code,msg,http_status)`。注意业务码与 HTTP 码语义混用（默认 `http_status=200`），建议规整。
5. **会话/事务**（`core/db.py`）：每请求一 Session，`finally` 关闭；事务边界靠 service 内显式 `commit/flush`，**缺统一事务装饰器**。
6. **前端拦截器**（`api/client.ts`）：请求注入 `Authorization`+`X-Project-Id`；响应拆 envelope、`code!==0` toast 报错、`401` 自动登出跳转。

## 2.3 关键业务流程：质量闭环主链路

```
登录(JWT+项目选择)
   ▼
需求文档上传(MD/Word/Excel/蓝湖) ──AI生成──▶ 用例预览(AiResultModal) ──导入──▶ 用例库(域/模块树)
                                                                                   ▼
                                                            测试计划(关联用例) ──执行──▶ 执行记录(状态+ELK traceId)
                                                                                   ▼
                                              ┌──────────────────┬──────────────────┐
                                              ▼                  ▼                  ▼
                                          测试报告(JSON快照)   缺陷(关联执行/用例)   工作台看板(统计/图表)
                                              ▲                                      ▲
                                          定时任务(APScheduler cron) ───触发执行/生成报告───┘
```
该主链路（需求→用例→计划→执行→报告/缺陷）是平台**已跑通的核心价值**，也是后续所有增强的主干。

## 2.4 模块成熟度矩阵（真功能 vs 演示外壳）★关键

| 模块 | 后端 service | 前端页 | 成熟度 | 证据 |
|------|------|------|--------|------|
| 登录/RBAC/审计 | auth/rbac/user/role/menu/audit | login/system | ✅ 真实 | JWT+bcrypt 完整 |
| 项目管理 | project | project | ✅ 真实 | 成员/隔离完整 |
| 需求+AI生成 | requirement/ai/file_parser | requirement | ✅ 真实(依赖外部LLM) | 真调 DeepSeek |
| 用例管理 | test_case | testcase | ✅ 真实 | 域树+CRUD |
| 测试计划/执行 | test_plan | testplan | ✅ 真实 | 执行记录闭环 |
| 测试报告 | report | report | ✅ 真实 | JSON 快照 |
| 定时任务 | schedule | schedule | ✅ 真实 | APScheduler |
| 缺陷管理 | defect | defect | 🟡 半真 | 仅外链禅道/Jira，无内建工作流 |
| 工作台看板 | dashboard | workbench | 🟡 半真 | 统计真，维度有限 |
| **音视频专项** | av_check | special | ❌ **模拟** | `av_check_service.py:130` 指标 `random.uniform` 伪造 |
| **UI 自动化** | ui_test | uitest | ❌ **模拟** | `ui_test_service.py:147` 结果 `random.randint` 伪造 |
| **API 测试** | （无） | apitest | ❌ **纯前端** | 浏览器 `fetch`+localStorage，无服务端执行/无落库 |

> **结论**：三个"自动化测试"模块目前是 UI 外壳 + 随机数/本地存储，不具备真实测试能力。这是产品侧最大的认知落差，也是 PRD 的重点。

---

# 第三部分　产品重构 PRD（资深产品经理视角）

## 3.1 产品定位与判断

CamelTv 测试平台 v2 想做的是**「需求→用例→计划→执行→缺陷→报告」的一体化测试管理 + 测试执行平台**，对标 MeterSphere / TestOps / 禅道测试模块。

当前阶段定位应明确为：**测试"管理"平台已成型，测试"执行"平台尚未落地**。
产品决策的主线只有一句话：**先把已跑通的管理闭环做深做透，再把三个演示态执行模块逐个做成真实引擎；不要横向再铺新模块。**

## 3.2 现状诊断（产品视角）

**已具备的产品价值（保住）**
- AI 读需求自动生成用例——差异化亮点，是获客锚点。
- 多项目 + RBAC + 审计——具备团队/企业级底座。
- 需求→用例→计划→报告主链路打通——核心管理价值成立。

**最大的产品风险（三类"假功能"）**
- 音视频专项、UI 自动化、API 测试——演示能跑、生产不可用。若对外宣称具备，会形成信任崩塌。**短期必须明确标注"Beta/演示"，中期做成真引擎或下线。**

**体验与信任债**
- 缺陷只能外链，无法在平台内形成"提单→流转→回归→关闭"闭环。
- 报告仅单计划 JSON 快照，无趋势、无质量门禁、无导出。
- 无任何通知触达（执行完成 / 缺陷指派 / 定时失败均无感）。
- 无追溯矩阵——需求覆盖率、用例-缺陷关联无法回答"这个需求测全了吗"。

## 3.3 功能路线决策表（增 / 删 / 改）

| 决策 | 模块 | 理由 |
|------|------|------|
| 🟢 **做深** | 用例管理、测试计划、报告中心、缺陷管理 | 主链路价值核心，ROI 最高 |
| 🟢 **新增** | 追溯矩阵、消息通知、真实 API 测试引擎、CI/CD 集成 | 补齐"管理→执行→反馈"缺口 |
| 🟠 **做真 or 降级** | UI 自动化、音视频专项 | 现为随机数模拟，要么接真引擎，要么标注 Beta 收窄预期 |
| 🟠 **升级** | API 测试 | 从前端工具升级为服务端用例化执行引擎 |
| 🔴 **暂缓/砍** | 同时铺更多专项 | 在三个执行模块做真之前，不再横向扩张 |

## 3.4 产品需求清单（按优先级 MoSCoW）

### Must（V2.2，1–2 月，补齐管理闭环可信度）

| ID | 需求 | 价值 | 关联代码 |
|----|------|------|---------|
| M1 | **需求-用例-缺陷追溯矩阵**：以需求为行、覆盖用例数/通过率/关联缺陷为列，输出"需求覆盖率" | 回答"测全没"，测试经理核心诉求 | 新增，复用 requirement/test_case/defect |
| M2 | **缺陷内建工作流**：状态机(新建→确认→修复→回归→关闭/拒绝)+指派+流转记录，保留外链同步 | 把缺陷闭环收回平台 | 增强 `defect` |
| M3 | **消息通知中心**：执行完成/缺陷指派/定时失败 → 邮件+企业微信/钉钉/飞书 Webhook | 让平台"会说话"，提升日活 | 新增 notify_service |
| M4 | **报告增强**：多计划趋势、通过率/缺陷收敛曲线、PDF/Excel 导出、可配模板 | 报告能对上汇报 | 增强 `report` |
| M5 | **安全整改**：密钥外置、默认口令强制改、操作二次确认 | P0 安全债 | `config.py` |

### Should（V2.3，3–4 月，把"假执行"做成"真执行")

| ID | 需求 | 价值 |
|----|------|------|
| S1 | **真实 API 测试引擎**：服务端执行，支持环境/变量/前后置脚本/断言/数据驱动，用例落库并入计划 | 把演示工具变生产能力 |
| S2 | **CI/CD 集成**：Jenkins/GitHub Actions Webhook 触发计划、回写结果、生成报告 | 接入研发流水线，黏性最强 |
| S3 | **UI 自动化做真**：对接 Playwright 真实执行（去掉 `random`），产出真实截图/视频/trace | 兑现"自动化"承诺 |
| S4 | **测试环境/配置管理**：dev/test/staging 环境集中管理，被 API/UI 用例引用 | 多环境必备底座 |
| S5 | **Xmind/Excel 用例双向导入导出 + 脑图编辑用例** | 国内测试团队强习惯 |

### Could（V3.0，规划，平台化/企业级）

| ID | 需求 |
|----|------|
| C1 | 用例评审流（提交→评审→驳回→归档）+ 用例版本历史/变更对比 |
| C2 | 音视频专项做真：接入真实拉流探测（起播时延/卡顿率/首帧）替换随机数 |
| C3 | 性能测试模块（JMeter/k6 集成） |
| C4 | 个人/团队质量度量看板（缺陷密度、用例执行效率、千行缺陷率） |
| C5 | SSO/LDAP/OAuth 单点登录、开放 API + Webhook 生态 |
| C6 | i18n 国际化、数据看板大屏 |
| C7 | 测试数据管理（mock 数据池、脱敏、造数） |

## 3.5 重点新功能详述（Top 3）

**① 追溯矩阵（M1）——测试经理的"驾驶舱"**
- 入口：需求详情页 + 独立"质量追溯"页。
- 视图：需求 × {关联用例数, 已执行, 通过, 失败, 阻塞, 关联缺陷, 覆盖率%}。
- 价值：一屏回答"需求是否被测试覆盖、质量风险在哪"，是管理类平台的灵魂功能，且**当前数据模型已具备**（requirement/test_case/test_plan/defect 齐全），仅缺聚合查询与可视化，性价比最高。

**② 真实 API 测试引擎（S1）——把工具做成能力**
- 现状：`apitest` 纯前端 fetch + localStorage，刷新即依赖浏览器、跨域受限、不可团队协作、无法纳入计划。
- 目标：服务端执行器（用例落库）→ 环境/全局变量 → 前置/后置脚本 → 断言（状态码/JSONPath/正则/响应时间）→ 数据驱动 → 可被测试计划编排、可被定时任务/CI 触发。
- 价值：与"需求→用例→计划"主链路打通，自动化用例与手工用例统一管理。

**③ 通知中心（M3）——让平台产生"拉力"**
- 触发：执行完成、缺陷指派/状态变更、定时任务失败、报告生成。
- 渠道：邮件 + 企业微信/钉钉/飞书机器人（Webhook 优先，落地快）。
- 价值：测试平台没有通知就只是"被动数据库"；有了通知才进入团队日常工作流，是日活/留存的关键杠杆。

## 3.6 非功能需求（NFR）

| 类别 | 要求 |
|------|------|
| 安全 | 密钥全部外置；JWT 强密钥；默认口令强制初始化修改；审计覆盖关键写操作 |
| 性能 | 列表统一分页+索引，消除 N+1；大列表虚拟滚动；权限码缓存 |
| 可靠 | 批量/导入操作事务原子化；定时任务失败重试+告警 |
| 可维护 | 后端 BaseService/Provider 抽象、前端 usePaginatedList/常量库；关键路径单测覆盖 |
| 可移植 | AI/ELK/蓝湖 Provider 化，支持本地 mock；SQLite↔PostgreSQL 平滑切换 |
| 可观测 | 前端 ErrorBoundary + 错误上报；后端结构化日志 + traceId 贯通 |

## 3.7 分期路线图

```
V2.2 (1–2月) 信任补齐   ：追溯矩阵 · 缺陷工作流 · 通知中心 · 报告增强 · 安全整改
V2.3 (3–4月) 执行做真   ：真实API引擎 · CI/CD集成 · UI自动化接Playwright · 环境管理 · Xmind导入
V3.0 (季度+) 平台化     ：用例评审/版本 · 音视频做真 · 性能测试 · 质量度量 · SSO/开放API · i18n
并行(贯穿)   技术健康度 ：BaseService/Hook抽象 · Provider化 · 测试覆盖 · 文档与代码对齐
```

## 3.8 给决策者的一页纸结论

1. **保**：AI 生成用例 + 需求→用例→计划→报告主链路 + RBAC 多项目底座——这是你的护城河。
2. **修**：先堵 P0 安全与 N+1/事务，再补复用抽象（后端 BaseService、前端列表 Hook + TanStack Query）。
3. **真**：音视频、UI 自动化、API 测试是三个演示外壳——短期标注 Beta，中期逐个接真引擎，否则是信任地雷。
4. **增**：追溯矩阵、通知、缺陷工作流、CI/CD ——四件让平台从"数据库"变"团队工作台"的关键拼图。
5. **不做**：在三个执行模块做真之前，不再横向铺新专项模块。

---

*附：本文所有结论均可在源码中验证，关键引用已标注 `文件:行号`。建议将本文纳入仓库 `docs/` 作为重构基线，并据「3.4 需求清单」逐条拆分为 issue 跟踪。*
