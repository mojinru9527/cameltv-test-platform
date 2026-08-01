# Batch 61 Release Readiness 冻结记录

## 1. 当前判定

**目标判定已降级为：`LOCAL HARDENING COMPLETE / EXTERNAL BLOCKED`。**

原因：截至 `2026-08-01`，Test5/VPN、六服务当前契约、最小权限账号、稳定数据/清理规则、脱敏旧 PostgreSQL 快照、test release 基础设施和 DevOps owner 均未登记。该目标只是允许继续完成本地加固；当前 19 个 MUST 为 4 `PASS` + 6 `BLOCKED` + 9 `NOT RUN`，因此仍不能声称“LOCAL HARDENING COMPLETE”。

Production 发布和 production 数据库迁移为 `DEFERRED`。Batch 61 只交付 test 环境 release MVP；OPS2 运维 API/UI 与 OPS3 production 晋级属于 Batch 62/63。

## 2. 判定状态词汇

| 状态 | 规则 |
| --- | --- |
| `PASS` | 全部必需断言与证据一致 |
| `FAIL` | 已执行且至少一个必需断言失败 |
| `BLOCKED` | 外部前置缺失，无通过计数；记录日期、owner 和解除条件 |
| `NOT RUN` | 可执行但尚未执行 |
| `DEFERRED` | 明确不属于 Batch 61 |

## 3. Release train 与合并门禁

```text
W1 production-safety-and-test-credibility
  required checks + PR merge to main
    ↓ 从最新 origin/main 创建
W2 sports-api-ui-r2-acceptance
  required checks + PR merge to main
    ↓ 从最新 origin/main 创建
W3 test-release-control-plane-mvp（新开 deploy/release-control 项目）
  required checks + PR merge to main
    ↓
仅有证据对账变更时创建 final acceptance PR
```

不得在上一工作流未合并时从旧代码创建后续工作流；不得直接 push `main`。

## 4. 里程碑 readiness

| 里程碑 | 计划输出 | 当前状态 | 当前依据 / 解除条件 |
| --- | --- | --- | --- |
| M0 Batch 60 closure | B60 合入 main、CI 绿色、干净 B61 基线 | `PASS`（仅基线） | B61 HEAD 与 `origin/main` 均为 `7d9a0118...`；不代表 B61 功能通过 |
| M1 Safety hardening | 4 个 P0 动态关闭、五入口、隔离/RBAC | `NOT RUN` | W1 已完成统一 guard、API 契约、改密与浏览器矩阵实现，但真实后端/DB/审计、五入口浏览器基数及历史标注回读闭环未齐，按严格词汇仍为 `NOT RUN` |
| M2 Sports credibility | 无假绿、零未接受 high/critical、R2 只读 | `BLOCKED` | Test5/VPN/账号/数据 owner `UNASSIGNED` |
| M3 Release contract/engine | manifest、CLI、状态机、Jenkins、回滚 | `BLOCKED` | DevOps owner 和 test 基础设施 `UNASSIGNED`；W3 尚未按顺序创建 |
| M4 Real exercises | Test5、旧 PG、test deploy/rollback | `BLOCKED` | R2 包、旧 PG 快照和 release 环境均缺失 |
| M5 Full acceptance | 全矩阵、PC 证据、QA 与 verdict | `NOT RUN` | 必须等待 W1→W2→W3 顺序合并和证据对账 |

## 5. A01–A14 初始门禁

