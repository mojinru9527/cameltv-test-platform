# 03｜AITDE 前端与测试工程师使用方案

## 1. 前端设计目标

测试工程师不应该学习“AI Agent 怎么工作”。

他需要解决的是：

```text
我要测哪个版本？
AI认为要测什么？
有没有理解歧义？
什么才算正确？
有哪些 Scenario？
数据准备好了没有？
哪些已经能跑？
为什么 PASS？
为什么 FAIL？
这个 Build 比上一个 Build 好了多少？
```

因此前端核心不是 Chat，而是：

> **Review + Run + Replay。**

Chat 可以存在，但只是辅助入口。

---

# 2. 技术栈建议

现有 React 19 + TypeScript + React Router + shadcn/Radix/Tailwind 可以继续使用。

没有必要为了新架构切 Next.js。

建议新增：

```text
TanStack Query
```

用于 Server State。

职责：

```text
Zustand
→ auth / project / local UI state

TanStack Query
→ mission / scope / contract / scenario / run / replay

SSE
→ live execution / workflow events
```

不要把新的 Mission 数据全部塞 Zustand。

---

# 3. 新信息架构

## 主导航

```text
工作台
测试任务
执行中心
回放与证据
缺陷与验收

──────────

测试资产
  需求与资料
  场景库
  API 资产
  UI 自动化
  测试数据
  环境
  知识

──────────

系统治理
  Worker
  集成
  通知
  AI 配置
  策略
  审计
```

---

# 4. Workbench 重构

旧 Workbench 不再主要展示：

```text
case count
plan count
defect count
```

而展示“我今天需要处理什么”。

```text
┌─────────────────────────────────────────────┐
│ 我的测试任务                                │
│                                             │
│ 会员中心 V3.6   Contract 待确认      [进入] │
│ 支付 V2.9       3 个 P0 FAIL         [进入] │
│ 赛事 V4.1       Build #18 正在执行    [进入] │
├─────────────────────────────────────────────┤
│ 待我确认                                    │
│ Scope 12 项 | Ambiguity 4 | Contract 2      │
├─────────────────────────────────────────────┤
│ 真实业务失败                                │
│ BUSINESS_FAIL 8                              │
├─────────────────────────────────────────────┤
│ 自动化问题                                  │
│ AUTOMATION_FAIL 3 | DATA_FAIL 2             │
└─────────────────────────────────────────────┘
```

---

# 5. 创建 Mission：不要做复杂表单

建议 3 步向导。

## Step 1 基本信息

```text
任务名称
版本标签
测试负责人
默认测试环境
Mission Type
```

类型：

```text
版本测试
功能测试
Hotfix
回归
探索
```

---

## Step 2 导入 Sources

同一页面支持：

```text
拖 PRD
粘需求链接
选择已有需求
OpenAPI URL
OpenAPI File
选择 Test DB
关联历史缺陷
```

每个 Source 显示：

```text
已读取
解析中
解析失败
敏感等级
版本 / hash
```

---

## Step 3 AI 分析

用户点击：

```text
开始分析测试范围
```

不是：

```text
直接生成所有用例
```

---

# 6. Mission Detail

路由：

```text
/missions/:missionId
```

子页：

```text
/overview
/sources
/scope
/contract
/scenarios
/data
/executions
/replay
/trace
```

顶部固定 Mission Header：

```text
会员中心 V3.6
Contract v3 FROZEN
Build #18
Acceptance: NOT READY

[运行回归] [导出] [...]
```

---

# 7. Overview

测试工程师第一眼需要：

```text
当前最重要的问题
```

而不是一堆统计图。

建议：

```text
┌ Scope ──────┐ ┌ Contract ────┐ ┌ Acceptance ──┐
│ 24/24 已确认│ │ v3 FROZEN    │ │ NOT READY    │
└─────────────┘ └───────────────┘ └──────────────┘

阻塞：
🔴 2 个 P0 BUSINESS_FAIL
🟠 1 个 P0 INCONCLUSIVE
🟡 3 个 Automation Fail

最新 Build：
#18

Scenario:
PASS 52
BUSINESS_FAIL 3
AUTOMATION_FAIL 2
DATA_FAIL 1
BLOCKED 4
```

---

# 8. Sources 页面

左侧 Source List：

```text
PRD v3
OpenAPI 2026-08-28
Test DB Schema
Historical Defects
Production Observation
```

中间内容阅读器。

右侧：

```text
AI 提取实体
关联 Scope
引用位置
```

测试工程师点击任何 AI 结论，都可以：

