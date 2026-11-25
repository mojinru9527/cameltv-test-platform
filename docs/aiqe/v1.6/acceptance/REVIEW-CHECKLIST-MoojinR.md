# AIQE V1.6 独立验收清单 — MoojinR (qa)

> 本清单只列出待验收项，不代表已验收。
> 每条需求需 MoojinR 阅读对应证据后，再写入 `acceptance/records/<ID>.json`（`record_acceptance.py`）。

- 总需求：**70**
- 当前独立验收：**0 / 70**
- 记录目录：`docs/aiqe/v1.6/acceptance/records/`
- 角色域：reviewer = qa（MoojinR），owner 见下表

## 分组清单

### TC-AIQE-001

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-001 | P1 | 需求契约冻结 + 需求变更影响 | qa-automation | 2 证据 / 2 测试 | NOT_REVIEWED |

### TC-AIQE-002

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-002 | P1 | 运营后台发布资讯 → 前端可查看（用户批准简化口径） | qa-automation | 3 证据 / 2 测试 | NOT_REVIEWED |

### TC-AIQE-003

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-003 | P1 | API 首次失败 + 重试成功 → 不得掩盖失败 | qa-automation | 1 证据 / 2 测试 | NOT_REVIEWED |

### TC-AIQE-004

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-004 | P1 | 广告/其他功能浮层造成交叉干扰 | qa-automation | 2 证据 / 2 测试 | NOT_REVIEWED |

### TC-AIQE-005

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-005 | P1 | 并发数据污染 | qa-automation | 2 证据 / 2 测试 | NOT_REVIEWED |

### TC-AIQE-006

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-006 | P1 | 上游第三方故障 | qa-automation | 2 证据 / 2 测试 | NOT_REVIEWED |

### TC-AIQE-007

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-007 | P1 | UI Runner 自身故障 | qa-automation | 1 证据 / 2 测试 | NOT_REVIEWED |

### TC-AIQE-008

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-008 | P1 | 开发修复后点击回归 | qa-automation | 4 证据 / 2 测试 | NOT_REVIEWED |

### TC-AIQE-009

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-009 | P2 | 多端 AC 对照 | qa-automation | 1 证据 / 2 测试 | NOT_REVIEWED |

### TC-AIQE-010

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| TC-AIQE-010 | P1 | 学习候选发布 | qa-automation | 4 证据 / 2 测试 | NOT_REVIEWED |

### V16-001

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-001-R1 | P0 | 策略四态决策与不可变授权快照 | backend-security | 2 证据 / 4 测试 | NOT_REVIEWED |
| V16-001-R2 | P0 | Worker 入口在创建 Driver 前 fail-closed | backend-security | 2 证据 / 7 测试 | NOT_REVIEWED |
| V16-001-R3 | P0 | 删除 legacy fail-open 执行器与静态门禁 | backend-security | 2 证据 / 2 测试 | NOT_REVIEWED |
| V16-001-R4 | P0 | 外部 Runner 载荷与上报同样受策略约束 | execution-platform | 2 证据 / 3 测试 | NOT_REVIEWED |
| V16-001-R5 | P0 | 旧 Workflow 策略迁移与 NEEDS_POLICY_REVIEW 禁止启动 | backend-security | 2 证据 / 2 测试 | NOT_REVIEWED |

### V16-002

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-002-R1 | P0 | 应用层导航预校验 + 浏览器层 route 全请求拦截 | driver-device | 2 证据 / 5 测试 | NOT_REVIEWED |
| V16-002-R2 | P0 | 出口代理覆盖 redirect / WebSocket / 弹窗与 DNS pinning | driver-device | 2 证据 / 5 测试 | NOT_REVIEWED |
| V16-002-R3 | P0 | 拦截证据与安全事件（不含敏感值） | backend-security | 2 证据 / 3 测试 | NOT_REVIEWED |

### V16-003

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-003-R1 | P0 | 输出分类与 Secret Handle 化（唯一安全写入入口） | backend-security | 1 证据 / 4 测试 | NOT_REVIEWED |
| V16-003-R2 | P0 | 持久化/API/日志/Artifact 零明文（Canary 扫描） | backend-security | 1 证据 / 3 测试 | NOT_REVIEWED |
| V16-003-R3 | P0 | Vault 不可用 fail-closed 与生命周期（过期/撤销/轮换） | backend-security | 1 证据 / 3 测试 | NOT_REVIEWED |
| V16-003-R4 | P0 | 外部 Secret Store / KMS 跨进程解析（Vault Transit） | security | 4 证据 / 6 测试 | NOT_REVIEWED |

