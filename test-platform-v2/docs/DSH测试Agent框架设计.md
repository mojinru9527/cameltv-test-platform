# DSH 测试 Agent 框架设计

> 版本：v1.1 | 日期：2026-08-17 | 状态：三阶段已落地（评审确认 2026-08-17）
> 执行器：DeepSeek Harness（feature/dsh-test-agent-framework）
> 关联：ADR-0009（知识中心）、ADR-0010（向量检索）、docs/agent-team/dsh-agent-teams.md（船长手册）、RAG知识图谱与Agent持续学习能力落地执行文档.md（M0-M4 路线图）

---

## 1. 背景与目标

测试平台已接入 DeepSeek Harness（DSH），但 DSH 目前只用于**开发批次**（模式② 船长团队，PRD→PM→Design→Dev→QA）。本框架把 DSH 扩展为**测试工程师的日常工作流**：

> 测试工程师导入需求 → DSH 通过知识中心熟悉项目 → 设计/补齐用例（走既有 skill 规则直接入库）→ 触发平台 Runner 执行 → 审查与报告 → 知识回流 → 流程自更新

**核心主张**：以知识中心为**骨架**（项目知识结构），以功能用例/接口用例/自动化用例为**血肉**（用例资产），以 DSH tester-team 为**执行者**，形成「导入需求即可用」的完整框架。

## 2. 现状盘点（复用资产，不重复建设）

| 资产 | 位置 | 状态 |
|------|------|------|
| DSH 任务执行抽象 | `backend/app/services/dsh/dsh_runner.py`（single/team 两形态、DSH_MODEL/KEY 环境注入、并发闸门、心跳续期） | ✅ 已落地 |
| AgentTeams 船长模式 | `agent_team_persona.py`（full/light persona 纯函数）+ `agent-team/` profile 模板 | ✅ 已落地（开发批次用） |
| DSH 任务 API | `api/v1/dsh_tasks.py`（提交/列表/详情/取消，mode=single\|team） | ✅ 已落地 |
| 知识中心检索/图谱 | `api/v1/knowledge_core.py`（/search RAG）、`knowledge_graph.py`（实体/关系/模块关联/设计稿） | ✅ 已落地 |
| 模块-用例-接口实体关联 | `POST /knowledge/graph/module-associations`（module/test_case/api 实体 + contains/tested_by 等关系，Batch 122/132） | ✅ 已落地（L0 骨架实体层） |
| 开放 API（API Token 鉴权） | `api/v1/open_api.py`（触发计划/UI 测试、查执行结果、回写结果、质量门禁） | ✅ 已落地 |
| 用例生成规则 | `.agents/skills/test-case-design/`（= tests/test-case-standards/ 标准） | ✅ 已就位（单一事实源） |
| MCP 服务先例 | `lanhu-mcp/`（FastMCP HTTP 模式，端口 8000） | ✅ 已落地（模板） |
| 需求/用例/接口查询面 | `/requirements`、`/test-cases`、`/apitest`、`/requirement-modules` | ✅ 已落地 |

**缺口**（本框架新建）：

1. **knowledge-mcp**：知识中心 → DSH 的实时查询/执行/回写通道（决策：MCP 桥接实时查询）
2. **tester-team persona/preset**：测试工程师视角的船长团队（决策：平台 Runner 执行、agent 编排）
3. **开放 API 知识查询面**：open_api.py 目前只有执行触发，缺只读知识查询（知识 API 走 JWT+权限，MCP 需要 API Token 通道）
4. **L0 项目知识拓扑视图**：模块关联实体已入库，缺「按模块聚合查询」的对外视图
5. **产品化层**：模型/key 切换、实例池托管、用户入口（阶段 3）

## 3. 总体架构（三层一闭环 + 元审查）