```text
查看来源
```

---

# 9. Scope Review 是第一个核心 UX

建议三栏。

```text
┌──────────────┬────────────────────────┬───────────────┐
│ 需求章节     │ AI Scope Proposal      │ Review        │
│              │                        │               │
│ PRD 3.2      │ 会员续费 P0 FULL       │ ✓ Include     │
│              │ Reason: ...            │ ○ Exclude     │
│              │ API: /renew            │ Depth: Full   │
│              │ DB: membership         │ Risk: P0      │
└──────────────┴────────────────────────┴───────────────┘
```

支持批量：

```text
批准全部低风险建议
仅查看 P0/P1
仅查看 AI confidence < 0.8
```

---

# 10. Scope 必须显示“为什么”

每个 Scope Item：

```text
会员续费
P0 / FULL

为什么纳入：
- PRD 3.2 有修改
- POST /member/renew Schema 变化
- 历史上该模块 3 次线上缺陷

来源：
[PRD 3.2] [OpenAPI diff] [DEFECT-822]
```

不要只显示：

```text
AI建议：Full
```

---

# 11. Ambiguity 页面

测试工程师不需要审 1000 条 Case，优先审：

> AI 不确定的地方。

```text
⚠ Grace Period 是否允许续费？

PRD：
仅说明 EXPIRED

API：
renewable = true

DB：
存在 GRACE_PERIOD

[允许]
[不允许]
[本版本不测]
[需要产品确认]
```

点击选项后直接记录为 Contract 输入。

---

# 12. Contract 页面

Contract 页面不是大段 JSON。

按业务规则展示。

```text
会员续费

成功标准
✓ Order = SUCCESS
✓ Membership = ACTIVE
✓ Privilege usable = true
✓ UI 显示新有效期

禁止条件
✓ SUSPENDED 不允许续费

待确认
0

来源可信度
Requirement Explicit  3
Tester Approved       2
AI Inferred           0
```

---

# 13. Freeze Interaction

点击：

```text
冻结 Contract v3
```

弹窗明确：

```text
冻结后：
- AI 不能修改业务预期
- 已生成 Scenario 将绑定 v3
- 后续修改将创建 v4 Proposal

未解决 P0/P1 Ambiguity：0

[确认冻结]
```

这是非常重要的信任操作。

---

# 14. Contract Diff

后续 v4：

```text
v3                 v4

EXPIRED 可续费       EXPIRED 可续费
GRACE 未定义     →  GRACE 可续费
```

高亮：

```text
哪些 Scenario 受影响
哪些 Oracle stale
哪些 Run 需要重跑
```

---

# 15. Scenario Matrix 是测试工程师主工作区

```text
Scenario            Risk  Data  Manual API UI DB Hybrid  Last

过期会员续费          P0    ✓     ✓    ✓  ✓  ✓    ✓     PASS
余额不足              P0    ✓     ✓    ✓  -  ✓    ✓     PASS
重复点击              P1    ✓     ✓    ✓  ✓  ✓    ✓     FAIL
Amount 边界           P1    -     ✓    ✓  -  -    -     PASS
UI 有效期展示         P1    ✓     ✓    -  ✓  -    -     PASS
```

支持：

```text
按风险
按模块
按功能点
按状态
按 Build
按 Adapter
```

---

# 16. Scenario Detail

布局：

```text
┌─────────────────────────────────────────────────────┐
│ MEMBER-RENEW-001 | P0 | Contract v3                │
├─────────────────────────────────────────────────────┤
│ Business Goal                                       │
│ 过期会员续费后立即恢复权益                           │
├────────────────┬────────────────────────────────────┤
│ Given          │ user normal                       │
│                │ membership expired                │
│                │ balance >= 100                    │
├────────────────┼────────────────────────────────────┤
│ When           │ renew monthly                     │
├────────────────┼────────────────────────────────────┤
│ Then / Oracle  │ DB membership = ACTIVE            │
│                │ API privilege usable = true       │
│                │ UI shows active                   │
├────────────────┴────────────────────────────────────┤
│ Sources: PRD 3.2.1 | API /renew | Tester approved  │
└─────────────────────────────────────────────────────┘
```

---

# 17. Functional View

测试工程师仍然可以点击：

```text
[功能用例视图]
```

看到传统：

```text
前置条件
步骤
预期
```

并可以：

```text
开始人工执行
```

这是功能测试阶段特别重要的能力。

---

# 18. Assisted Manual Execution

最终平台不应该逼所有功能测试都立即自动化。

人工执行也使用同一个 Scenario。

