# knowledge-mcp — 测试平台知识中心 MCP 服务器（DSH 测试 Agent 框架）

> 版本：v1.2 | 日期：2026-08-17 | 关联：`test-platform-v2/docs/DSH测试Agent框架设计.md`
>
> 把测试平台知识中心（骨架）暴露为 MCP 工具，供 DeepSeek Harness 测试船长团队
> （tester-team）查询项目知识、触发平台 Runner 执行、回写用例/缺陷。
> 仿照 `lanhu-mcp/` 的 FastMCP HTTP 模式与部署形态。

## 核心能力（17 工具）

| 工具面 | 工具 | 说明 |
|--------|------|------|
| 查询 | `search_knowledge(query, top_k?)` | RAG 混合检索（关键词+向量 RRF） |
| 查询 | `get_module_topology(module?)` | 模块拓扑：模块实体 + 挂接子实体（L0 骨架） |
| 查询 | `get_knowledge_sources(source_type?)` | 知识源列表（需求/接口/用例/缺陷/执行结果） |
| 查询 | `get_requirements(keyword?)` | 需求文档列表 |
| 查询 | `get_test_cases(module?, keyword?)` | 用例列表（含三关联元数据） |
| 执行 | `get_test_plans(status?, keyword?)` | 测试计划列表（api-tester 编排入口） |
| 执行 | `get_test_plan(plan_id)` | 测试计划详情（含用例清单） |
| 执行 | `get_plan_executions(plan_id)` | 计划执行记录（判定/回读） |
| 执行 | `trigger_test_plan(plan_id)` | 触发平台测试计划执行（API Runner） |
| 执行 | `get_execution_result(run_id)` | 查询执行结果 |
| 执行 | `get_ui_test_jobs(keyword?)` | UI 自动化任务列表（ui-tester 编排入口） |
| 执行 | `trigger_ui_test(job_id)` | 触发平台 UI 自动化任务 |
| 执行 | `get_ui_test_run(run_id)` | 查询 UI 测试运行状态与结果 |
| 回写 | `submit_test_cases(cases[])` | 用例直接入库（走 skill 规则产出） |
| 回写 | `submit_defect(defect)` | 缺陷直接入库（C-A4：自动沉淀知识中心缺陷源） |

> 完整工具面 17 个（查询 5 / 计划执行 5 / UI 执行 3 / 回写 2）。

## 启动方式

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境（.env 或环境变量）
#   PLATFORM_BASE_URL=http://127.0.0.1:8055      # 测试平台后端
#   PLATFORM_API_TOKEN=tpat_xxx                   # 平台 API Token（开放 API）
#   PLATFORM_PROJECT_ID=1                         # 项目 ID（X-Project-Id）

# 启动 MCP 服务器（HTTP 模式，默认端口 8110）
python knowledge_mcp_server.py
```

## MCP 连接配置

在 DSH / Claude Code / Cursor 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "knowledge": {
      "url": "http://localhost:8110/mcp"
    }
  }
}
```

## 鉴权

- 平台侧：API Token（`Authorization: Bearer tpat_xxx`）+ `X-Project-Id` 头
- 调用平台开放 API `/api/v1/open/*`（`verify_api_token` 校验，project 隔离）
- Token 在平台「开放 API」页面创建，最小权限建议 `read`+`write`

## 目录结构

```
knowledge-mcp/
├── knowledge_mcp_server.py   主服务入口（FastMCP HTTP）
├── requirements.txt          依赖
├── .env.example              环境变量模板
├── Dockerfile                Docker 部署
└── README.md                 本文档
```

## 与平台的关系

- 只经平台开放 API 通信，不直连数据库（遵守平台「路由禁 ORM」边界）
- 测试执行统一走平台 Runner（`POST /open/plans/{id}/trigger`），agent 不自跑测试环境
- 用例回写走 `POST /open/test-cases`（直接入库，规则单一事实源 = test-case-design skill）
