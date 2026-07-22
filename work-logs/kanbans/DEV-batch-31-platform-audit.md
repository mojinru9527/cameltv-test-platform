# Dev 看板 — Batch 31 平台全面审查

> 创建/更新：2026-07-22 | 分支：`feature/batch-31-platform-audit`

| Slice | 方案 | 编码 | 自测 | 审批 | 合入 |
|---|:---:|:---:|:---:|:---:|:---:|
| 最新基线与 Git 隔离 | ✅ | ✅ | ✅ | ✅ | — |
| 全栈缺陷修复 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 知识中心 UI/功能验收 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| Agent Team / CI 加固 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 远端 Draft PR | ✅ | ✅ | ✅ | 🔄 | ⏳ |

## 当前状态

- 本地：后端 653 passed，前端 96 passed，typecheck/build 通过。
- 生产验收：用户端赛事回放未达到蓝湖 15.0；后台生产验收阻塞。
- 下一步：显式暂存 → commit → push → Draft PR → 等待 CI/人工审查。

## 风险

| 项 | 等级 | 处理 |
|---|---|---|
| develop 无 required checks/审批 | P1 | Draft PR，禁止自动合并 |
| npm audit 17 | P1 | 独立依赖升级批次 |
| Ruff 全规则 201 | P2 | 独立清理批次，F821 已阻断 |