用户点击：

```text
开始人工执行
```

系统先：

```text
自动准备 Data Fixture
```

然后进入：

```text
步骤 1 / 5
登录用户

[已完成]
[失败]
[阻塞]
[添加截图]
```

与此同时平台可以后台：

- 记录 Browser Session（如果在受控浏览器中）；
- 抓 XHR；
- 采集 Screenshot；
- 自动执行 DB/API Oracle；
- 保存人工备注。

这样：

> 功能测试阶段已经进入 Runtime，而不是等 UI 自动化写完以后才享受平台能力。

---

# 19. Record / Observe Mode

功能测试工程师第一次手工走业务时：

```text
[开始观察模式]
```

平台打开 Browser Session：

```text
Tester 操作
     ↓
Browser Observer
     ├ DOM semantic event
     ├ click/input
     ├ navigation
     ├ XHR/fetch
     ├ screenshot
     └ timing
```

结束后：

```text
AI 建议生成 UI Action Plan
```

测试工程师 Review 后形成 Regression Adapter。

这比让 AI 自己一开始盲点生产/测试页面更可靠。

---

# 20. Data Workspace

不要让测试工程师首先看到 SQL。

看到：

```text
Scenario 需要的数据

Member
  status = EXPIRED

Wallet
  balance >= 100
```

系统给策略：

```text
✓ Test DB 已找到符合数据
  User #T-8892

或者：

需要创建
  Strategy: API Builder
  预计 3 个实体

[预览数据计划]
[准备]
```

---

# 21. 数据 Plan 详情

高级模式：

```text
Data Plan

1. Create user
2. Create member
3. Set membership expired
4. Set balance 100
5. Lease for Run
6. Cleanup after run

Affected:
member_test.user
member_test.membership
member_test.wallet
```

测试工程师可以知道 AI 要造什么，而不是让它偷偷改数据库。

---

# 22. Execution Launch

点击：

```text
运行
```

弹出：

```text
Environment:
TEST-5

Build:
2026-08-28.18

Scope:
○ 当前 Scenario
○ 当前模块
● 受影响 Scenario
○ 全量

Data:
● Auto Prepare

Browser:
Chromium

Evidence:
✓ Screenshot
✓ Trace
✓ Network
✓ DB Snapshot

[执行]
```

---

# 23. Preflight Check

真正执行前系统自动：

```text
Environment reachable      ✓
Worker available            ✓
DataSource reachable        ✓
Required Secret available   ✓
Contract Frozen             ✓
Scenario compiled           ✓
Required Oracle supported   ✓
```

有问题：

```text
禁止开始
```

这能减少很多“跑了半天才发现环境/数据不对”。

---

# 24. Live Execution

```text
RUN #812

PREPARING_DATA  ✓
EXECUTING       ●
ASSERTING
COLLECTING
CLASSIFYING

Timeline
09:31:02 DATA  ensure expired member     ✓
09:31:05 UI    login                     ✓
09:31:08 API   GET /membership           200
09:31:12 UI    click 立即续费             ●
```

前端通过 SSE 实时更新。

---

# 25. Outcome UI 必须避免所有错误都显示红色 FAIL

建议：

```text
PASS                 ✓
BUSINESS_FAIL         ✕ 业务失败
AUTOMATION_FAIL       ⚙ 自动化问题
DATA_FAIL             ◇ 数据问题
ENV_FAIL              ◇ 环境问题
ASSERTION_ERROR       ! 断言配置
BLOCKED               ⊘ 尚不可测
INCONCLUSIVE          ? 无法裁决
```

同时始终显示文字，不只依赖颜色。

---

# 26. Replay 是第二个核心 UX

三栏：

```text
┌───────────────┬───────────────────────┬─────────────────┐
│ Timeline      │ Visual / Browser      │ Evidence Detail │
│               │                       │                 │
│ DATA ✓        │ Screenshot / DOM      │ Request         │
│ LOGIN ✓       │                       │ Response        │
│ POST 200 ✓    │                       │ DB Before       │
│ DB ✕          │                       │ DB After        │
│ ASSERT ✕      │                       │ Oracle          │
└───────────────┴───────────────────────┴─────────────────┘
```

---

# 27. PASS Replay

即使 PASS：

```text
Why PASS?

Required Oracle

✓ Membership DB = ACTIVE
✓ Privilege API = true
✓ UI = active

Evidence completeness: 100%

[查看时间线]
```

用于防止假成功。

---

# 28. BUSINESS_FAIL Replay

显示：

