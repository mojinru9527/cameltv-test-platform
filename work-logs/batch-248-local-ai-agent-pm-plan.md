# Batch 248 — PM Plan

> **PM (🟨)** | Date: 2026-09-17

## 规格摘要
**原始需求**：PRD §1（平台零推理；AiJob 派发；本地 ChatGPT 客户端执行；平台展示与导入）
**目标时间**：1 个工作日内完成六部门流水线（不含发布）

## 开发任务

### [ ] Task 1: 配置开关与超时参数
**描述**: 新增 `ai_platform_inference`（默认 False）与 `ai_job_stale_seconds`（默认 300）。
**验收标准**: 环境变量可覆盖；默认值使平台不调用 LLM。
**涉及文件**: `test-platform-v2/backend/app/core/config.py` — 新增两个 setting
**参考**: PRD §5

### [ ] Task 2: Agent 凭据表与迁移
**描述**: 新增 `ai_agent_token` 表（agent_id/project_id/token_hash/token_prefix/enabled/last_used_at/revoked_at）+ Alembic 迁移（单头）。
**验收标准**: `alembic heads` 单头；升级/降级均可执行；PG 与 SQLite 语法兼容。
**涉及文件**: `app/models/ai_agent_token.py`（新）、`app/models/__init__.py`、`alembic/versions/20260922_ai_agent_token.py`（新）
**参考**: PRD US-3

### [ ] Task 3: AiJob 生产端（创建/查询）
**描述**: `create_job` / `list_jobs` / `get_job` 服务函数 + `POST /ai/jobs`、`GET /ai/jobs`、`GET /ai/jobs/{id}` 路由（项目隔离）。
**验收标准**: 跨项目读取返回 404（envelope code=404 + HTTP 200）；列表支持 status 过滤与分页。
**涉及文件**: `app/services/ai_agent_service.py`、`app/api/v1/ai_agent.py`
**参考**: PRD US-1/§5

### [ ] Task 4: Agent token 鉴权 + stale 回收
**描述**: register 返回一次性明文 token；claim/heartbeat/report 支持 `X-AI-Agent-Token`（保留 JWT 兼容）；claim 时回收心跳超时的 running 任务。
**验收标准**: 无 token/JWT → 401；禁用 token → 401；超时任务可被第二个 agent 认领。
**涉及文件**: `app/services/ai_agent_service.py`、`app/api/v1/ai_agent.py`、`app/core/deps.py`（如需新增依赖）
**参考**: PRD US-3/US-4

### [ ] Task 5: 需求拆分/生成切 AiJob
**描述**: `extract` / `extract-async` / `generate` / `generate-async` 在 `ai_platform_inference=False` 时创建 AiJob 并返回 `{job_id,status}`；`=True` 时保持旧行为。禁止 0 模块静默 confirmed。
**验收标准**: 关闭开关时 4 个端点均不 import 调用 ai_service；拆分结果为空时状态为 `pending_review`/`failed` 而非 `confirmed`。
**涉及文件**: `app/api/v1/requirement_ai.py`、`app/api/v1/requirement_ai_generate.py`
**参考**: PRD §1/§5

### [ ] Task 6: 结果导入用例库
**描述**: `POST /ai/jobs/{id}/import` 按 job_type（extract/generate）把结果写入需求文档模块/用例库，复用现有 import 逻辑；重复导入幂等。
**验收标准**: 首次导入返回 imported>0；重复导入 imported=0 且不新增用例。
**涉及文件**: `app/services/ai_agent_service.py`、`app/api/v1/ai_agent.py`、必要时 `app/services/requirement_service.py`
**参考**: PRD US-2

### [ ] Task 7: 本地 Agent CLI
**描述**: `scripts/ai_agent/cli.py`：`register | doctor | next | show | report | import`，默认 manual 模式（打印任务输入、接收结果 JSON 文件）。
**验收标准**: `--help` 可用；`doctor` 报告平台连通性与项目；`next` 无任务时优雅退出码 0。
**涉及文件**: `scripts/ai_agent/cli.py`（新）、`scripts/ai_agent/README.md`（新）、`docs/ai/local-ai-agent.md`（新）
**参考**: PRD US-1

### [ ] Task 8: 前端 AI 任务页
**描述**: `/ai-jobs` 路由：列表（状态筛选）+ 详情抽屉（输入/结果/模型名）+ 「导入用例库」+ Agent 在线状态；AI 配置页加入口。
**验收标准**: 四态齐全（loading/empty/error/正常）；非活跃不并发请求；错误提取链含 `detail`。
**涉及文件**: `src/pages/ai-jobs/index.tsx`（新）、`src/pages/ai-jobs/components/*`、`src/api/aiAgent.ts`（新）、路由注册、`src/pages/ai-config/index.tsx`
**参考**: Design Spec

### [ ] Task 9: 测试与守卫
**描述**: 后端 job 生命周期/鉴权/stale/导入测试；需求端点"不调用 LLM"守卫测试；CLI smoke；前端组件测试。
**验收标准**: 新增测试全绿；架构守卫新增断言通过。
**涉及文件**: `test-platform-v2/backend/tests/test_ai_local_agent_flow.py`（新）、`test-platform-v2/tests/test_execution_architecture_guard.py`（扩展）、`src/pages/ai-jobs/__tests__/`
**参考**: PRD §2

## 质量要求
- [x] 响应式（Desktop + Tablet）  - [x] OpenAPI 同步（FastAPI 自动）  - [x] 单元测试覆盖
- [x] 无障碍（ARIA/键盘）  - [x] 无 console 报错/告警
