# ADR-0019：认领式任务队列统一与删除语义唯一约定

- **状态**: Accepted（2026-08-16，Batch 181 / FIX-173-P2-06、P2-08）
- **涉及**: `app/core/task_queue.py`、`app/models/*`、`alembic/versions/20260816_b181_*`
- **关联**: [report-arch-backend.md](../../_review_tools/b173/report-arch-backend.md) §3.4/§4.4

## 背景

Batch 173 深度审查确认两类架构债：

1. **六套认领式任务队列各自为政**：API/AI/DSH/证据包/Agent/UI run 六种实现，认领方式 3 种（skip_locked、UPDATE-rowcount、非原子 SELECT→改→commit），锁字段 3 套，失联回收仅 2 套具备；`agent_queue` 的认领存在跨进程 TOCTOU，多副本部署下可重复执行同一队列项。
2. **软删除三套语义并存**：`is_deleted`（用例域）、`status=deprecated`（知识域，含保鲜衰减自动废弃）、硬删（需求/缺陷/计划等），查询层过滤写法 3+ 种。

## 决策

### 1. 认领式队列统一原语（`app/core/task_queue.py`）

- `QueueSpec`（模型/状态词表/锁列/排序契约）+ `atomic_claim`/`atomic_claim_by_id`（条件 UPDATE + rowcount 校验，SQLite/PG 通用，消除 TOCTOU）+ `reap_stale`（running 且活性信号超时 → failed + 解锁）+ `finish_task` + `QueueWorkerLoop`（线程/唤醒/轮询骨架）。
- 六队列全部接入；各队列状态词表与 execute 处理器保持域内原样（状态枚举统一属 P1-06，另立专项）。
- 锁列统一 `locked_by`/`locked_at`（5 表经迁移补齐）；证据包活性判定保留 `heartbeat_at`。

### 2. 删除语义唯一约定

- **软删除 = `is_deleted` 布尔**（True=已删）。知识域 deprecated 语义并入 `is_deleted`（存量数据幂等回填；status 列保留仅作 UI 展示值）。
- **硬删除 = 显式审计删除**（不建软删列，保留审计留痕）。
- 禁止第三套删除语义；过滤写法统一 `is_deleted.is_(False)`。

## 后果

- 队列：任意 worker 崩溃后任务可被统一回收；新队列无需自研认领；并发安全由单一原语保证。
- 删除：查询/统计/检索对「已删」口径一致；`status` 从「生命周期+删除」双职责中解耦。
- 成本：表结构变更（5 表锁列 + 2 表 is_deleted，单头幂等迁移）；既有测试断言按新语义调整 5 处。