```text
业务失败

Expected:
membership.status = ACTIVE

Actual:
EXPIRED

Oracle Source:
PRD 3.2.1
Contract v3

Related Evidence:
POST /renew → 200
DB after → EXPIRED
```

---

# 29. AUTOMATION_FAIL Replay

例如：

```text
自动化失败，不等于业务失败

原因：
Locator not found

业务 Oracle：
NOT EVALUATED

AI 建议：
按钮文本由“续费”变为“立即续费”

[查看 Healing Proposal]
[批准修复并重跑]
```

---

# 30. Healing UX

显示明确 diff：

```text
Before
getByRole('button', {name: '续费'})

After
getByRole('button', {name: '立即续费'})

Reason
当前 DOM 仅存在“立即续费”

Scope
Action only

Oracle changed?
NO
```

只有 Oracle 不变时才允许“一键批准”。

---

# 31. Failure Triage

AI 分析放在结果之后：

```text
AI 分析（不是最终判定）

高概率问题：
续费接口返回成功，但会员状态未更新。

证据：
API 200
DB EXPIRED
UI EXPIRED

建议开发检查：
1. 事务提交
2. membership update
3. async event consumer
```

测试工程师可以：

```text
[创建缺陷]
```

---

# 32. Defect Create

自动带：

```text
Scenario
Contract version
Build
Expected
Actual
Replay URL
Evidence refs
Environment
Fixture
```

测试工程师只补：

```text
标题
严重等级
负责人
```

---

# 33. Continuous Acceptance Dashboard

不是代码进度。

```text
Build           P0 GREEN     P1 GREEN    Gate

#15             8/12         17/28       FAIL
#16             10/12        21/28       FAIL
#17             11/12        26/28       FAIL
#18             12/12        28/28       PASS
```

点击任意 Build：

```text
从 #17 → #18
变绿 Scenario: 3
新增失败: 0
仍阻塞: 0
```

---

# 34. “开发修好了吗”的体验

测试工程师不再：

```text
收到开发一句“修好了”
→ 找数据
→ 重新手测
```

而是：

```text
Build #19 被检测
→ 受影响 Scenario 自动执行
→ BUSINESS_FAIL → PASS
→ 测试收到通知
```

---

# 35. Trace 页面

新的 Trace 从：

```text
Requirement → TestCase → Execution
```

升级：

```text
Source
→ Scope
→ Intent
→ Contract
→ Scenario
→ Oracle
→ Adapter
→ Run
→ Assertion
→ Evidence
→ Defect
```

任何节点可点击。

---

# 36. 专业资产页面如何保留

## API Test

仍然允许：

- OpenAPI 浏览；
- 单接口调试；
- Request Builder；
- Schema；
- 手工执行；
- 生成 API Adapter。

额外显示：

```text
Referenced by 18 Scenarios
```

---

## UI Test

仍然允许：

- Browser Script；
- locator；
- trace；
- video；
- standalone run。

额外显示：

```text
Generated from Scenario / Action Plan
```

---

## Dataset

改名：

```text
测试数据
```

包含：

```text
Static Dataset
Data Source
Fixture
Lease
Template
```

---

# 37. 用户权限体验

权限不要让普通 Tester 处理复杂 Policy。

按钮层体现：

```text
生产数据：只读
生产浏览：观察模式
测试环境：允许造数
```

高风险动作：

```text
需要审批
```

并说明原因。

---

# 38. AI 交互原则

## 不推荐

每个页面一个：

```text
Ask AI...
```

让用户自己想 Prompt。

## 推荐

上下文动作：

```text
[分析测试范围]
[发现需求歧义]
[生成 Scenario]
[生成 UI Action Plan]
[分析失败]
[建议修复]
```

Prompt 被产品能力吸收。

---

# 39. AI 建议必须有三个东西

每条建议：

```text
建议
依据
置信度 / 不确定性
```

例如：

```text
建议：
Grace Period 纳入 FULL

依据：
DB 状态存在
API renewable=true
历史缺陷 DEF-31

Confidence:
0.72

[批准] [拒绝] [需要确认]
```

---

# 40. Reviewer Efficiency

Review 页面默认优先展示：

```text
AI confidence 低
P0/P1
Oracle = AI_INFERRED
新出现状态
Contract Diff
```

测试工程师不需要逐条审所有 AI 正确的机械边界 Case。

---

# 41. Frontend Route 设计

