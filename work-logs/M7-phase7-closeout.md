# M7（Phase 7：MCP Server + AGENTS 规整 + Skill 跨 Agent）收口报告

> **日期**：2026-11-12 · **范围**：TA-036 / TA-037 / TA-038（3 批）
> **结论**：M7 全部任务完成并合入 main；生产后端保持 `20261123`（112 表，health 200）。

## 1. 批次

| 批次 | TA | 内容 | PR |
|------|----|------|----|
| batch-320 | TA-036 | 内网 MCP Server（stdio JSON-RPC：initialize/list/call；写审批） | #549 |
| batch-321 | TA-037 | AGENTS.md AIQE 规范 + `check-agents-md.ps1` | #550 |
| batch-322 | TA-038 | Skill 跨 Agent（6 skill × 3 客户端契约校验） | #551 |

## 2. 交付物

- `scripts/mcp-server/aiqe_mcp/server.py` + `README.md`（Codex/Claude/Cursor 注册命令）；
- `AGENTS.md` §5.5：入口、门禁、MCP/Skill 使用；
- `docs/aiqe/skills.md`、`scripts/aiqe/skill-clients.json`、`verify-skill-compat.ps1`；
- 守卫：`AGENTS_GUARD=PASS`、`SKILL_COMPAT=PASS clients=3 skills=6`。

## 3. 测试

- 后端全量：**1647 passed / 43 skipped**（M7 新增 5 条 MCP server 测试）；
- 前端：560 passed（M7 未改前端）；
- ratchet PASS；MCP stdio initialize 冒烟通过。

## 4. 发布（tooling-only）

M7 不改变后端运行时、无新迁移，因此**不重建/重启生产镜像**：

| 项 | 结果 |
|----|------|
| 生产镜像 | `cameltv-tp-backend:main`（M6 `release-m6-20261112`） |
| 迁移 head | `20261123_ta033_mutation_ledger` |
| 表 | **112** |
| 健康 | health=200；backend/minio healthy |
| 版本锁 | `config/aiqe-version.lock`（commit `4529e957`，tag `release-m6-20261112`） |

## 5. 遗留（人工/环境依赖）

| 项 | 说明 |
|----|------|
| Codex CLI 实机 `mcp add` | 需公司网内 Codex 环境；stdio 协议已本地冒烟 |
| 三端 Skill 截图 | 需 Claude Code/Codex/Cursor 实机，人工补充至 `work-logs/aiqe/skill-compat/` |
| MCP 后端 adapter | 当前 reader 为占位；生产需注入鉴权 adapter |

## 6. 下一步

M8：按 §19 后续任务（TA-039+，V1.1+ 剩余项）。
