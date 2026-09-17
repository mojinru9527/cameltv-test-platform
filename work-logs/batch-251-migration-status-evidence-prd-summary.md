# Batch 251 — 迁移状态证据取源修复（C250-1）PRD-lite

> **🟦 Product** | Date: 2026-09-17 | 分支：`fix/batch-251-migration-status-evidence`

```yaml
mode: light
豁免理由: |
  修复既有缺陷（C250-1），不引入新接口、新配置、新依赖、新用户可见行为：
  仅把「迁移状态」的**取值来源**从被截断的日志尾部窗口，换成执行器已持有的完整远端输出，
  并把结果作为既有 `ExecutorResult` 的一个可选字段带回控制面事件。
判定依据: docs/agent-team/pipeline-modes.md「是否引入新行为/新接口/新配置/新依赖」→ 否。
```

## 1. 问题陈述（为什么用户/运维关心）

Batch 250 的生产验收（`release-20260917-0006`）暴露：迁移校验步骤确实按设计执行了
（顺序为 迁移→校验→停旧→起新，命令实测 rc=0），但控制面的 `PROD_OBSERVING` 事件 reason
**只剩 `publish succeeded`**，没有带上 `migration target=… actual=…`。

根因：状态行在命令序列**早期**打印，而 `ExecutorResult.logs = output[-4000:]` 只保留远端输出
最后 4000 字符，其后的 `docker compose up --wait` 输出（60+ 行）把状态行挤出窗口，
`_success_reason` 解析 `logs` 自然取不到。

后果：运维在发布记录里看不到"这次发布把库迁到了哪个 revision"的**正向证据**，
只能再去 SSH 手工核对——这正是 C249-4 想消除的核对成本。

## 2. 成功指标

| # | 指标 | 判定 |
|---|------|------|
| M1 | 成功发布的事件 reason 带迁移落点 | `/events` 的 `PROD_OBSERVING.reason` 含 `migration target=X actual=X`（真实发布验证） |
| M2 | 不依赖日志窗口 | 单测：状态行在完整输出里、但**不在** `logs` 尾部窗口时仍能取到 |
| M3 | 无状态行时不臆造 | 单测：输出里没有 `CAMELTV_MIGRATION` → `migration_status=None`，reason 保持原样 |
| M4 | 失败路径语义不变 | Batch 250 的失败路径用例继续全绿 |

## 3. 非目标（本批不做）

- 不放大日志窗口（保持 4000 字符）：`up --wait` 的输出不该被灌进事件/API 响应。
- 不改失败路径的取值方式（异常文本尾部已含状态行，语义不变）。
- 不动 C248-8（runner target 本机不可构建）、C249-5/-6/-7。

## 4. 用户故事与验收标准

### US-1（运维）发布记录要能自证迁移落点

- **Given** 一次发布成功（迁移已把库升到 manifest 的 target revision）
- **When** 我查看该发布的 `/api/deployments/{id}/events`
- **Then** `PROD_OBSERVING` 的 reason 形如
  `publish succeeded; migration target=20260922_ai_agent_token actual=20260922_ai_agent_token`

### US-2（后续开发者）回归保护

- **Given** 远端输出很长、状态行落在尾部窗口之外
- **When** 我跑控制面测试
- **Then** 有用例断言 `ExecutorResult.migration_status` 取自完整输出，且 `logs` 里确实不含该行

## 5. 纳入本批的 C 条件

| ID | 内容 | 本批处理 |
|----|------|---------|
| C250-1 | 迁移状态正向证据被 4000 字符日志窗口截断 | ✅ 修复（完整输出解析 + 结果字段 + 事件 reason） |

## 6. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| 新增字段破坏既有调用方 | 低 | `ExecutorResult.migration_status` 为带默认值的可选字段；`app.py` 保留 `logs` 兜底，测试替身不受影响 |
| 迁移状态与日志不一致（两处解析） | 低 | 执行器只解析一次，事件优先用该字段；兜底仅在字段缺失时生效 |
| 生产验证需要再跑一次发布窗口 | 中 | 复用 `-0006` 已在服务器的镜像生成 `-0007` 制品（不重新构建），窗口约 1–2 分钟 |
