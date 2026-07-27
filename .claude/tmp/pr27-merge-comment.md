## 🔀 已解决与 develop 的合并冲突 + 纯净环境构建修复

**合并冲突（对 develop #26「页面标题 + 知识图谱前端」）**：6 处前端冲突逐一解决（`icons.ts` / `api/knowledge.ts` / `types/index.ts` / `knowledge/index.tsx` / `GraphTab.tsx` add/add / `package-lock.json`）。本分支的图谱/实体/迭代实现是 #26 的功能超集，冲突处均保留本分支更完整版本，未丢弃 develop 侧独有工作；净代码增量 ≈ 0（HEAD 已超集 #26）。合并提交 `4890cfd`。

**纯净环境构建修复 `dc0822c`**（此前仅靠开发机未提交改动 + 累积 node_modules 掩盖的预存阻断，与本期 Wiki 无关）：
- `knowledge.ts` 补 `export type { KnowledgeIteration, KnowledgeSnapshot, CompareSnapshots }`（IterationTab TS2459）
- `agent.ts` `AgentRunTriggerResult` 增 `queue_item_id`/`run_id` 可空、`fetchQueueItems` 返回 `KnowledgePage<AgentQueueItem>`（agent-workbench 类型不匹配）
- `package.json` 补声明 `@radix-ui/react-label`（label.tsx）、`markmap-lib`/`markmap-view`（mindmap 动态导入，rollup 纯净构建解析失败）

**验证**：`tsc --noEmit` 全绿；`npm run build` 全绿（3270 模块，7.9s）。PR 现为 **MERGEABLE / CLEAN**。