### V16-004

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-004-R1 | P0 | Query Registry 服务端化 + AST allowlist | backend-security | 2 证据 / 11 测试 | NOT_REVIEWED |
| V16-004-R2 | P0 | 租户谓词、限额、审批与执行审计 | backend-security | 1 证据 / 5 测试 | NOT_REVIEWED |
| V16-004-R3 | P0 | 只读数据库连接拒绝写操作 | security | 3 证据 / 2 测试 | NOT_REVIEWED |

### V16-005

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-005-R1 | P1 | fencing token 强制覆盖全部写结果路径 | execution-platform | 1 证据 / 4 测试 | NOT_REVIEWED |
| V16-005-R2 | P1 | Job 幂等键与重复投递不产生第二副作用 | execution-platform | 1 证据 / 2 测试 | NOT_REVIEWED |
| V16-005-R3 | P1 | Reconciler 收敛 QUEUED 悬挂与幂等对账 | execution-platform | 2 证据 / 3 测试 | NOT_REVIEWED |

### V16-006

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-006-R1 | P1 | 唯一 Launch 入口与 LaunchResult 契约 | execution-platform | 1 证据 / 4 测试 | NOT_REVIEWED |
| V16-006-R2 | P1 | Outbox 同事务写入与幂等 relay | execution-platform | 1 证据 / 2 测试 | NOT_REVIEWED |

### V16-007

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-007-R1 | P1 | 不可变 WorkflowSnapshot 与 Run 绑定 | execution-platform | 1 证据 / 6 测试 | NOT_REVIEWED |
| V16-007-R2 | P1 | SnapshotCloner 完整复制 DAG 与 clone diff | execution-platform | 2 证据 / 4 测试 | NOT_REVIEWED |

### V16-008

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-008-R1 | P1 | 服务端 Scope Snapshot 与三类集合 | quality-platform | 1 证据 / 4 测试 | NOT_REVIEWED |
| V16-008-R2 | P1 | Launch 强制 Scope 且禁止排除 Mandatory | quality-platform | 1 证据 / 4 测试 | NOT_REVIEWED |
| V16-008-R3 | P1 | Run PASS 门禁：Mandatory 全部 PASSED | quality-platform | 1 证据 / 3 测试 | NOT_REVIEWED |
| V16-008-R4 | P1 | 回归幂等键确定性（SHA/Snapshot/Scope/Env） | quality-platform | 2 证据 / 3 测试 | NOT_REVIEWED |

### V16-009

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-009-R1 | P1 | 节点类别与业务 Oracle 强制 | execution-platform | 1 证据 / 6 测试 | NOT_REVIEWED |
| V16-009-R2 | P1 | Run PASS 语义与业务证据 | execution-platform | 1 证据 / 3 测试 | NOT_REVIEWED |

### V16-010

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-010-R1 | P1 | Benchmark Gate 唯一批准条件 | ai-quality | 1 证据 / 5 测试 | NOT_REVIEWED |
| V16-010-R2 | P1 | 审批/发布事务内重校验与撤销 | ai-quality | 1 证据 / 5 测试 | NOT_REVIEWED |

### V16-011

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-011-R1 | P1 | Benchmark/Learning Service 跨项目隔离 | ai-quality | 1 证据 / 8 测试 | NOT_REVIEWED |

### V16-012

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-012-R1 | P1 | 服务端 Evidence Resolver | ai-quality | 1 证据 / 4 测试 | NOT_REVIEWED |
| V16-012-R2 | P1 | A4 归因证据强制校验与 BLOCKED 语义 | ai-quality | 1 证据 / 7 测试 | NOT_REVIEWED |
| V16-012-R3 | P1 | 证据快照/hash 防替换 | ai-quality | 1 证据 / 2 测试 | NOT_REVIEWED |

### V16-013

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-013-R1 | P1 | 持久化 AgentTask 与审批状态机 | ai-quality | 1 证据 / 4 测试 | NOT_REVIEWED |
| V16-013-R2 | P1 | 审批后真实执行 run_plan 与失败语义 | ai-quality | 2 证据 / 4 测试 | NOT_REVIEWED |
| V16-013-R3 | P1 | Outbox + ExecutionJob 异步执行入口 | ai-quality | 3 证据 / 6 测试 | NOT_REVIEWED |