```text
/workbench

/missions
/missions/new
/missions/:id/overview
/missions/:id/sources
/missions/:id/scope
/missions/:id/contract
/missions/:id/scenarios
/missions/:id/data
/missions/:id/executions
/missions/:id/replay
/missions/:id/trace

/executions
/executions/:runId
/executions/:runId/replay

/assets/requirements
/assets/scenarios
/assets/apis
/assets/ui
/assets/data
/assets/environments
/assets/knowledge

/defects
/acceptance

/admin/workers
/admin/ai
/admin/policies
/admin/audit
```

旧路由保留 redirect/legacy。

---

# 42. 前端代码结构

```text
src/
├ app/
│  ├ router/
│  └ providers/
│
├ features/
│  ├ missions/
│  ├ sources/
│  ├ scope/
│  ├ contracts/
│  ├ scenarios/
│  ├ data/
│  ├ executions/
│  ├ replay/
│  ├ acceptance/
│  └ assets/
│
├ entities/
│  ├ mission/
│  ├ scenario/
│  ├ oracle/
│  ├ run/
│  └ evidence/
│
├ shared/
│  ├ api/
│  ├ ui/
│  ├ hooks/
│  ├ events/
│  └ utils/
│
└ legacy/
```

---

# 43. Query Key

例：

```text
mission.detail(id)
mission.scope(id)
mission.contract(id)
mission.scenarios(id, filters)
run.detail(runId)
run.timeline(runId)
run.evidence(runId)
```

SSE event 到达后：

```text
invalidate / patch query cache
```

---

# 44. 大列表

Scenario / Evidence / Timeline 必须：

- server-side filter；
- pagination；
- virtual list；
- URL 保存 filter；
- 可复制 share link。

---

# 45. Empty State

新系统会有很多阶段状态。

不要只写：

```text
暂无数据
```

例如 Contract 为空：

```text
尚未生成 Test Contract

需要先：
1. 确认 Scope
2. 解决 P0/P1 Ambiguity

[前往 Scope]
```

---

# 46. Error Recovery UX

如果 AI 分析失败：

```text
Scope analysis failed

已完成：
Source parse ✓

未执行：
Scope generation

[重试 Scope 分析]
```

不要从头创建 Mission。

这是后端 Durable Workflow 在 UX 上的重要体现。

---

# 47. 前端最重要的几个“保护型交互”

## Freeze

显式确认。

## Production

显示环境徽标：

```text
PRODUCTION / READ ONLY
```

## DB Fixture

显示影响实体预览。

## Retry

告诉用户：

```text
是否复用 Fixture
是否重新创建 Browser Context
```

## Contract Change

必须显示影响 Scenario。

---

# 48. 测试工程师 5 条真实使用旅程

## Journey A：需求评审当天

```text
创建 Mission
→ 导 PRD/OpenAPI
→ AI Scope
→ Review
→ 解决 Ambiguity
→ Freeze Contract
→ 场景生成
```

结果：

> 开发前已经知道“做到什么才算正确”。

---

## Journey B：功能测试阶段

```text
Scenario
→ 系统自动准备测试数据
→ Assisted Manual Execution
→ Tester 手工操作
→ 系统后台抓 API/DB/截图
→ Oracle 自动校验
→ Replay
```

价值：

> 就算 UI 自动化尚未生成，功能测试阶段已经享受 Data / Oracle / Evidence 能力。

---

## Journey C：将手工路径转 UI 自动化

```text
Observe Mode
→ Tester 正常操作
→ 系统捕获 DOM/XHR
→ AI 生成 Action Plan
→ Tester Review
→ Regression Adapter
→ 执行
```

---

## Journey D：审查 AI 是否假成功/假失败

```text
点击 PASS/FAIL
→ Replay
→ Oracle
→ Evidence
→ 时间线
→ 确认 / 标记误判
```

该反馈进入质量指标。

---

## Journey E：新 Build 到达

```text
Environment Fingerprint changed
→ Impact Analysis
→ 自动回归
→ Dashboard 更新
→ 测试只处理真正失败
```

---

# 49. 用户无需知道的东西

普通 Tester 默认不需要看到：

```text
Temporal Workflow ID
LangGraph 节点
模型 Prompt
Worker Task Queue
SQL connection string
Object Storage URI
```

这些只在 Advanced / Admin 模式。

---

# 50. 前端最终成功标准

一个测试工程师从需求评审到验收：

> 80% 以上操作应该在一个 Mission 内完成。

测试工程师不应该为了完成一个 Scenario 来回跳：

```text
需求 → Dataset → API → UI → TestPlan → Report → Trace
```

这些旧工作区可以存在，但 Mission 应该把它们以“业务上下文”聚合起来。
