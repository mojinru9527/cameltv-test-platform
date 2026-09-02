# Batch 213 — PRD Summary：首页我的待办（B3 / home-todo）

> **Product (🟦)** | Date: 2026-09-02 | Status: Review | Executor: Codex | 完整批次（前后端）

## 1. 问题陈述

- 平台重构定位「AI 版本验收工作台」（`docs/platform-refactor/01` §1/§3.1）：测试工程师默认 5 个一级入口，
  第一条就是**我的待办（首页）**——「今天要审什么、什么在跑、什么失败」；但现状 `/workbench` 仍是**数字宫格**：
  一堆用例/计划/通过率/优先级/跨项目图表（`pages/workbench/index.tsx`），普通测试员第一眼看不出「今天点哪」；
- 导航已由 batch-212（B2）收敛为「工作台 / 版本验收 / 结果与缺陷 / 知识中心 / 资产与更多」5 行，
  但「工作台」入口点进去还是旧版数字宫格，与「工作台 = 我的待办」的新定位脱节；
- 平台虽已有若干「待办」语义的数据（AI 生成候选用例待审 `RequirementReview`、后台 AI 任务 `AiTask`
  running/failed、缺陷 `Defect` open、发布包 `ReleaseBundle` active），但**没有一处把它们聚合成「今天该干嘛」的单一入口**；
- 路线图 B3 出口标准：**工作台改「我的待办」（待审/在跑/失败/待放行聚合）；dashboard API；3 分钟说出今天点哪；无埋点**。
- 证据：B2 PRD「非目标」明确把「我的待办」工作台内容改造留给 batch-213；`pages/workbench/index.tsx` 为旧数字宫格。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 工作台第一屏 | 数字宫格（图表/StatCard/无任务列表） | 「我的待办」四区（待审/在跑/失败/待放行）每区有数量 + 可点击条目 | 本批 QA 截图 + 浏览器走查 |
| dashboard API | 无待办聚合接口 | 新增 `GET /api/v1/dashboard/todo`，待审/在跑/失败/待放行各返回 count + items | 接口测试 + 前端仅一次有效请求 |
| 「3 分钟说出今天点哪」 | 需进入多个模块才能知道 | 首屏即见可点任务，每条可直达对应模块/过滤 | 小白走查（3 分钟内说出并点出 1 条） |
| 埋点 | — | 0（不加任何埋点） | rg 查 `analytics`/`track` 无新增 |

## 3. 非目标（本次不做）

- **不做版本验收任务模型/向导**（`VersionTask` 唯一事实源、建任务向导/审核面板）——B6/batch-216、B7/batch-217；
- **不做结果与缺陷聚合页**（一键运行/证据回放/失败分类）——B8/batch-218；**不做放行页**——B9/batch-219；
- **不做知识管线与智能回归**——B11/B12（batch-221/222）；
- **不做「待放行」的完整验收状态机**——B3 仅先把 `ReleaseBundle status=active`（当前版本）作为「待放行」聚合，
  完整多阶段放行状态随 B9/batch-219 建立；
- **不删除旧数字宫格图表/接口**（`/dashboard/stats`、`/dashboard/cross-project` 保持兼容，供既有页面/外部引用）；
  仅替换「工作台页面」默认展示；旧接口不删，避免破坏报告中心等引用方；
- **不加埋点**（owner 单用户，用户已取消）。

## 4. 用户故事 + 验收标准

- As 黑盒测试员，I want 登录后第一眼是「我的待办」，so that 我能立刻知道今天该审什么、什么在跑、什么失败、哪个版本待放行。
  - 验收：Given 我已登录 / When 进入首页 `/` / Then 默认落地 `我的待办`（/workbench），首屏展示四个待办区，不再出现数字宫格。
- As 测试员，I want 每个待办条目可点击直达对应模块，so that 我能从「知道」到「去做」一步到位。
  - 验收：Given 待办列表有数据 / When 点击「待审」条目 / Then 跳转 `/requirement/:id/review`；点击「在跑」→ 相应任务/执行页；点击「失败」→ 缺陷/执行页；点击「待放行」→ `/release-bundles/:id`。
  - 验收：每个待办区均提供「查看全部」链接，直达该模块列表页。
- As 测试员，I want 看到的是**我负责/可见项目**的待办，so that 我不用跨项目翻找。
  - 验收：接口按当前用户项目/权限过滤，仅返回当前项目（`current.project_id`）相关的待办数据。

## 5. 技术考量

- **后端**：新增 `GET /api/v1/dashboard/todo`（v1 dashboard 路由，沿用 `CurrentUser`/`get_db` 依赖），聚合四桶：
  - 待审：`RequirementReview.status='pending'`（AI 生成候选用例，关联需求文档标题）；条目 link=`/requirement/{requirement_id}/review`；
  - 在跑：`AiTask.status='running'`（后台 AI 任务，含 task_type）；link 到任务/需求相关页；
  - 失败：`AiTask.status='failed'` + `Defect.status` 非 `closed/rejected`（open/confirmed/fixing/pending_review）；link=`/defect/{id}`、报告中心；
  - 待放行：`ReleaseBundle.status='active'`（当前版本发布包）；link=`/release-bundles/{id}`。
  - 统一 `count` + `items`（每桶最多取 5 条，含 id/title/subtitle/link）；空桶返回 count=0、items=[]。
- **前端**：重写 `pages/workbench/index.tsx` 为「我的待办」页（保留路径 `/workbench`、文档标题改「我的待办」）；
  `api/dashboard.ts` 增加 `fetchDashboardTodo`；页面用 `useApi` 单次拉取（GET 只出现 1 次有效请求）。
- **首页落地**：`router/index.tsx` 的 `PlatformHomeEntry` 默认改为 `Navigate to="/workbench"`（我的待办），
  让「登录第一眼即我的待办」成立；保留 `版本验收` 菜单项直达 `/missions`（AITDE 引擎入口仍可达）。
  - 风险：V40-019「AITDE 开启时默认落 /missions」将被覆盖——这是**刻意决策**：新定位以「我的待办」为首页，
    AITDE 引擎不再抢首页，但通过「版本验收」入口与 `/missions` 路由仍深度可达；本 PRD 记录该决策供 Leader 复核。
  - 若该决策被否决，退化为「仅改 /workbench 页面内容 + API，不动首页跳转」，仍满足 B3 出口。
- **依赖**：batch-211 基线（01 定位 / 03 术语）+ batch-212 导航（`nav-config` 已把「工作台」置顶）；无新依赖。
- **风险**：四桶数据源状态的语义是「借用现有字段」，非新模型；后续 B6 引入 `VersionTask` 后应在 B8/B9 迁移到真实待办语义（记入交接区）。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批合入 main | owner（唯一真实用户） | 首屏即「我的待办」；四区有数量/条目；每区可点直达；接口返回正确；QA 小白走查 3 分钟内说出并点出 1 条 |
| M0 出口（B1–B5） | owner | 登录第一眼即「我的待办」；C 级入口已下架；死代码已清（B5） |

## 7. 技能使用

- `cameltv-ui-conventions` → 「我的待办」卡片/列表/空态用 shadcn 语义组件核对（非测试证据；走查结论见设计规范）。
- `cameltv-bug-guard` → 前端 `useApi`/useEffect/路由 改前避坑（useEffect cleanup、GET 单次、无 N+1）。
- `cameltv-agent-team` → 本批为完整批次六部门工件流程。


