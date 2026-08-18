# 设计：AI 模型配置中心 + DSH 测试入口 + 知识中心 tab 修复

> 日期：2026-08-18 | 状态：设计已批准（用户确认全部决策点） | 批次模式：完整批次（A/B 分批次执行，C 可轻量）
> 执行器：DeepSeek_Harness | 范围：test-platform-v2 backend + frontend + docs + 测试

## 1. 背景与目标

用户 4 点诉求：

1. **AI 模型配置入口缺失**：测试平台没有切换模型/输入 KEY 的入口（对比 DeepSeek Harness 设置的
   提供方 + Key + API 地址方式）；配置应适用于整个测试平台所有用到 AI 模型和 key 的地方。
2. **DSH 任务模块定位提升**：应做成与知识中心同级的关键入口，最终可通过 DSH 直接使用测试平台。
3. **测试同学场景适配**：通过该模块导入需求、生成测试用例、接口用例、UI 自动化用例。
4. **知识中心 tab 拼接 bug**：切换 tab 时内容仍拼接在概览 tab 数据下方。

**目标**：三个子项目（A 配置中心 / B DSH 测试入口 / C tab 修复），按 C → A → B（B1→B2→B3）顺序交付。

## 2. 现状盘点（探索结论）

| 项 | 现状 |
|----|------|
| AI 配置 | 全部走 `.env`：`AI_API_KEY/AI_API_BASE_URL/AI_MODEL`（通用）+ `DSH_API_KEY/DSH_BASE_URL/DSH_MODEL/DSH_MODEL_POOL`（DSH）。无任何 UI 配置入口 |
| AI 消费点 | 8 处服务读 `settings.ai_*`：ai_service（用例生成）、case_compiler、triage_service（缺陷分类）、knowledge/llm_json_client、knowledge/agent_orchestrator、knowledge/skill_service、api_generalization_service（接口用例泛化）、dsh_runner（注入 DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL/DSH_MODEL 环境变量） |
| DSH 任务模块 | `dsh_task` 表 + `dsh_task_service`（submit/list/get/cancel，Batch 181 认领锁）+ `dsh_runner`（node CLI / python-sdk 双运行时，Batch 184 沙箱）+ `/api/v1/dsh-tasks/*`（权限 agent:view/agent:run）+ 前端一页（列表+新建对话框+详情侧栏，Batch 191 团队模式 team_json 进度树，Batch 202 tester 视角 persona + 模型池下拉） |
| 测试 Agent 基础 | Batch 202：`tester_team_persona.py`（analyst/case-designer/api-tester/ui-tester/reviewer 五成员）、`open_knowledge.py`（知识源/检索/需求/用例读+写/计划/执行/UI 任务，API Token 鉴权 + project 隔离）、`docs/DSH测试Agent-测试工程师使用手册.md` |
| 产物审核机制 | `AiArtifact`（review_status pending/approved/rejected）+ `artifact_service`（仅 approved 可导入 TestCase，未审核不得进正式库）+ `knowledge:approve` 权限 + 前端「AI 审核台」Tab |
| 需求导入 | requirement 模块已有文档上传/URL 抓取/功能拆分确认流（requirement_docs / requirement_ai） |
| 知识中心 tab | Radix Tabs + `forceMount={visitedTabs.has(x) ? true : undefined}`（Batch 155 引入状态保留）；理论上非活动 tab 由 Radix 加 `hidden` 隐藏，用户实际看到拼接 → 需复现确认根因 |

## 3. 决策记录（用户逐项确认）

| 决策点 | 结论 |
|--------|------|
| 配置归属层级 | **项目级**（每个项目自己的配置） |
| 配置形态 | **多提供方池**（每项目可配多个 provider，生成/任务时选择） |
| 未配置行为 | **无配置即禁用 AI**（严格隔离，不自动回退 env） |
| 全局默认 | **纯项目级，无全局概念**（env 中 AI/DSH 凭据类配置退役） |
| DSH 入口形态 | **场景卡片 + 分步向导** |
| 产物落库 | **先进知识中心 AI 审核台草稿，人工确认后导入正式库** |
| 深链 | **全量深链**（需求详情/接口资产/UI 用例/用例库页加入口按钮） |
| 实施顺序 | C → A → B（B1 向导 → B2 产物闭环 → B3 深链） |

## 4. 子项目 A：AI 模型配置中心

### 4.1 数据模型（新增 `ai_provider` 表，项目级）

```python
class AiProvider(Base, TimestampMixin):
    project_id: int          # 索引；项目隔离
    name: str                # 展示名（如 "DeepSeek 官方"）
    provider_type: str       # deepseek_official | openai_compatible
    api_base_url: str        # OpenAI 兼容端点；deepseek_official 预置 https://api.deepseek.com
    api_key_encrypted: str   # Fernet 加密（密钥从 SECRET_KEY 派生），绝不落明文
    models: str              # JSON 数组（模型清单）
    default_model: str
    is_default: bool         # 每项目至多一个默认提供方
    enabled: bool
```

