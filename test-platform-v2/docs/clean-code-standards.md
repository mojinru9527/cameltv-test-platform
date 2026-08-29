---
title: "测试平台 Clean Code 代码规范（适配版）"
owner: "qa-team"
last_reviewed: "2026-08-07"
status: "active"
expires: "2027-01-07"
tags: ["clean-code", "engineering", "frontend", "backend", "standards", "code-quality"]
related: ["../../docs/engineering-standards.md", "../CLAUDE.md", "../backend/CLAUDE.md", "../frontend/CLAUDE.md", "../../docs/testing-strategy.md", "../../docs/common-pitfalls.md"]
---

# 测试平台 Clean Code 代码规范（适配版）

> 本文档以 **Robert C. Martin（Uncle Bob）《Clean Code》** 的工程思想为骨架，参考 **GitHub 主流测试平台开源项目** 的前后端写法，并结合 **CamelTv 测试平台 v2** 的实际分层/工具链约定，形成一套「可直接执行、可被评审、可写进自检清单」的代码规范。
>
> **适用范围**：`test-platform-v2/backend/`（Python · FastAPI）与 `test-platform-v2/frontend/`（TypeScript · React）。
> **约束等级**：`[强制]` = 违反即 Block PR；`[建议]` = 评审建议；`[原则]` = 哲学指导思想，落地为具体条目。
> **可执行化**：本文档每条强制/建议条目已转成 [Gherkin 验收套件](../../tests/clean-code/README.md)，可作评审清单或自动化门禁基线。

---

## 1. 指导思想：为什么用 Clean Code 思维写测试平台

Uncle Bob 在《Clean Code》开篇的论断是：**代码是给人读的，只是在机器上运行**。「整洁代码」不是语法糖，而是一种降低变更成本的工程策略。

对 **测试平台** 这类系统，Clean Code 比一般业务系统更重要：

1. **平台本身也是测试对象**。测试平台是「测试能力」的载体，若平台代码又臭又长，就失去「质量标杆」的说服力——自测不过关，何谈测试别人。
2. **AI 生成代码占比高**。本平台大量用例/需求由 LLM 生成（见 `services/ai_service.py`、`services/case_generation_service.py`），生成的代码若不合规会污染整个交付物；所以规范必须做到「可被 AI 执行」的确定性（见 §7）。
3. **前后端长期并行演进**。FastAPI + React 两端由不同角色维护，契约靠 REST API 绑定；命名、分层、错误处理不统一，跨端排障成本指数上升。
4. **CI 已有硬门禁**（ruff F821、tsc、vitest、pytest）。Clean Code 规范要**落在这些已知门禁上**，而不是另起无关道德条款。

### 1.1 三条铁律（源自《Clean Code》第 1 章）

| 铁律 | 含义 | 落地到本平台 |
|------|------|--------------|
| **童子军规则** | 每次提交让代码比来时更干净 | 任何改动顺手清理见到的坏味道；修 bug 时顺手拆掉超长函数 |
| **技术债要记账** | 坏味道不是「历史问题」，是可偿还的债务 | 已知坏味道写入 `docs/engineering-standards.md` 或 PR 描述，明确「本期不还、何时还」 |
| **不做「假整洁」** | 变量名藏意图、注释复述代码，都是伪装 | 拒绝「定义变量」「调用函数」类注释（已在本仓库 `docs/engineering-standards.md` §1 强制） |

> **本平台已有支撑**：`docs/engineering-standards.md` 与 `AGENTS.md` §3 已经把「用途注释、无调试遗留、无硬编码密钥」定为强制项。本文档与它们是**互补**关系——那里是「交付红线」，这里是「怎么写好」。

---

## 2. 参考的 GitHub 测试平台（前后端写法基线）

以下选型的标准：**开源测试平台 + 前后端分离 + 与本文档目标能力相近（用例/计划/执行/报告/缺陷/自动化）**。我们「对标其分层与命名」，而非照搬其技术栈。