```
┌─ L4 元审查层 ─────────────────────────────────────────┐
│  reviewer 角色（独立模型视角）+ 流程反思卡               │
│  → 回写知识中心 → preset 自动加载最新流程版本            │
└──────────────┬───────────────────────────────────────┘
┌─ L2 Agent 执行层（DSH tester-team）──────────────────┐
│  船长 tester-lead：导入需求 → 拆任务 → 汇总报告         │
│  analyst（项目熟悉）→ case-designer（用例设计）→        │
│  api-tester ∥ ui-tester（触发执行+判定）→ reviewer     │
│  （成员可配独立模型 → 交叉审查第二视角）                │
└──────┬───────────────────────┬───────────────────────┘
       │ knowledge-mcp 查询/执行/回写
┌──────┴─────────┐        ┌─────┴──────────┐
│ L0 骨架         │        │ L1 血肉        │
│ 项目知识拓扑    │        │ 用例三关联     │
│ （模块实体+关联）│        │ + skill 规则   │
└──────┬─────────┘        └─────┬──────────┘
       └── L3 回写闭环（执行结果/用例/缺陷 → 知识中心）──┘
```

## 4. L0 骨架：项目知识拓扑

**复用**：`knowledge_entity`（module/test_case/api 实体）+ `knowledge_relation`（contains/tested_by/navigates_to/links_to_admin/configures）已具备骨架实体层（Batch 122/132）。

**本框架新增**：对外「模块拓扑视图」——按模块聚合其下需求/用例/接口/设计稿：

- 后端：`POST /knowledge/module-topology/query`（新端点，service 层聚合 entity+relation+source）
- 返回：`[{module, module_id, requirements[], test_cases[], api_contracts[], design_assets[], freshness}]`
- knowledge-mcp 的 `get_module_topology` 工具封装该端点

## 5. L1 血肉：用例三关联 + skill 单一事实源

- 用例生成规则**单一事实源** = `test-case-design` skill（tests/test-case-standards/ 标准）；DSH 不另造规则
- case-designer 成员强制挂载该 skill，产出必须通过 skill 自检清单
- 用例入库走 `POST /test-cases`（平台既有 CRUD，直接入库，不走 AI 审核台——2026-08-17 评审决策）
- 用例三关联元数据（模块归属/需求追溯/接口契约）在生成时即写入

## 6. L2 Agent 执行层

### 6.1 knowledge-mcp（新组件，仓库根 `knowledge-mcp/`，仿 lanhu-mcp）

FastMCP HTTP 模式（独立端口 8110），鉴权 = 平台 API Token（`Authorization: Bearer tpat_xxx`）+ `X-Project-Id`，经开放 API 通道访问（见 §7）。

| 工具面 | 工具 | 底层端点 |
|--------|------|---------|
| 查询 | `search_knowledge(query, source_types?, limit?)` | `POST /knowledge/search`（open 通道） |
| 查询 | `get_module_topology(module?)` | `POST /knowledge/module-topology/query`（新） |
| 查询 | `get_requirements(keyword?, module?)` | `GET /requirements` |
| 查询 | `get_test_cases(module?, keyword?, page?)` | `GET /test-cases` |
| 查询 | `get_api_contracts(module?)` | `/apitest` 资产 + 模块拓扑聚合 |
| 查询 | `get_design_specs(module?)` | `/knowledge/design-assets/*` |
| 查询 | `get_skill_template(template_key)` | 平台 Skills 模板 ↔ DSH skill 映射（阶段 3 细化） |
| 执行 | `trigger_test_execution(plan_id, env?)` | `POST /open/plans/{id}/trigger` |
| 执行 | `get_execution_result(run_id)` | `GET /open/runs/{run_id}` |
| 回写 | `submit_test_cases(cases[])` | `POST /test-cases` |
| 回写 | `submit_defect(defect)` | `POST /defects`（阶段 3） |

### 6.2 tester-team persona（后端新增 `tester_team_persona.py`）

复用 agent-team profile（工具集相同），persona 替换为测试视角。成员集：

```
full：tester-lead（船长）/ analyst / case-designer / api-tester / ui-tester / reviewer
light：tester-lead / analyst / case-designer（含审查）
```

- 任务依赖：analyst → case-designer → {api-tester ∥ ui-tester} → reviewer → 船长报告
- 固定步骤沿用 `_STEPS` 纪律（认领必唤醒、轮询至全部 completed）
- 约束：用例生成必须遵守 test-case-design skill 自检清单；执行走平台 Runner 不自行直连测试环境；产物写 work-logs/
- `params.team_kind="tester"` 时 dsh_task_service 选用该 persona（batch_mode 语义保留）

### 6.3 onboarding 标准流程（「熟悉项目」）

