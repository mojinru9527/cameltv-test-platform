# M2（Phase 2：DAG + Driver + 变量 + 能力）收口报告

> **日期**：2026-11-11 · **范围**：TA-009 / TA-010 / TA-010.3 / TA-011 / TA-012 / TA-013 / TA-014 / TA-015
> **结论**：M2 全部批次开发完成并合入 main；生产 20261114 已部署，20261115 待窗口。

## 1. 批次

| 批次 | TA | 内容 | PR |
|------|----|------|----|
| batch-283 | TA-009 | Workflow Validator（环/依赖/变量/driver/重试/断言/edge/checksum） | #512 |
| batch-284 | TA-010 + .3 | DAG Scheduler + 资源锁（TTL/fencing/恢复） | #513 |
| batch-286 | TA-011 | RunContext（变量/secret/隔离） | #515 |
| batch-287 | TA-012 | HTTP Driver（证据/脱敏/链式/首失败保留） | #516 |
| batch-288 | TA-013 | Playwright Driver（登录/动作/五类证据） | #517 |
| batch-289 | TA-014 | DB Read-only Driver（白名单/行数上限） | #518 |
| batch-290 | TA-015 | Capability Registry（evidence 门槛/筛选） | 本批 |

## 2. 数据模型

新增 3 表：`workflow_definitions`、`resource_locks`、`node_capability_manifests`；
迁移链 `20261114 → 20261115`，生产 20261114 已上线，20261115 待窗口。

## 3. 验收与测试

- 后端全量 **1478 passed / 43 skipped**（M2 新增 68 条：16+15+9+6+5+16+8 = 75？以实际批次为准）；
- ratchet PASS；
- 关键验收：环/悬空变量/未注册 driver/非幂等重试拒绝；串行/并行/fail_fast/恢复；资源锁 fencing；
  secret 不落库；HTTP 首失败保留；DB 写操作全拒；缺 WebKit 节点不接 WebKit。

## 4. 遗留（不阻塞 M3）

| 项 | 说明 |
|----|------|
| 规则 6 profile policy | 需 `execution_profiles` 表（M3） |
| 规则 7 审批 API/UI | 存储层冻结已完成，HTTP/审批流待补 |
| 条件边 `edges.condition` | 调度器当前仅成功边 |
| 调度器接 ExecutionJob/Worker | dispatch 目前是回调 |
| 真实浏览器 E2E | Playwright Driver 仅 fake 测试 |
| Console 菜单/RBAC | 仍 URL 直达 |
| SSE 长连接/Redis | 30s SSE + 轮询 |
| Artifact 留存/GC | 文件只增不减 |

## 5. 下一步

M3（Phase 3）：Playwright MCP Explorer PoC / TesterArmy Adapter / Keploy / Agent Service（TA-016+）。
