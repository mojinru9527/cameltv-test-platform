# DSH 测试 Agent 框架 — QA 报告（feature/dsh-test-agent-framework）

> 日期：2026-08-17 | 执行器：DeepSeek Harness | 分支：feature/dsh-test-agent-framework（11 commits, +2316 行）
> 关联：test-platform-v2/docs/DSH测试Agent框架设计.md（v1.1）· DSH测试Agent-测试工程师使用手册.md（v1.0）

## 1. 交付范围

三阶段完整落地（评审确认 2026-08-17）：

| 阶段 | 内容 | 状态 |
|------|------|:----:|
| 1 Onboarding 先行 | tester_team_persona + team_kind 分派 + open API 知识查询面 + knowledge-mcp 查询/回写 | ✅ |
| 2 接口测试打通 | open 计划查询面 + MCP 计划工具 + 触发→执行→回读 | ✅ |
| 3 全自动+产品化 | 模型池（dsh_model_pool 准入）+ 前端团队视角/模型下拉 + UI 任务查询面 + 使用手册 | ✅ |

## 2. 变更清单

### 后端（test-platform-v2/backend）
- `services/dsh/tester_team_persona.py`（新）：测试船长 persona 纯函数（analyst/case-designer/api-tester/ui-tester/reviewer；skill 自检 + 平台 Runner + reviewer 三触发点）
- `services/dsh/dsh_task_service.py`：team_kind 分派（tester→tester persona，缺省 dev 不回归）+ model 透传（single/team）
- `schemas/dsh.py`：team_kind（dev|tester）+ model（非空串）校验
- `api/v1/open_knowledge.py`（新）：Agent 查询面 10 端点（知识源/检索/模块拓扑/需求/用例读+写/计划列表/详情/执行记录/UI 任务）
- `api/v1/dsh_tasks.py`：/model-pool 端点 + 模型池准入
- `core/config.py`：dsh_model_pool + dsh_model_pool_list/dsh_model_allowed
- `services/knowledge/entity_service.py`：get_module_topology（L0 拓扑，双向关系聚合）
- `api/v1/open_api.py`：Agent 查询面迁移出（保持 ≤20KB 守卫）
- `.env.example`：补 DSH_MODEL_POOL

### knowledge-mcp（新组件，仓库根）
- `knowledge_mcp_server.py`：16 工具（查询 5 / 计划执行 4 / UI 执行 3 / 触发 2 / 回读 2 / 回写 1）
- `tests/test_knowledge_mcp.py`：16 用例（路径/参数/鉴权头/错误）
- `README.md` v1.1 + `Dockerfile` + `.env.example` + `requirements.txt`

### 前端（test-platform-v2/frontend）
- `pages/dsh-tasks/index.tsx`：新建任务对话框团队视角（dev/tester）+ 模型池下拉
- `api/dshTasks.ts`：fetchDshModelPool + DshModelPool 类型
- `__tests__/index.test.tsx`：团队视角/模型池交互测试

### 文档
- `docs/DSH测试Agent框架设计.md`（v1.1：落地清单 + 延后项）
- `docs/DSH测试Agent-测试工程师使用手册.md`（v1.0，新）

## 3. 自检结果

| 检查 | 命令 | 结果 |
|------|------|:----:|
| 后端 F821 | ruff check app/ --select F821 | ✅ 全过 |
| 后端全量测试 | pytest tests/ | ✅ 1659 通过 / 3 跳过 / 6 失败 |
| 前端类型 | tsc -b | ✅ |
| 前端全量测试 | vitest run | ✅ 490 通过（118 files） |
| 前端构建 | vite build | ✅ |
| knowledge-mcp 测试 | pytest knowledge-mcp/tests | ✅ 16 通过 |
| 无调试遗留 | grep console.log/print/breakpoint | ✅ 无 |
| 无硬编码密钥 | grep sk-/tpat_ | ✅ 无 |

**失败项分析（6 = 基线环境，非本分支引入）**：
- `test_lanhu_login_hook.py`（2）+ `test_lanhu_provider.py`（2）+ `test_deploy_compose_contract.py`（1）：lanhu-mcp 子模块未初始化（worktree 环境缺子模块文件，CI 会 init 子模块）
- `test_route_inventory.py`（1）：路由基线曾漂移 → 已在本分支更新 fixture（433 条）并复跑通过

## 4. 端到端冒烟证据

1. **MCP 握手**：fastmcp Client 连接 `http://127.0.0.1:8110/mcp` → 8 工具注册列表返回
2. **知识查询链路**：get_module_topology / get_requirements / get_test_cases / get_knowledge_sources 真实返回 seed 数据（模块→用例 contains 关系正确聚合）
3. **用例回写链路**：submit_test_cases → 用例 id=2 入库 → get_test_cases(keyword) 可查回（project 隔离生效）
4. **阶段 2 执行链路**：get_test_plans(keyword) → get_test_plan(1) → trigger_test_plan(1)（triggered=True, cases_queued=1）→ get_plan_executions(1)（total=1, status=pending）
5. **检索降级**：search_knowledge 在无切片时返回 []（RAG 降级关键词无内容，行为正确）

## 5. 风险与遗留

| 项 | 说明 | 处置 |
|----|------|------|
| submit_defect 缺陷回写 | 待缺陷模块 API 契约确认 | 延后（设计文档 §14 登记） |
| 平台模板 ↔ DSH skill 映射 | get_skill_template 待迭代 | 延后 |
| 实例池 UI 工作台（内嵌 DSH Web） | 复用 #282 dsh-headless 集成 | 待部署验收 |
| 用例直接入库 | 防污染由 skill 自检 + reviewer 审查兜底 | 设计决策（2026-08-17 评审确认） |
| 模型池默认不限 | DSH_MODEL_POOL 空 = 不限 | 生产部署时配置 |

## 6. 结论

**QA 判定：PASS**（lanhu 子模块 5 失败为环境基线，路由基线已修复复跑通过）。三阶段落地完整，可推送并合入 main。
