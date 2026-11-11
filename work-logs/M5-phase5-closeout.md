# M5（Phase 5：变更影响 + 学习策展 + 门禁 + MCP + Skills）收口报告

> **日期**：2026-11-12 · **范围**：TA-029 → TA-032.5（5 批）
> **结论**：M5 全部任务完成并合入 main；生产 `20261122` 已上线（111 表）。

## 1. 批次

| 批次 | TA | 内容 | PR |
|------|----|------|----|
| batch-309 | TA-029 | A5 Change Impact（PR diff → 候选并集、auth 强制） | #538 |
| batch-310 | TA-030 | A6 Learning Curator（benchmark→人审→ACTIVE、误报/重复护栏） | #539 |
| batch-311 | TA-031 | VersionTask Quality Gate（P0 未执行/未知/失败不 PASS） | #540 |
| batch-312 | TA-032 | AIQE MCP Gateway（只读查询、写审批门禁） | #541 |
| batch-313 | TA-032.5 | Agent Skills ×6（统一契约 + 校验脚本） | #542 |

## 2. 数据模型

- `learning_candidates` / `bug_patterns`（迁移 `20261122`）；
- 生产迁移链：`20261121 → 20261122`（head），表数 109 → **111**。

## 3. 测试与质量

- 后端全量：**1625 passed / 43 skipped**；
- 前端全量：**560 passed**（M5 未改前端）；
- ratchet PASS；Skill 校验 `AIQE_SKILLS=PASS（6 个 skill）`。

## 4. 生产部署

| 项 | 结果 |
|----|------|
| 备份 | `pre-m5-20261112-041221.dump`（174MB，sha256 `ba48c512…`） |
| 镜像 | `cameltv-tp-backend:release-m5-20261112` → `:main`；回滚 `prev-m5` |
| 迁移 | `20261121 → 20261122_ta030_learning` |
| 表 | 109 → **111**（learning_candidates / bug_patterns） |
| 健康 | health=200；imports OK |
| 磁盘 | 82% |

## 5. 遗留（不阻塞 M6）

| 项 | 说明 |
|----|------|
| 真实 benchmark 数据 | 服务接收外部指标，数据集管道后续接 |
| MCP 真实 server/adapter | Gateway 纯函数已测，stdio/HTTP 封装待接 |
| 三客户端 Skill 加载截图 | 需 Claude Code/Codex/Cursor 实机人工验收 |
| Quality Gate 前端 | 判定服务已就绪，版本任务详情页待接 |
| CI 接入 skill 校验 | workflow 修改受 worktree scope 限制，另批接 |

## 6. 下一步

M6：按 §19 后续任务（TA-033+）。
