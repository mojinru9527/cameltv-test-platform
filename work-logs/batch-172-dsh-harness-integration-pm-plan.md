# Batch 172 — PM Plan
> **PM (🟨)** | Date: 2026-08-13 | Executor: codex

## 规格摘要
**原始需求**: PRD §4 — A 用例生成 harness 模式 / B Agent 工作台执行型 Agent / C DSH 任务执行模块。
**目标时间**: 本批内完成三阶段（Slice 1→5），每 Slice 独立提交。

## 开发任务

### Slice 1 — DSH 运行时抽象 + 配置（A/B/C 公共底座）
- [ ] Task 1.1: 配置
  **描述**: `app/core/config.py` 新增 `dsh_*` 设置：`dsh_enabled`、`dsh_runtime`(node|python-sdk)、`dsh_model`、`dsh_base_url`、`dsh_session_root`、`dsh_timeout`、`dsh_harness_path`、`dsh_max_output_chars`；提供 `dsh_available()` 校验（enabled + 凭据/路径）。
  **验收标准**: settings 读取无报错；未配置时 `dsh_available()=False` 且原因可读。
  **涉及文件**: `test-platform-v2/backend/app/core/config.py`
  **参考**: PRD §5 技术考量
- [ ] Task 1.2: DSH Runner 抽象服务
  **描述**: 新建 `app/services/dsh/dsh_runner.py`：统一 `run_dsh_task(task, workspace, session_root, model, timeout) -> DshRunResult(final_response, exit_code, error, session_dir)`。
  - `dsh_runtime=python-sdk`：`pip install deepseek-harness-sdk`（锁版本）走 `DeepSeekHarness`（Linux 生产）。
  - `dsh_runtime=node`：子进程调用 Node CLI headless（`dsh --profile headless`，Windows 本地开发），带超时 kill。
  - 依赖注入便于单测 mock；`runtime_available()` 健康检查。
  **验收标准**: mock 下 run 返回结构化结果；真实 node runtime 在本地可执行一次只读任务（QA 阶段验证）。
  **涉及文件**: `test-platform-v2/backend/app/services/dsh/__init__.py`、`dsh_runner.py`；`requirements.lock`（python-sdk 锁版本，如启用）
  **参考**: PRD §5

### Slice 2 — A: AI 用例生成 harness 模式
- [ ] Task 2.1: `ai_service.py` harness 模式
  **描述**: `generate_cases`/`review_cases` 增加 `use_harness: bool = False` 与读取 `settings.dsh_enabled`；启用时经 `dsh_runner` 执行「按 tests/test-case-standards 规范生成用例 + 自校验 schema」任务，输出转成与现格式一致的用例 JSON；解析失败降级到直连模式并记录 warning。**默认 False，现有行为不变**。
  **验收标准**: 未开启时输出与现状逐字节一致（回归）；开启时 mock runner 返回用例被正确转换；schema 校验通过。
  **涉及文件**: `app/services/ai_service.py`、`app/services/dsh/dsh_runner.py`
  **参考**: PRD §4 用户故事 A；test-case-design skill
- [ ] Task 2.2: 异步链路透传
  **描述**: `app/services/ai_tasks.py` 的 generate 分支按 `settings.dsh_enabled` 选择 harness 模式并持久化 result_json。
  **验收标准**: AiTask 状态流转正常；result 结构与现一致。
  **涉及文件**: `app/services/ai_tasks.py`
- [ ] Task 2.3: 单测
  **描述**: `backend/tests/` 新增 harness 模式单测（mock runner）：开/关行为、schema 转换、降级。
  **验收标准**: `pytest` 相关用例全绿。

### Slice 3 — B: Agent 工作台执行型 Agent
- [ ] Task 3.1: 新增 agent 类型
  **描述**: `app/services/knowledge/agent_prompts.py` 的 `AGENT_META` 新增 `dsh_execution`（label「DSH 执行」、artifact_type `dsh_execution`）。
  **验收标准**: `GET /api/v1/agents/types` 返回新类型且 `available` 随 `dsh_available()`。
  **涉及文件**: `app/services/knowledge/agent_prompts.py`、`app/api/v1/agent.py`（unavailable_reason 扩展）
- [ ] Task 3.2: orchestrator 分发执行
  **描述**: `app/services/knowledge/agent_orchestrator.py`：`agent_type == "dsh_execution"` 时走 dsh_runner（用户输入即任务文本），不走 RAG+LLM；start_run/finish_run 记录 output/error 到 AiArtifact（复用现有持久化）。
  **验收标准**: 触发后队列→执行→runs 记录含 status/output/log；失败原因可查。
  **涉及文件**: `app/services/knowledge/agent_orchestrator.py`