- Alembic 迁移；key 加密用 `cryptography.Fernet`，密钥 = `SECRET_KEY` 派生（已有依赖评估：cryptography 已在 requirements）。
- 列表/详情 API 只返回掩码 `sk-****{尾4}`；更新时 key 留空 = 不变。

### 4.2 配置解析层（核心改造）

新增 `ai_config_service.resolve(project_id) -> EffectiveAiConfig`（含 provider 字段 + `effective_api_key()` 解密 + `to_runner_env()`）。

- **8 处消费点**从"读 `settings.ai_*`"改为"先 resolve 项目配置"；项目无配置 → 返回明确业务错误
  （如 `code=400, msg="当前项目未配置 AI 提供方，请在 AI 配置中设置"`），对应前端入口 disabled + 引导。
- 消费点签名补 `project_id` 透传（路由层已有 `current.project_id`，主要是服务层参数化）。
- **dsh_runner**：`DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DSH_MODEL` 改为由任务提交时绑定的项目
  provider 注入（提交 DSH 任务时快照 provider_id 到任务参数，避免执行时配置变更影响在跑任务）。

### 4.3 API（`/api/v1/ai-config/*`）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/providers` | GET | 当前项目 provider 列表（掩码 key） |
| `/providers` | POST | 新建（body 含 key） |
| `/providers/{id}` | PUT | 更新（key 留空不变） |
| `/providers/{id}` | DELETE | 删除（默认项禁止删或转移默认） |
| `/providers/{id}/test-connection` | POST | 后端 httpx 实测连通 + 模型可达（用该 provider 发一次最小请求） |
| `/resolve` | GET | 当前项目生效配置（前端展示/各模块查询） |

权限：新权限点 `ai_config:manage`（项目数据范围，管理员角色拥有）；测试角色只读列表（无 key）。

### 4.4 前端

- 新增「AI 配置」菜单：**项目级菜单区**（侧边栏与知识中心/DSH任务同级，项目切换后按项目隔离展示）；
  provider 列表 + 新建/编辑表单（类型、地址、key、模型清单 tags 输入、默认模型、设为默认、测试连接
  按钮）+ 未配置引导横幅。
- 各 AI 功能入口（生成用例/需求分析/审核台等）在项目无配置时 disabled，提示"当前项目未配置 AI 提供方，去配置"。
- DSH 任务页顶部状态条新增 AI 配置状态（已配置·{默认 provider 名} / 未配置→引导）。

### 4.5 env 退役边界

- **退役**：`AI_API_KEY / AI_API_BASE_URL / AI_MODEL / DSH_API_KEY / DSH_BASE_URL / DSH_MODEL / DSH_MODEL_POOL`。
- **保留**：部署基础设施 `DSH_ENABLED / DSH_RUNTIME / DSH_HARNESS_PATH / DSH_SESSION_ROOT / DSH_TIMEOUT_* / DSH_MAX_* / DSH_TEAM_*`。
- 迁移：现有环境由项目管理员把旧 env 值填入项目配置（一次性成本）。`.env.example` 与 CLAUDE.md 同步更新。

## 5. 子项目 B：DSH 测试入口

### 5.1 页面结构（dsh-tasks 页升级）

```
┌─ 顶部状态条 ────────────────────────────────┐
│ [DSH 可用] [AI 配置: 已配置·DeepSeek官方] [刷新] │
├─ 场景卡片区（新增）───────────────────────────┤
│ [导入需求] [功能用例] [接口用例] [UI自动化] [通用任务] │
├─ 任务列表（保留增强）──────────────────────────┤
│ 状态 + 场景标签 + 产物列（N 条待审核 → 跳审核台）    │
└────────────────────────────────────────────┘
详情侧栏增强：执行输出 + 产物链接（审核台条目/正式库条目）
```

### 5.2 分步向导（共享 `SceneWizard` 组件，Dialog 3 步）

| 步骤 | 内容 |
|------|------|
| 1 输入 | 因场景而异（见 5.3） |
| 2 配置 | AI 提供方（项目池下拉，默认预选）+ 模型 + 任务模式（默认团队·测试视角，可切标准）+ 批次（团队模式） |
| 3 提交 | 场景模板生成的任务描述（可编辑）+ 提交 |

### 5.3 五个场景

| 场景 | 输入 | 输出 | 产物 |
|------|------|------|------|
| 导入需求 | 粘贴文本 / URL / 上传文档 | 需求分析与功能模块拆分 | 需求产物 → 审核台 → 确认入需求库 |
| 生成功能用例 | 选已有需求 或 粘贴需求 | 功能用例（test-case-design skill 标准） | 用例产物 → 审核台 → 确认入 test_case 库 |
| 生成接口用例 | 选接口资产 / 粘贴 OpenAPI | 接口用例（断言/边界/异常） | 用例产物 → 审核台 → 确认入接口用例库 |
| 生成 UI 自动化用例 | 选功能用例/需求 + 目标页面 | UI 用例/脚本草案 | 用例产物 → 审核台 → 确认入 UI 用例库 |
| 通用任务 | 自由文本（保留现状） | 自由 | 不进审核台 |