1. 用户提交需求（文档导入 / 选择已有需求）+ 目标
2. analyst 通过 knowledge-mcp 拉模块拓扑 → 定位受影响模块 → 拉需求/接口/用例/设计稿
3. 产出「项目理解摘要 + 测试影响面 + 用例建议」
4. case-designer 按 skill 规则产出用例 → 直接入库
5. reviewer 审查（覆盖/格式/断链）→ 船长汇总报告
6. 结果回写知识中心（agent_run 留痕）

## 7. 开放 API 知识查询面（阶段 1 后端改造）

open_api.py 新增只读知识查询端点（API Token 鉴权，project 隔离）：

```
GET  /open/knowledge/sources         知识源列表（分页/类型过滤）
POST /open/knowledge/search          RAG 混合检索
GET  /open/knowledge/modules         模块拓扑列表
GET  /open/requirements              需求文档列表
GET  /open/test-cases                用例列表（module/keyword 过滤）
```

- 路由层不直连 ORM（Batch 181 强制）：全部收敛到既有 service
- 复用 `verify_api_token` + `token.project_id` 隔离
- 用例回写：`POST /open/test-cases`（受 token project 隔离，写入用例库）——供 submit_test_cases 使用

## 8. L3 回写闭环

- 执行结果：平台 Runner 原生自动入库（执行结果事件源），无需额外开发
- 用例：knowledge-mcp `submit_test_cases` → `POST /open/test-cases` 直接入库
- 缺陷：`submit_defect`（阶段 3）
- 保鲜：知识中心 freshness 机制自动标记过时需求 → agent 下次检索即见

## 9. L4 元审查层

- reviewer 三个触发点：
  1. 用例设计完成 → 对照需求核覆盖 + 对照 skill 规则核格式
  2. 需求调整 → 平台「知识差异对比」能力找受影响用例
  3. 用例转换（功能→接口→自动化）断链检查
- 流程反思卡：每个批次 reporter 产出「流程反思卡」（哪卡了、缺什么工具/视角）→ 回写知识中心 → 下批 preset 自动加载最新流程版本（流程自更新）
- 交叉审查：reviewer 用独立模型快照（agent-teams 成员支持独立 provider/model）

## 10. 产品化形态（阶段 3）：平台托管 DSH 实例池

- 复用 dsh-headless 集成（#282 已内置 DSH 运行时到 backend 镜像）：平台后端调度 DSH 实例池
- 测试工程师登录平台 → 浏览器内嵌 DSH 工作台（或经 dsh-tasks API 提交任务）→ 零安装
- **模型/key 切换 = 平台设置页**：
  - `dsh_runner` 已支持 `model` 参数 + `DSH_MODEL`/`DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL` 环境注入（每任务隔离）
  - 新增模型池配置（settings 或 DB 表）：管理员维护可用模型列表；用户任务可指定模型；key 走平台池或用户自填
- 实例调度沿用已验证踩坑经验：心跳续期防 stale 回收、workspace 隔离、并发闸门

## 11. 落地路线（三阶段）

> **2026-08-17 三阶段全部落地**（feature/dsh-test-agent-framework），见 §14 落地清单。

| 阶段 | 内容 | 验收标准 |
|------|------|---------|
| **1. Onboarding 先行** | knowledge-mcp 查询面 + 开放 API 知识查询面 + tester_team_persona（analyst/case-designer/reviewer）+ onboarding 流程 | ✅ 导入需求 → 项目理解摘要 + 用例直接入库 + 审查报告（单测/集成测试通过；MCP 端到端冒烟通过） |
| **2. 接口测试打通** | api-tester + trigger_test_execution/get_execution_result + 结果回读判定 | ✅ 接口用例 → 平台 Runner 执行 → 判定回写（端到端冒烟：计划列表→详情→触发→执行记录回读） |
| **3. 全自动 + 产品化** | ui-tester + 实例池托管 + 模型/key 平台化 + submit_defect | ✅ ui-tester 编排面（open UI 任务列表 + MCP 工具）；模型池（dsh_model_pool 配置/准入/前端下拉）；实例池复用 dsh-headless 集成（#282）；submit_defect 留待缺陷模块对接 |

## 12. 风险与治理