- [ ] Task 3.3: 前端入口与详情
  **描述**: `frontend/src/pages/agent-workbench/index.tsx` 增加「DSH 执行」触发入口（输入任务文本→POST /agents/run/dsh_execution→轮询 runs）与执行结果展示（输出/状态/错误）。
  **验收标准**: 页面可触发并可看到执行记录详情；无 console 报错。
  **涉及文件**: `frontend/src/pages/agent-workbench/index.tsx`、`frontend/src/api/`
- [ ] Task 3.4: 单测
  **描述**: orchestrator 分发单测（mock runner 成功/失败）。
  **验收标准**: `pytest` 相关用例全绿。

### Slice 4 — C: DSH 任务执行模块
- [ ] Task 4.1: 模型 + 迁移
  **描述**: 新建 `app/models/dsh_task.py`（`DshTask`：id/project_id/task/status/params_json/output_text/session_dir/error/operator_id/时间戳，status=pending|running|success|failed|cancelled）+ Alembic 迁移。
  **验收标准**: `alembic upgrade head` 单头通过；模型注册到 `app/models/__init__.py`。
  **涉及文件**: `app/models/dsh_task.py`、`app/models/__init__.py`、`alembic/versions/`
- [ ] Task 4.2: 服务
  **描述**: `app/services/dsh/dsh_task_service.py`：提交（插 pending + 唤醒 worker）、认领、执行（dsh_runner）、回写状态/输出/错误；worker 复用 `ai_tasks.py` 线程/DB 认领模式。
  **验收标准**: 状态流转与并发认领正确；超时/失败落 error。
  **涉及文件**: `app/services/dsh/dsh_task_service.py`
- [ ] Task 4.3: API
  **描述**: `app/api/v1/dsh_tasks.py`：`POST /dsh-tasks`（触发）、`GET /dsh-tasks`（列表，分页/状态过滤）、`GET /dsh-tasks/{id}`（详情）、`POST /dsh-tasks/{id}/cancel`；权限复用 `agent:run`/`agent:view`；注册进 `router.py`；schema 进 `app/schemas/dsh.py`。
  **验收标准**: OpenAPI 生成正常；权限校验生效；项目隔离（只能看本项目任务）。
  **涉及文件**: `app/api/v1/dsh_tasks.py`、`app/api/v1/router.py`、`app/schemas/dsh.py`
- [ ] Task 4.4: 前端模块
  **描述**: `frontend/src/pages/dsh-tasks/index.tsx` 列表+详情+新建（任务文本）+状态轮询；路由注册；侧边栏菜单「DSH 任务」。
  **验收标准**: 页面可用；提交→状态流转→结果展示；空态/加载态/错误态齐全；响应式。
  **涉及文件**: `frontend/src/pages/dsh-tasks/index.tsx`、`frontend/src/router/`、`frontend/src/components/`(菜单)
- [ ] Task 4.5: 单测/回归
  **描述**: service/API 单测 + 前端组件测试。
  **验收标准**: 后端 `pytest`、前端 `vitest` 相关用例全绿。

### Slice 5 — 文档 + 全量回归
- [ ] Task 5.1: 文档
  **描述**: `docs/adr/` 新增 DSH 集成 ADR（运行时选择/版本锁定/成本控制）；`test-platform-v2/README.md` 与 `CLAUDE.md` 增补 dsh 配置说明；`.env.example` 增补 DSH_* 项。
  **验收标准**: 文档与实际配置一致。
  **涉及文件**: `docs/adr/00xx-dsh-harness-integration.md`、`test-platform-v2/README.md`、`test-platform-v2/backend/.env.example`、`test-platform-v2/backend/CLAUDE.md`
- [ ] Task 5.2: 全量回归
  **描述**: 后端 `pytest` 全量、前端 `npm test`、`npm run typecheck && npm run build`、`ruff check app --select F821`；记录基线与本分支失败集合。
  **验收标准**: 无新增失败；硬门禁全绿。

## 质量要求
- [ ] OpenAPI schema 与实现同步（新增/变更 API）
- [ ] 单元测试覆盖 A/B/C 核心逻辑
- [ ] 无 console.log / print / debugger 调试残留
- [ ] 响应式（Desktop + Tablet）+ 无障碍（ARIA/键盘）
- [ ] 新配置无硬编码密钥；`.env.example` 同步
