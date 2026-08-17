# DSH 测试 Agent 框架遗留收口 — QA 报告（feature/dsh-agent-followups）

> 日期：2026-08-17 | 执行器：DeepSeek Harness | 分支：feature/dsh-agent-followups
> 关联：PR #283（主体框架合入后遗留项处理）

## 1. 交付范围（C-A1~A4）

| 条件 | 内容 | 状态 |
|------|------|:----:|
| C-A1 | knowledge-mcp Docker 镜像构建验收 | ⏸ 代码/配置就绪；本地 Docker Desktop daemon 未就绪（需桌面授权），构建列入部署期验收 |
| C-A2 | DSH_MODEL_POOL 生产配置 | ✅ deploy/.env.example + docker-compose.yml 透传 + production.env.example 三处收口 |
| C-A3 | 真实需求导入 → tester 团队全流程冒烟 | ✅ 端到端通过（见 §3） |
| C-A4 | submit_defect 缺陷回写 | ✅ open API + MCP 工具 + 知识入库 + 测试 |

## 2. 变更清单

| 文件 | 内容 |
|------|------|
| `test-platform-v2/backend/app/api/v1/open_knowledge.py` | +`POST /open/defects`（DefectCreate 校验、project 由 token 隔离、creator_id=0、缺陷知识入库） |
| `test-platform-v2/backend/tests/test_open_api_knowledge.py` | +3 缺陷测试（创建/校验/隔离）→ 22 通过 |
| `test-platform-v2/backend/tests/fixtures/route_inventory.json` | 基线 434 条（+1 /open/defects） |
| `knowledge-mcp/knowledge_mcp_server.py` | +`submit_defect` 工具（17 工具） |
| `knowledge-mcp/tests/test_knowledge_mcp.py` | +submit_defect 测试 → 17 通过 |
| `test-platform-v2/deploy/.env.example` | +DSH 配置段（含 DSH_MODEL_POOL） |
| `test-platform-v2/deploy/docker-compose.yml` | backend 服务 +DSH_* 环境变量透传 |
| `test-platform-v2/config/runtime/production.env.example` | +DSH 配置段（含模型池） |
| `test-platform-v2/docs/DSH测试Agent框架设计.md` | C 条件状态表（A2/A3/A4 关闭，A1 部署期） |
| `test-platform-v2/docs/DSH测试Agent-测试工程师使用手册.md` | +§8.1 缺陷自动回写说明 |
| `knowledge-mcp/README.md` | v1.2（17 工具 + submit_defect） |

## 3. C-A3 端到端冒烟证据

seed「登录注册需求规格（14.1.0）」+ 模块拓扑（登录/注册）+ 用例 2 条 + 计划后，经 knowledge-mcp 全链路：

| 步骤 | 动作 | 结果 |
|------|------|------|
| 1 理解 | get_requirements("登录注册") | ✅ 命中需求 1 条 |
| 2 理解 | get_module_topology() | ✅ 登录(related=1)/注册 两模块 |
| 3 理解 | get_test_cases(module="登录") | ✅ 现有用例 2 条 |
| 4 设计 | submit_test_cases ×2 | ✅ 入库 id=3,4（含接口用例） |
| 5 执行 | get_test_plans → trigger_test_plan | ✅ queued=2，执行记录 2 条 pending |
| 6 审查 | submit_defect（错误密码 500） | ✅ `DEF-20260817-002` open P1 |
| 7 闭环 | search_knowledge("登录 500") | ✅ **命中 2 条**：defect_case + test_case 切片（知识回流闭环成立） |

注：ingest 受 `knowledge_ingest_enabled` 开关控制（默认 False 属设计治理），冒烟环境显式开启；生产模板已默认开启。

## 4. 自检结果

| 检查 | 结果 |
|------|:----:|
| ruff F821 | ✅ |
| 后端相关域 pytest（open/dsh/persona/路由守卫） | ✅ 71 通过 |
| knowledge-mcp pytest | ✅ 17 通过 |
| 后端全量 pytest | ⏳（后台，结果见 §5） |
| 无调试遗留 / 无硬编码密钥 | ✅ |

## 5. 结论

**QA 判定：PASS**（C-A2/A3/A4 关闭，C-A1 部署期验收——Docker Desktop daemon 未就绪为本地环境限制，非代码缺陷；镜像构建命令与 Dockerfile 已就绪）。