场景模板 = 前端预置中文 prompt 模板（内联输入 + tester 五成员 persona 职责引用），提交前用户可见可改。

### 5.4 产物闭环（核心机制）

```
DSH 团队执行完成
  → 后端解析结果（结构化 JSON 产物清单，persona 提示词约束输出契约）
  → 写 AiArtifact（pending，source=dsh_task:{id} 溯源）
  → 知识中心「AI 审核台」出现待审条目
  → approve → 按产物类型导入正式库（需求/功能用例/接口用例/UI 用例）
  → 任务详情回链：任务 → 审核条目 → 正式库条目
```

- 复用 `AiArtifact` + `artifact_service`（已有"未审核不得进正式库"守卫），扩展产物类型与多目标库映射。
- 审核权限沿用 `knowledge:approve`。
- 解析失败兜底：产物进"待解析"状态，人工在任务详情查看原始输出。

### 5.5 全量深链

- 需求详情页：「用 DSH 生成功能用例」→ 向导预锁需求
- 接口资产页：「用 DSH 生成接口用例」→ 向导预选接口
- UI 自动化页：「用 DSH 生成 UI 自动化用例」→ 向导预选目标
- 用例库页：「用 DSH 补充用例」→ 向导预带模块上下文
- 实现：共享 SceneWizard + URL 深链参数（`/dsh-tasks?scene=functional&requirement_id=12`）

### 5.6 改造清单与子阶段

**后端**：`/dsh-tasks` 提交扩展 scene + 结构化输入（场景参数 + provider 快照）；任务产物查询 API；
`dsh_artifact_service`（结果解析 → AiArtifact）；tester persona 补结构化输出契约（结尾附 JSON 产物清单）。

**前端**：dsh-tasks 页重构（卡片区 + 列表增强）；SceneWizard 共享组件；深链解析 hook；各页面按钮。

**子阶段**（各自独立 PR）：
- B1 场景向导 + 任务页重构（产物先留在任务详情展示，不落库）
- B2 产物闭环（解析 → 审核台 → 导入正式库）
- B3 全量深链 + 各页面按钮

### 5.7 风险

1. 结构化输出契约依赖 persona 提示词约束 → 解析失败兜底"待解析"人工处理。
2. 多目标库导入映射（功能/接口/UI 三类 target 类型扩展）→ 审核台/artifact_service 扩展点预留。
3. 长任务（团队 1800s）向导停留体验 → 提交后关闭进入列表轮询（现状已有）。

## 6. 子项目 C：知识中心 tab 拼接修复

1. **复现确认**：本地起前后端实际切换 tab 验证 DOM/可见性；确认用户所看环境（本地/test 部署构建版本）。
2. **修复**（按根因选一）：
   - `hidden` 未生效 → 改条件渲染（`tab === 'x' && <Tab/>`）或非活动 TabsContent 显式加 hidden class；
   - 需保留 tab 状态 → "保留但显式隐藏"方案 + 交互回归测试防复发。

## 7. 交付物与测试策略

| 子项目 | 后端 | 前端 | 测试 |
|--------|------|------|------|
| A | ai_provider 模型+迁移、ai_config_service、8 处消费点改造、CRUD+test-connection、权限点 | AI 配置页、各 AI 入口未配置引导 | pytest（解析/加密/权限/无配置禁用）+ 受影响模块回归 |
| B | scene 提交扩展、产物解析→AiArtifact、查询 API、persona 输出契约 | 任务页重构、SceneWizard、深链、审核台产物展示 | pytest（提交/解析/导入守卫）+ 前端向导 vitest |
| C | — | index.tsx 修复 | 交互回归测试 |

门禁（AGENTS.md §3）：后端 `ruff --select F821` + 受影响模块 pytest；前端 `npm run typecheck && npm run build` + 受影响 vitest；全量回归记录；独立 worktree + 功能分支 + Draft PR + audit-ai-pr。

文档保鲜：CLAUDE.md（config 章节、AI 配置说明）、`.env.example`、`docs/DSH测试Agent-测试工程师使用手册.md` 更新；如引入架构级决策补充 ADR。

## 8. 实施顺序

C（小快）→ A（B 的基础）→ B：B1 场景向导+任务页重构 → B2 产物闭环 → B3 全量深链。

## 9. 待办/确认项

- [ ] C 复现确认：本地验证 + 确认用户查看环境构建版本
- [ ] A：Fernet 密钥派生方案复核（SECRET_KEY 轮换策略）
- [ ] B：persona 结构化输出契约草案（含解析失败兜底样例）
