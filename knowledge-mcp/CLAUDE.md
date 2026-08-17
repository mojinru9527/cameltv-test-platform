---
title: "knowledge-mcp — 知识中心 MCP 服务器"
owner: "qa-team"
last_reviewed: "2026-08-17"
status: "active"
expires: "2027-02-17"
tags: ["mcp", "knowledge-center", "dsh", "agent"]
related: ["test-platform-v2/docs/DSH测试Agent框架设计.md", "test-platform-v2/docs/DSH测试Agent-测试工程师使用手册.md", "../lanhu-mcp/CLAUDE.md"]
---

# knowledge-mcp — 知识中心 MCP 服务器

> 将测试平台知识中心（项目知识拓扑/用例/需求/计划）暴露为 MCP 工具，
> 供 DeepSeek Harness 测试船长团队（tester-team）查询、触发执行、回写用例。
> 仿照 lanhu-mcp 的 FastMCP HTTP 模式（path=/mcp，端口 8110）。

## 技术栈

- 运行时：Python 3.12+
- 框架：FastMCP（HTTP 模式）
- 通信：httpx → 平台开放 API（`/api/v1/open/*`，API Token 鉴权 + X-Project-Id 隔离）

## 核心能力（16 工具）

| 面 | 工具 |
|----|------|
| 查询 | `search_knowledge` / `get_module_topology` / `get_knowledge_sources` / `get_requirements` / `get_test_cases` |
| 计划执行 | `get_test_plans` / `get_test_plan` / `get_plan_executions` / `trigger_test_plan` / `get_execution_result` |
| UI 执行 | `get_ui_test_jobs` / `trigger_ui_test` / `get_ui_test_run` |
| 回写 | `submit_test_cases`（直接入库，走 test-case-design skill 规则） |

## 目录结构

```
knowledge-mcp/
├── knowledge_mcp_server.py   主服务入口（FastMCP HTTP，path=/mcp）
├── requirements.txt          fastmcp / httpx / python-dotenv
├── tests/test_knowledge_mcp.py   工具路径/参数/鉴权头单测
├── .env.example              PLATFORM_BASE_URL / API_TOKEN / PROJECT_ID / MCP_PORT
├── Dockerfile
└── README.md                 部署与连接配置
```

## 启动方式

```bash
pip install -r requirements.txt
# .env 配 PLATFORM_BASE_URL / PLATFORM_API_TOKEN / PLATFORM_PROJECT_ID
python knowledge_mcp_server.py   # HTTP 模式，默认 0.0.0.0:8110/mcp
```

## 开发约定

- **只经平台开放 API 通信，不直连数据库**（遵守平台「路由禁 ORM」边界）
- 新增工具 = 平台 open API 先有端点，再在 `_call` 之上薄封装（不加业务逻辑）
- 测试：`tests/` 打桩 `_call` 验证路径/参数/鉴权头（不连真实平台）
- 平台侧对应文件：`test-platform-v2/backend/app/api/v1/open_knowledge.py`
  （路由层禁 ORM 由后端守卫测试强制）

## 与测试平台的集成

- DSH 测试船长团队经 MCP 工具：熟悉项目（拓扑/需求/用例）→ 设计用例（回写入库）→
  触发平台 Runner（计划/UI）→ 回读结果 → 报告
- 用例生成规则单一事实源 = `tests/test-case-standards/` + `.agents/skills/test-case-design/`
- 架构与使用见 `test-platform-v2/docs/DSH测试Agent框架设计.md` 与
  `test-platform-v2/docs/DSH测试Agent-测试工程师使用手册.md`
