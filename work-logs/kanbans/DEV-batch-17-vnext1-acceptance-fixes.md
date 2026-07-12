# 🗂️ Dev 部门项目看板 — Batch 17 · VNext-1 验收修复

> **触发来源**：[知识中心与Agent持续学习功能验收报告-2026-07-10](../../test-platform-v2/docs/知识中心与Agent持续学习功能验收报告-2026-07-10.md)
> **上一批次**：[batch-15 (M5/M6 持续学习闭环)](DEV-batch-15-rag-m5-m6-continuous-learning.md) — ✅ 代码已落地
> **验收结论**：骨架完成，端到端闭环未通过。本轮修复 P0 阻断 + P1 高优。

## 项目信息

| 字段 | 值 |
|------|-----|
| **里程碑** | VNext-1 发布阻断修复 |
| **关联** | batch-11~15（M0-M6）全部代码 |
| **状态** | 🔄 进行中 |
| **最后更新** | 2026-07-10 |

## 📍 当前位置

**Batch 17 → Slice 1 → 🔄 编码阶段**

上次完成：P0-1~P0-3 + P1-1~P1-3 全部编码修复完成
本次继续：重启后端 + 验证 + 提交

---

## 🎯 交付切片

### Slice 1 — P0 阻断修复（VNext-1 核心）

| # | 问题 | 修复文件 | 状态 |
|---|------|---------|:---:|
| P0-1a | `tsconfig.node.json` composite/emit 冲突 | `frontend/tsconfig.node.json` | ✅ |
| P0-1b | `fetchQueueItems()` 返回 `AgentRunPage` 类型错误 | `frontend/src/api/agent.ts` | ✅ |
| P0-1c | `IterationTab` 导入类型未从 `@/api/knowledge` 导出 | `frontend/src/api/knowledge.ts` | ✅ |
| P0-2 | `source_run_id` → `agent_run_id` 字段名错误 | `backend/.../agent_orchestrator.py:187` | ✅ |
| P0-3 | 队列接口 `agent:read` → `agent:list` 权限码 | `backend/.../api/v1/agent.py` | ✅ |

### Slice 2 — P1 高优修复

| # | 问题 | 修复文件 | 状态 |
|---|------|---------|:---:|
| P1-1 | tester 缺少 `menu:agent-workbench` | `backend/app/seed.py` | ✅ |
| P1-2 | 触发响应 `run_id` → `queue_item_id` + `run_id: null` | `backend/.../agent.py` + `frontend/.../agent.ts` | ✅ |
| P1-3a | Graph 禁用返回 HTTP 200+code:503 → HTTP 503 | `backend/.../knowledge.py:378` | ✅ |
| P1-3b | SearchTab 重复 toast → 内联错误状态 | `frontend/.../SearchTab.tsx` | ✅ |
| P1-3c | axios 成功拦截器业务错误 toast → 移除 | `frontend/src/api/client.ts` | ✅ |

### Slice 3 — 验证 + 提交

- [ ] 重启后端验证所有修复
- [ ] `npm run typecheck` 通过
- [ ] `npm run build` 通过
- [ ] `pytest` 后端单测通过
- [ ] 登出登入验证 CSRF 修复 + 权限修复
- [ ] Agent 触发 → 队列 → 产物写入验证
- [ ] Commit + Push

---

## 📜 批次记录

| Batch | 产出 | 审批 | 耗时 |
|-------|------|------|------|
| 17-Slice1 | P0 阻断修复 ×5 | — | — |
| 17-Slice2 | P1 高优修复 ×3 | — | — |

---

## 参考

- [验收报告](../../test-platform-v2/docs/知识中心与Agent持续学习功能验收报告-2026-07-10.md)
- [batch-11 (M0/M1)](DEV-batch-11-rag-knowledge.md)
- [batch-12 (M2 向量)](DEV-batch-12-rag-m2-vector-search.md)
- [batch-13 (M3 图谱)](DEV-batch-13-rag-m3-knowledge-graph.md)
- [batch-14 (M4 Agent)](DEV-batch-14-rag-m4-agent-orchestration.md)
- [batch-15 (M5/M6)](DEV-batch-15-rag-m5-m6-continuous-learning.md)