| 风险 | 对策 |
|------|------|
| 用例直接入库污染正式库 | skill 自检清单强制 + reviewer 审查环节兜底（不阻塞入库但留痕） |
| MCP 鉴权泄漏 | API Token 最小权限 + project 隔离 + 限流（60/min 复用） |
| DSH 长任务失联 | 心跳续期已有（60s/1800s 超时），tester 任务同样受控 |
| 两套 skill 体系漂移 | 平台模板 ↔ DSH skill 映射单一事实源（阶段 3 get_skill_template） |
| 并发批次串扰 | DSH_MAX_CONCURRENT 闸门 + workspace 隔离（已有） |

## 13. 关联文档

- 船长手册：`docs/agent-team/dsh-agent-teams.md`
- 知识中心：`知识中心-用户使用手册.md`、`RAG知识图谱与Agent持续学习能力落地执行文档.md`
- 用例规则：`tests/test-case-standards/`、`.agents/skills/test-case-design/`
- MCP 先例：`lanhu-mcp/`

## 14. 落地清单（2026-08-17，feature/dsh-test-agent-framework）

### 后端（test-platform-v2/backend）

| 文件 | 内容 |
|------|------|
| `app/services/dsh/tester_team_persona.py` | 测试船长 persona 纯函数（analyst/case-designer/api-tester/ui-tester/reviewer；skill 自检 + 平台 Runner + reviewer 三触发点约束） |
| `app/services/dsh/dsh_task_service.py` | `params.team_kind` 分派（tester→tester_team_persona，缺省 dev 不回归）；`params.model` 透传 runner（single/team） |
| `app/schemas/dsh.py` | `team_kind`（dev\|tester）+ `model`（非空串）校验 |
| `app/api/v1/open_knowledge.py` | Agent 查询面：知识源/检索/模块拓扑/需求/用例（读+写）/计划（列表/详情/执行记录）/UI 任务列表 |
| `app/api/v1/dsh_tasks.py` | `/model-pool` 端点 + 模型池准入校验 |
| `app/core/config.py` | `dsh_model_pool` 配置 + `dsh_model_pool_list`/`dsh_model_allowed` |
| `app/services/knowledge/entity_service.py` | `get_module_topology`（模块实体 + 双向关系聚合，L0 拓扑） |
| `app/api/v1/open_api.py` | 移除 Agent 查询面至 open_knowledge.py（保持 ≤20KB 守卫） |
| `app/api/v1/router.py` | 注册 open_knowledge |

### knowledge-mcp（仓库根新组件）

| 文件 | 内容 |
|------|------|
| `knowledge_mcp_server.py` | 12 个工具：search_knowledge / get_module_topology / get_knowledge_sources / get_requirements / get_test_cases / get_test_plans / get_test_plan / get_plan_executions / trigger_test_plan / get_execution_result / get_ui_test_jobs / trigger_ui_test / get_ui_test_run / submit_test_cases |
| `tests/test_knowledge_mcp.py` | 工具路径/参数/鉴权头单测 |
| `README.md` / `Dockerfile` / `.env.example` / `requirements.txt` | 部署与使用文档 |

### 前端（test-platform-v2/frontend）

| 文件 | 内容 |
|------|------|
| `src/api/dshTasks.ts` | `fetchDshModelPool` + `DshModelPool` 类型 |
| `src/pages/dsh-tasks/index.tsx` | 新建任务对话框：团队视角（dev/tester）下拉 + 模型池下拉 |
| `src/pages/dsh-tasks/__tests__/index.test.tsx` | 团队视角/模型池交互测试 |

### 测试与冒烟

- 后端：`test_tester_team_persona.py`（7）+ `test_open_api_knowledge.py`（19）+ `test_dsh_tasks.py` 团队/模型池/透传（+10）——相关域 198+ 全绿
- knowledge-mcp：16 用例全绿
- 前端：dsh-tasks 页 11 用例全绿 + typecheck 通过
- 端到端冒烟：MCP 客户端握手 8 工具注册 + 真实调用（拓扑/需求/用例/源/检索/用例回写）；阶段 2 全链路（计划列表→详情→触发→执行记录回读）

### 已知延后（非阻塞）

- `submit_defect`（缺陷回写）：缺陷模块对接待缺陷 API 契约确认
- 平台模板 ↔ DSH skill 映射（`get_skill_template`）：阶段 3 后续迭代
- 实例池 UI 工作台（内嵌 DSH Web）：复用 #282 dsh-headless 集成，待部署验收