| 参考仓库 | 定位 | 前后端栈 | 我们借鉴的点 |
|---------|------|---------|-------------|
| [MeterSphere / metersphere](https://github.com/metersphere/metersphere) | 一站式开源持续测试平台（用例/接口/UI 测试/报告/缺陷） | 前端 Vue，后端 Java Spring Boot | 模块边界清晰（用例库 / 测试计划 / 接口测试 / UI 测试 / 报告中心各自成域）；「资源 + 回收站软删」语义 |
| [QAMangementSystem](https://github.com/Pythagora-io/QAMangementSystem) | QA 管理平台（需求 → 用例 → 计划 → 报告） | 前端，后端（TypeScript/Node 栈） | 面向「QA 人员」的信息结构（页面按角色工作流组织），前端目录按功能域分 `views/api/components/hooks` |
| [Tectonic-TCMS](https://github.com/PaulNasc/Tectonic-TCMS) | 测试用例管理与执行周期管理 | 前端 Web，后端 | 用例-执行周期（cycles）的实体建模，状态机用独立词表而非魔法字符串 |
| [autotest-platform](https://github.com/seven-017/autotest-platform) | 接口/UI 自动化测试平台 | Python 后端 + Web 前端 | 接口用例用「环境 + 变量」解耦，把凭据从脚本里剥离（与本平台 `environment`/`dataset` 理念一致） |
| [Autotest_platform (POM)](https://github.com/shaonianyr/Autotest_platform) | 基于 POM 模式的 Web UI 自动化平台 | Python 后端 + 前端 | 用 POM 把「页面定位」与「业务动作」分层，稳定命名页面对象 |

> **对标结论**：一流测试平台几乎都遵循——**资源与回收站分离、执行状态词表统一、环境/数据与脚本分离、前端按功能域分目录且页面薄**。这些正是本平台 `backend/CLAUDE.md`（状态词表、删除语义、环境隔离）与 `frontend/CLAUDE.md`（功能域分目录）已经定下的方向，本文档使其与 Clean Code 原则显式对齐。

---

## 3. 命名规范（《Clean Code》第 2 章）

> 原则：**名字要自解释目的，而不是藏起目的。** 好的命名让注释变得多余。

### 3.1 通用（前后端一致）

- **[强制] 用「意图命名」不用「类型命名」**。不用 `data`、`obj`、`temp`、`list1`、`val`。
  - ❌ `d = get_data(id)`
  - ✅ `case_detail = fetch_case_detail(case_id)`
- **[强制] 布尔前缀统一：`is_` / `has_` / `can_` / `should_`**。
  - `is_deleted`（本仓库软删约定）、`can_run`、`has_asserts`。
- **[强制] 避免双关语与误导性缩写**。`front` 可能指前端、可能指前台；同一概念全仓库只用一个词（见 §3.4 术语表）。
- **[建议] 类名用名词/名词短语，函数/方法用动词开头**。
  - 后端 `TestCaseService`（名词），`create_case`（动词）。
  - 前端 `CaseTable`（名词），`handleSave`（动词）。

### 3.2 后端（Python）

- **[强制] 遵循 PEP 8**：模块/函数/变量 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE_CASE`。
- **[强制] 函数名「动词 + 对象」**：`fetch_case_by_id`、`build_execution_payload`、`list_paginated`。禁止 `do_it`、`process`、`handle_data` 这类无信息量动词。
- **[建议] 路由处理函数直接以 HTTP 动作 + 资源命名**，与 `backend/CLAUDE.md` 的 URL 风格 `/api/v1/{resource}` 对齐：
  - `GET /api/v1/test-cases` → `list_test_cases`；`POST /api/v1/test-cases` → `create_test_case`。
- **[强制] 布尔列/字段保留规范名**：`is_deleted`、`is_active`、`last_status`、`locked_by`/`locked_at`（对齐 `backend/CLAUDE.md` 删除与队列约定）。

### 3.3 前端（TypeScript）

- **[强制] 遵循仓库 TS 约定**：文件名 `kebab-case`（`CaseFilterBar.tsx`），React 组件 `PascalCase`，hooks `useXxx`，工具函数 `camelCase`。
- **[强制] 组件命名表意**：`CaseTable`、`DefectFilterBar`、`RequirementStatsRow`。禁止 `Page1`、`Widget`、`Container`。
- **[建议] props/state 全部显式类型化**，用 `src/types/` 里的生成类型（`npm run gen:api`），**禁止 `any` 当成万能逃生舱**（`client.ts` 中 `detail.map((d: any)` 是反例，仅在边界处容忍并加注释说明）。
- **[强制] 接口函数名与后端对应**（`frontend/CLAUDE.md` 约定）：`fetchTestCases` / `createTestCase`，资源词与后端一致。

### 3.4 术语表（一次命名，处处复用）

> 在测试平台领域，「用例 / 计划 / 执行 / 报告」是高频词。定义唯一术语，避免同义词混用。

| 术语 | 唯一含义 | 对应对象（示例） |
|------|---------|-----------------|
| 用例 | `test_case` | `TestCase` / `testcase.ts` |
| 测试计划 | `test_plan` | `TestPlan` / `testplan.ts` |
| 执行 | `execution`（运行实例） | `TestPlanExecution` / `execution_status.ts` |
| 报告 | `report` | `Report` / `report.ts` |
| 缺陷 | `defect` | `Defect` / `defect.ts` |
| 需求 | `requirement` | `Requirement` / `requirement.ts` |
| 环境 | `environment` | `Environment` / `environment.ts` |

> 命名演进时（如从 `case` 迁到 `test_case`）**不要留下新旧混用**；同一个实体只能有一个主名，别名仅在边界（如对外 API）处映射。

---

## 4. 函数规范（《Clean Code》第 3 章）

> 原则：**函数要小、要做一件事、只做一件事、使用抽象层级（SLAP）。**

### 4.1 后端

- **[强制] 单个函数尽量 ≤ 30 行，超过就要问「它在做几件事」**。长函数是拆分的候选，不是让它继续长下去的理由。
- **[强制] 单一职责（SRP）落地到函数**：一个函数只做「渲染响应」「组装查询」「编排流程」之一，不混用。
  - 反例：一个路由函数既查库、又拼 SQL、又算统计、又组装响应。
  - 正例（本仓库 `core/base_service.py`）：`paginate` 只做分页、`batch_user_names` 只做批量取用户名——全是「纯函数 + 显式 session」，彼此可测。
- **[建议] 使用抽象层级**：函数体内部只使用同一层级的概念。
  - 顶层函数调用 `fetch_case` / `build_tree` / `persist`（高层）；底层函数处理 `select(...).where(...)`（低层）。不要在高层函数里写原生 SQL。
- **[强制] 副作用收敛**：路由层**只做参数校验、权限、调用 Service、组装响应、`db.commit()`**（`backend/CLAUDE.md` 路由禁 ORM 的强制项即本原则的落地）。
- **[建议] 用上下文管理器封装事务**：`with transaction(db):`（`core/base_service.py`），在异常时统一 rollback，避免手写 try/except 漏掉 commit。
- **[强制] 禁止魔法数字**：`page_size=20`、超时 30 分钟、保留期 7 天等提到常量或 `settings`（对齐 `core/config.py`）。
- **[建议] 优先返回可判定的领域对象，不用裸 `True/False`、`None`、魔法字符串表示业务语义**。用 `core/exceptions.py` 的异常（`not_found`/`forbidden`）表达明确业务分支。

### 4.2 前端

- **[强制] 组件函数保持「薄」**：页面组件是「数据 + 渲染」装配层；复杂逻辑拆到 hooks（`hooks/`）或纯工具函数（`utils/`、`lib/`）。
  - 本平台 `hooks/useApi.ts`、`hooks/usePaginatedList.ts`、`hooks/useDebouncedValue.ts` 正是把人肉处理 loading/error/abort/debounce 的逻辑从组件抽出来的正确示范。
- **[强制] 不在组件内写复杂编排**。一个 300 行、内含 5 个 useEffect 的组件，应拆为子组件 + 自定义 hook + 纯函数。
- **[建议] 纯函数与副作用分离**：把状态迁移（如 `uiRunResult.ts`、`executionStatus.ts`、`caseListFormatters.ts`）写成可单测的纯函数；副作用（fetch/订阅）交给 `useApi`/`useAbortableEffect`。
- **[建议] avoid 巨型条件（长长的 if/else 或平铺 schema）**，用跳表/映射对象（本仓库 `KnowledgeStatus`、`executionStatus` 双值映射就是好例子）。

---

## 5. 错误处理（《Clean Code》第 7 章）

> 原则：**错误处理也是程序的一部分，别让它污染主流程。用异常代替返回码来传递失败。**

### 5.1 后端

- **[强制] 使用统一异常体系**：业务错误抛 `APIException`（`core/exceptions.py`），由全局处理器统一转 `{code, msg, data}`（`main.py`）。
  - 不要在路由里 `return {"code": 1, "msg": "..."}` 到处拼响应；那是把异常降级成散落的 return。
- **[强制] 让调用方用「显式异常」表达预期业务失败**：
  - `not_found()`、`forbidden()`、`unauthorized()`（`core/exceptions.py` 已提供）。
  - 外部/历史状态经 `canonical_exec_status()` 规范化（`core/execution_status.py`），不把脏值直接落库。
- **[建议] 区分「预期业务错误」与「异常」**：预期失败用领域异常（`AIProviderUnconfiguredError` 等），系统异常只在边界捕获、记日志，不吞掉。
- **[强制] 禁止裸 `except Exception: pass`**。即使要兜底，也要注释「为什么容忍、失败后的行为」。全仓 `pytest` 失败集合必须在 PR 中说明（`AGENTS.md` §3.1）。

### 5.2 前端

- **[强制] Axios 统一拆 envelope 与错误处理**（详见 `src/api/client.ts`）：
  - 成功解包 `data`；`code !== 0` 抛业务 `Error`（附带 `.code/.data`，供调用方识别 404 等场景）。
  - 401 统一登出 + 清缓存 + 跳转；其余 `toast.error`。
- **[强制] 组件层已知错误先本地呈现**：调用方在 `onError` 回调用内联 UI 提示（`useApi.ts` 的 `onError`），不要让每个页面都重复打 toast。
- **[强制] 处理 AbortError**：路由切换/请求被取消不是用户可见失败，`client.ts` 与 `useApi.ts` 已对 `ERR_CANCELED` / `AbortError` 单独放行，不 toast。
- **[建议] 用 `ErrorBoundary` 兜 UI 崩溃**（`components/ErrorBoundary.tsx` 已存在），避免一处在渲染期抛错导致整页白屏。

---

## 6. 分层与依赖方向（SOLID / SRP + DIP）

> 原则：**让依赖指向抽象与稳定方向，而非具体与易变方向。**

### 6.1 后端

```
Router (api/v1/)  →  Service (services/)  →  Model (models/)
       ↓                     ↓
   Deps (core/deps.py)   BaseService 纯函数 (core/base_service.py)
```

- **[强制] 分层单向依赖**：Router 不触 ORM（`backend/CLAUDE.md` 强制）；Service 承载业务；Model 只描述结构；Schema 与请求/响应分离。
- **[建议] Service 之间通过接口协作而非互相透传裸 session**；跨域协作（如用例→执行）用显式 service 方法，不写内联 SQL。
- **[强制] 新队列认领必须走 `core/task_queue.py` 原语**（`QueueSpec` + `atomic_claim*`），禁止自研 `SELECT→改→commit`（TOCTOU，`backend/CLAUDE.md` 强制）。这是 DIP「复用稳定的抽象」的直接案例。
- **[建议] 相对稳定的抽象放 `core/`**（`config`, `db`, `deps`, `exceptions`, `task_queue`, `base_service`），易变业务放 `services/`。

### 6.2 前端

```
pages/  →  hooks/  →  api/  →  client.ts
   └── components/（shadcn/ui + 业务组件）
stores/ 只存状态，不调 API（frontend/CLAUDE.md 约定）
```

- **[强制] 依赖单向**：页面 → hooks → api；Store 只存状态不做 API（`frontend/CLAUDE.md`）。页面不直接 `fetch`，统一走 `api/` 层。
- **[建议] 可复用逻辑抽 hooks**：数据拉取用 `useApi`/`usePaginatedList`；可取消副作用用 `useAbortableEffect`；避免每个页面手写一遍 abort/loading/error。
- **[强制] 组件边界让 shadcn/ui 承担通用底座**，业务组件只做「领域装配」，不重复造 Button/Dialog 等（`components/ui/` 34 个组件即为共享底座）。

---

## 7. 与 AI 生成代码的适配（本平台独有）

> 本平台大量代码由 LLM/DSH Agent 生成（用例生成、需求拆解、API case 生成）。Clean Code 需要 **adapt 成机器可执行的确定性检查**，否则规范形同虚设。

- **[强制] 自动生成代码落地前跑硬门禁**：后端 `ruff check app/ --select F821`，前端 `npm run typecheck && npm run build`（`AGENTS.md` §3.1）。生成代码也必须通过。
- **[强制] 生成代码必须补齐用途注释**（`docs/engineering-standards.md` §1「自动生成代码也必须补齐用途注释后才能交付」）。
- **[强制] 生成代码禁止硬编码凭据/环境值**：账号、Token、API Key、`X-Project-Id` 等一律走 env / `core/config.py` / `environment`/`dataset` 模块注入。
- **[建议] 用「版本化 persona」约束生成**：`services/dsh/tester_team_persona.py`、`agent_team_persona.py` 中把本文档要点（命名、分层、禁 ORM、状态词表）写进提示词，让生成型 Agent 产出一致风格。
- **[强制] AI 生成的断言/测试同样适用本规范**（`docs/engineering-standards.md` §2 自动化测试注释要求）。
- **[建议] 三桶过滤**：AI 生成 → 人工/评审 Review → CI/Chat 检查；评审不是可选项。

---

## 8. 测试与代码质量（《Clean Code》第 9 章：TDD / FIRST）

> 原则：**整洁的代码必然可测；测试是代码的说明书。**

- **[强制] 后端测试用 pytest + httpx AsyncClient**（`backend/tests/`），前端用 Vitest（`*.test.ts(x)`）。新功能必须带对应测试（`AGENTS.md` §3.1 相关测试通过）。
- **[强制] 测试遵循 FIRST**：
  - **F**ast：单测跑得快，不依赖真实网络/外部服务；外部调用用 mock。
  - **I**ndependent：测试间无顺序依赖，不共享可变全局。
  - **R**epeatable：结果可复现；不依赖本地时间/随机/绝对路径。
  - **S**elf-validating：每个测试有明确断言，不做无断言的「跑通即通过」。
  - **T**imely：随代码一起写，不是事后补。
- **[建议] 每个测试一个行为点**：命名 `test_<module>_<scenario>_<expect>`，一目了然。
- **[强制] 覆盖「错误路径」与「边界」**：不仅测 happy path，还要测 `not_found`、无权限、超长、空数据、并发认领（如 `tests/test_dsh_sandbox.py`、`tests/test_route_layer_orm_ban.py` 这类守卫测试就是好范式）。
- **[建议] 用 fixture 而非在测试里重复造数据**，并把测试数据与控制逻辑分离（`docs/engineering-standards.md` §3）。
- **[建议] 单测覆盖纯函数/快照**（`uiRunResult.ts`、`caseListFormatters.ts`、`executionStatus.ts`），这些没有副作用的纯函数是回归最稳的「契约」。

---

## 9. 注释规范（与现有规范一致，强调「为什么」）

> 原则（《Clean Code》第 4 章）：**好的注释回答「为什么」，坏的注释复述「是什么」。**

- **[强制] 不写复述语法的注释**：禁止「定义变量」「调用函数」「返回结果」。
- **[强制] 业务规则、权限、状态流转、异常兜底、数据迁移、定时任务、外部系统对接、AI 调用、缓存策略必须写注释**（`docs/engineering-standards.md` §1）。
- **[建议] 注释解释「意图 / 约束 / 后果」**，例如本仓库 `client.ts` 里那段 422 detail 转字符串的注释——正是「为什么这样处理」，属于好的注释。
- **[建议] 用 docstring 标注公共方法与类职责**（Python），用 JSDoc 标注公共 hook 的用途与示例（`useApi.ts` 顶部 JSDoc 是好范例）。
- **[强制] 无调试遗留**：禁止 `print`/`console.log`/`breakpoint`/`debugger`（`AGENTS.md` §3.1）。

---

## 10. 交付与自检清单（对照 `AGENTS.md` §3 落地）

每次 `git push` 前，对照本文档自查：

**后端**
- [ ] 命名遵循 PEP 8 + 意图命名；无 `data/tmp/val` 类命名。
- [ ] 函数 ≤30 行、单一职责；无魔法数字；常量已提取。
- [ ] 路由层不触 ORM、不写业务逻辑；错误用 `APIException` 体系。
- [ ] 事务用 `transaction(db)` 或显式 commit/rollback；无裸 `except: pass`。
- [ ] 状态/删除语义走规范词表与 `is_deleted`；无 `== False`。
- [ ] 新队列走 `task_queue.py` 原语；锁列/失联回收齐全。
- [ ] `ruff check app/ --select F821` 通过；相关 pytest 通过；全量回归说明失败集合。

**前端**
- [ ] 组件薄、命名表意；`any` 仅在边界的 TODO 注释处使用。
- [ ] useEffect 有 cleanup；useCallback 无循环依赖；无 N+1；TabsContent 用 forceMount（`docs/engineering-standards.md` §4）。
- [ ] API 调用走 `api/` 层与 `useApi`；错误在前端内联；AbortError 已处理。
- [ ] 组件/RFC 依赖单向；Store 不做 API 调用；复杂逻辑在 hooks/纯函数。
- [ ] `npm run typecheck && npm run build` 通过；相关 Vitest 通过。

**通用**
- [ ] 无调试遗留、无硬编码凭据、无备份/DB/IDE 临时文件（`AGENTS.md` §3.5）。
- [ ] 生成代码已补用途注释并通过硬门禁。
- [ ] 本次变更涉及的分层/模块/状态改动已同步 `backend/CLAUDE.md`、`frontend/CLAUDE.md` 或相应 PRD（文档保鲜）。

---

## 11. 参考资料

- **《Clean Code: A Handbook of Agile Software Craftsmanship》** — Robert C. Martin (Uncle Bob)，2008。本文档的主题（命名、函数、注释、错误处理、类/分层、味道、测试）均以其章节为骨架。
- [Python PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [FastAPI — Best Practices 官方文档](https://fastapi.tiangolo.com/)
- [The TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)

### 对应的 Gherkin 验收套件

- [测试平台 Clean Code 规范 Gherkin 验收套件](../../tests/clean-code/README.md) — 把本文档每条 `[强制]/[建议]` 转成 `Feature/Scenario/Given/When/Then`，可作人工评审清单或后续自动化门禁基线
  - [01-naming.feature](../../tests/clean-code/01-naming.feature) · [02-functions.feature](../../tests/clean-code/02-functions.feature) · [03-error-handling.feature](../../tests/clean-code/03-error-handling.feature) · [04-layering.feature](../../tests/clean-code/04-layering.feature) · [05-testing.feature](../../tests/clean-code/05-testing.feature) · [06-comments.feature](../../tests/clean-code/06-comments.feature) · [07-ai-generated-code.feature](../../tests/clean-code/07-ai-generated-code.feature) · [08-delivery-checklist.feature](../../tests/clean-code/08-delivery-checklist.feature)

### 对应的代码开发校验门禁

- [测试平台 代码开发校验门禁（减少返工）](../../docs/code-development-gate.md) — 把本文档 §3–§10 的条目与 Gherkin 套件、QA 管理条件整合成 G0–G4 五道门禁。机械项走本地 `scripts/git/dev-gate.ps1`，语义项走评审与 CI。

### 参考的 GitHub 测试平台（前后端）

- [MeterSphere — 一站式开源持续测试平台](https://github.com/metersphere/metersphere)
- [QAMangementSystem — QA 管理平台](https://github.com/Pythagora-io/QAMangementSystem)
- [Tectonic-TCMS — 测试用例与执行周期管理](https://github.com/PaulNasc/Tectonic-TCMS)
- [autotest-platform — 接口/UI 自动化测试平台](https://github.com/seven-017/autotest-platform)
- [Autotest_platform (POM) — Web UI 自动化测试平台](https://github.com/shaonianyr/Autotest_platform)

### 本仓库既有规范（与本规范互相引用）

- [CamelTv 工程输出规范（docs/engineering-standards.md）](../../docs/engineering-standards.md)
- [测试平台 v2 总览（CLAUDE.md）](../CLAUDE.md)
- [后端 FastAPI 约定（backend/CLAUDE.md）](../backend/CLAUDE.md)
- [前端 React 约定（frontend/CLAUDE.md）](../frontend/CLAUDE.md)