| 门禁组 | 初始状态 | Batch 61 退出标准 |
| --- | --- | --- |
| A01/A02 基线与隔离 | `NOT RUN` | 三 worktree 元数据、SHA、端口/数据库/环境清单逐一可追溯 |
| A03–A09 功能/API/RBAC/事务/并发/查询/UI | `NOT RUN` | 所有 release-scope P0/P1 正负面 100% 执行且 100% PASS |
| A10 真实旧库 | `BLOCKED` | 授权脱敏旧 PG 快照升级、重复升级、唯一 head、数据保留通过 |
| A11 自动化/供应链 | `NOT RUN` | 双端全量、体育套件、release-control 测试和审计通过；零未接受 high/critical |
| A12 文档/证据一致 | `NOT RUN` | issue/matrix/manifest/snapshot/report totals 与代码事实一致 |
| A13 运维 Test 发布 | `BLOCKED` | immutable test 部署、实际 digest/revision、幂等、失败恢复和应用回滚通过 |
| A14 PC 快照 | `NOT RUN` | 所有正常工作 PC 功能有视觉复核的 1440×900 成功态索引 |

## 6. 外部 blocker 决策表

| Blocker | 状态 | 登记日期 | Owner | 对 verdict 的影响 |
| --- | --- | --- | --- | --- |
| Test5/VPN + 六契约 | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | 不得 `READY FOR TEST RELEASE` |
| Test5 只读/写账号 | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | 登录、鉴权、支付/退款/赠送不得记 PASS |
| 稳定业务数据 + cleanup | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | 缺数据必须 BLOCKED，禁止 skip 假绿 |
| 脱敏旧 PostgreSQL 快照 | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | A10 不通过，不能用空库替代 |
| DevOps owner + registry/Runner/PG16/backup/Secret refs | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | OPS0/OPS1、A13、M3/M4 不可通过 |
| Release-verdict owner | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | 无人类具名签署，不得发布 |

计划要求在相对 Day 2 前冻结这些输入；绝对开工日尚未批准，所以绝对到期日保持 `UNASSIGNED`，不编造日期。

## 7. 机械判定规则

```text
READY FOR TEST RELEASE
= 19/19 MUST PASS
  + release-scope P0/P1 zero FAIL/BLOCKED/NOT RUN/runtime skip
  + zero open P0
  + zero unaccepted high/critical runtime vulnerability
  + Test5 authorized R2 read-only evidence PASS
  + immutable test deployment and application rollback PASS
  + required checks PASS

LOCAL HARDENING COMPLETE / EXTERNAL BLOCKED
= all locally controllable MUST PASS
  + only external prerequisites remain BLOCKED
  + every blocker has date, owner/UNASSIGNED and解除条件

NOT READY
= any locally controllable MUST FAIL or NOT RUN
  OR evidence/owner/totals disagree
```

当前实际状态属于 `NOT READY`；目标上限为 `LOCAL HARDENING COMPLETE / EXTERNAL BLOCKED`，直到外部包具备并完成复测。

## 8. W1 代码质量检查点（2026-08-01）

| 检查 | 最终结果 | 证据边界 |
| --- | --- | --- |
| 后端运行时引用 | `PASS` | `ruff check app/ --select F821` 通过 |
| 后端全量 | `PASS` | 初始化 `lanhu-mcp` 后 `976 passed, 3 skipped, 0 failed`；skip 为 PostgreSQL 专用条件 |
| 前端全量 | `PASS` | Vitest `291/291`、TypeScript typecheck、生产 build 均通过 |
| W1 浏览器矩阵 | `PASS` | worktree 端口 `5197`，Chromium headed `39/39`；测试使用受控 Mock API，不替代真实后端/DB/审计证据 |
| Release verdict | `NOT READY` | 仅 B60-P1-011、015、016、020 达到当前最低证据；其他本地 MUST 与全部外部阻塞仍未关闭 |

## 9. 下一次复核触发器

- W1 每个 MUST 完成动态证据后更新矩阵、台账和 PC 索引。
- 任一 Test5/VPN/账号/数据包到位时，记录提供人、日期、有效期和授权范围，再解除对应 `BLOCKED`。
- DevOps owner 与 test 基础设施登记后，方可建立 W3 新项目并执行 OPS0/OPS1。
- 任一状态或文件总数变化时，同步对账五份 Batch 61 文档；不得只改 release verdict。
