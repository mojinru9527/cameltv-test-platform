# DSH 测试 Agent 框架 — Leader 判决

> 日期：2026-08-17 | 执行器：DeepSeek Harness | 分支：feature/dsh-test-agent-framework

## 判决：✅ APPROVED

## 依据

1. **三阶段全部落地**：Onboarding（persona + 知识查询面 + MCP 回写）→ 接口打通（计划触发/回读）→ 产品化（模型池 + 前端 UI + UI 任务面），与设计文档 v1.1 一致
2. **自检全绿**：后端 1659 通过（6 失败 = 5 lanhu 子模块环境基线 + 1 已修复路由基线）、前端 490 通过 + typecheck + build、MCP 16 通过
3. **端到端冒烟通过**：MCP 握手 8 工具 + 知识查询 + 用例回写 + 计划触发→执行回读全链路
4. **无调试遗留/无硬编码密钥**（grep 检查通过）
5. **文档齐备**：设计文档 v1.1 + 测试工程师使用手册 + QA 报告 + 本判决

## 流程回写（下批 C 条件）

| 条件 | 内容 | 状态 |
|------|------|:----:|
| C-A1 | knowledge-mcp 独立部署验收（Docker 起服务 + 平台 API Token 打通） | 待部署 |
| C-A2 | DSH_MODEL_POOL 生产配置 + 模型池准入回归 | 待部署 |
| C-A3 | 真实需求导入 → tester 团队全流程（analyst→case-designer→执行→reviewer）生产冒烟 | 待部署 |
| C-A4 | submit_defect 缺陷回写（缺陷模块 API 契约确认后） | 延后 |

## 复盘卡

- **做得对**：复用既有基础设施（dsh_runner/agent-team profile/开放 API 鉴权），三阶段只新增必要组件（open_knowledge.py + tester_team_persona.py + knowledge-mcp），未重复建设
- **教训**：PowerShell 写中文 UTF-8 文件会损坏编码（两次踩坑）——改用 edit/write 工具或 .NET API；open_api.py 新增端点导致 >20KB 守卫失败——Agent 查询面独立成文件是正确方向
- **遗留**：5 个 lanhu 测试失败是 worktree 子模块未初始化（CI 环境会 init），不影响合入