### V16-014

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-014-R1 | P1 | A5 证据化 Change Impact 分析 | ai-quality | 2 证据 / 8 测试 | NOT_REVIEWED |
| V16-014-R2 | P1 | A5 impacted cases 进入 Mandatory/Related Scope | ai-quality | 2 证据 / 9 测试 | NOT_REVIEWED |

### V16-015

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-015-R1 | P1 | VERIFIED 只来自真实验收 Run + Artifact | driver-platform | 1 证据 / 5 测试 | NOT_REVIEWED |
| V16-015-R2 | P1 | Preflight 只接受 VERIFIED 与软件变更自动降级 | driver-platform | 1 证据 / 3 测试 | NOT_REVIEWED |

### V16-016

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-016-R1 | P1 | GA 平台声明与动作粒度 Preflight | driver-platform | 1 证据 / 3 测试 | NOT_REVIEWED |
| V16-016-R2 | P1 | 设备租约回收与 PlatformBinding 绑定 | driver-platform | 1 证据 / 3 测试 | NOT_REVIEWED |

### V16-017

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-017-R1 | P1 | 平台链路真实 E2E（全部） | qa-automation | 12 证据 / 13 测试 | NOT_REVIEWED |
| V16-017-R2 | P1 | 产品级 E2E（全部） | qa-automation | 4 证据 / 2 测试 | NOT_REVIEWED |

### V16-018

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-018-R1 | P1 | Artifact finalize 完整性与归属校验 | security | 1 证据 / 4 测试 | NOT_REVIEWED |
| V16-018-R2 | P1 | Evidence Lifecycle 与访问审计 | security | 1 证据 / 5 测试 | NOT_REVIEWED |

### V16-019

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-019-R1 | P1 | 工具真实绑定与启动可用性校验 | ai-quality | 2 证据 / 10 测试 | NOT_REVIEWED |
| V16-019-R2 | P1 | 参数 schema / Project 越权 / 限流 / 超时拒绝 | ai-quality | 2 证据 / 6 测试 | NOT_REVIEWED |
| V16-019-R3 | P1 | 工具调用审计与审批/生产只读 | ai-quality | 2 证据 / 8 测试 | NOT_REVIEWED |

### V16-020

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-020-R1 | P1 | 仅真实终态 Run 生成 Comparison Snapshot | execution-platform | 1 证据 / 2 测试 | NOT_REVIEWED |
| V16-020-R2 | P1 | 聚合规则与不可变对比证据 | execution-platform | 1 证据 / 4 测试 | NOT_REVIEWED |

### V16-021

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-021-R1 | P2 | Dogfood 脚本无弱默认口令 | security | 2 证据 / 5 测试 | NOT_REVIEWED |

### V16-022

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-022-R1 | P2 | 依赖锁定与一键复现 | devops | 1 证据 / 3 测试 | NOT_REVIEWED |
| V16-022-R2 | P2 | 测试分层执行器与 JUnit 产物 | devops | 1 证据 / 3 测试 | NOT_REVIEWED |

### V16-023

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-023-R1 | P2 | 机器可读 evidence-index 生成器 | qa-automation | 3 证据 / 8 测试 | NOT_REVIEWED |

### V16-024

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-024-R1 | P0 | 指标与告警（21 项 / P0 Canary） | devops | 13 证据 / 6 测试 | NOT_REVIEWED |
| V16-024-R2 | P0 | 容器 egress / 限流 / Canary 计数器 | devops | 2 证据 / 3 测试 | NOT_REVIEWED |
| V16-024-R3 | P0 | 灰度 / 备份恢复 / 监控联调演练 | devops | 8 证据 / 3 测试 | NOT_REVIEWED |

### V16-025

| 需求 ID | 优先级 | 标题 | Owner | 证据/测试 | 验收状态 |
|---|---|---|---|---|---|
| V16-025-R1 | P0 | 需求—代码—正式入口—测试—证据追踪与 CI 门禁 | tech-lead | 12 证据 / 24 测试 | NOT_REVIEWED |

## 记录命令（示例）

```powershell
python scripts/aiqe/record_acceptance.py --requirement V16-001-R1 --reviewer MoojinR \
  --reviewed-at 2026-11-26 --artifact "docs/aiqe/v1.6/acceptance/records/V16-001-R1.json" \
  --decision REVIEWED
```

> 只有 MoojinR 本人完成 review 后才应写入 REVIEWED；不得由实现者代签。
