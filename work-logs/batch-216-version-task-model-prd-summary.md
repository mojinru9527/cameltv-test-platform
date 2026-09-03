# Batch 216 — VersionTask 统一事实源（B6）
> **Product (🟦)** | Date: 2026-09-03 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 路线图: `docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md` §2 B6(batch-216) 完整·后端+DB
- 主链路: `docs/platform-refactor/01-platform-positioning-and-mainline.md` §4 唯一主链路「版本验收任务」
- 白名单: `docs/platform-refactor/02-function-abc-whitelist.md` §4 D 级收敛
- B6 出口标准: `单头 migration + 可逆 drill；旧数据可读不双写`

## 1. 问题陈述
平台已有多个「任务/容器」概念并存（VersionMission、TestPlan、Mission、Campaign、ReleaseBundle），「版本」这一业务主线没有唯一事实源。测试员建任务时不知道哪个是主线，导致：
- 各容器各自为政，版本级「需求 → 方案 → 执行 → 缺陷 → 放行」无法一条链路追踪；
- D 级重复（白名单 §4）：用户只能靠人工拼装对账；
- B6 需先立起「版本验收任务（VersionTask）」这张数据脊梁，后续 B7+ 再在其上做向导/证据/放行。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| VersionTask 表/状态机 | 无 | 有，状态机合法流转可测 | 本批 |
| 与 requirement/release_bundle/executions/defect 关联 | 无 | 有（FK / 关联表） | 本批 |
| 旧数据兼容映射（VersionMission → 视图） | 无 | 有，只读不双写 | 本批 |
| Alembic 单头 + 可逆 drill | 单头 | 单头 + upgrade/downgrade/upgrade 通过 | 本批 |
| 后端回归 | 1 baseline fail | 无新增失败 | 本批 |

## 3. 非目标（本次不做）
- **不做向导/审核面板**（B7）、**执行与证据回放**（B8）、**放行页**（B9）——这些在后续批次基于 VersionTask 实现。
- **不删除旧 VersionMission/TestPlan**：兼容映射只读，不迁移、不双写（B14 才收敛）。
- **不改前端**：本批纯后端+DB，前端消费留到 B7。
- **不引入新依赖**：仅 SQLAlchemy/FastAPI 既有栈。

## 4. 用户故事 + 验收标准
- As a 测试员, I want 一个「版本验收任务」容器把需求/方案/执行/缺陷/结论串起来, so that 版本主线可一条链路追到底。
  - 验收：Given 创建 VersionTask / When 走状态机 draft→…→released / Then 合法流转成功、非法流转拒绝；且可关联 execution/defect。
- As a 维护者, I want 旧智能测试任务(VersionMission)能只读映射为 VersionTask 视图, so that 老数据可读不双写。
  - 验收：`compat/missions/{id}` 返回 mission 视图；库中不新增来自 mission 的 version_task 行。
- As a 发布者, I want 迁移单头且可逆, so that PG 与 SQLite 双向 drill 不破。
  - 验收：`alembic heads` 单头；upgrade → downgrade → upgrade 全通过。

## 5. 技术考量
- 后端栈：FastAPI + SQLAlchemy + Alembic；响应体 `R[Page[T]]` / `R[T]`。
- 状态机集中 `VersionTaskService.TRANSITIONS`，非法流转抛 `APIException(code=1)`（业务码）。
- JSON 列（scope/coverage/risk）在 Out schema 用 `field_validator(mode="before")` 解析字符串为 dict。
- 旧数据兼容映射只读（`_mission_to_task_dict`），绝不落库。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台 | 后端 F821/route-inventory/Alembic drill/version_task 测试 + 全量回归无新增失败 |
| M1 里程碑 | 平台 | B6–B10 合入 → 黑盒跑通版本验收闭环 |

## 7. 技能使用
- `cameltv-agent-team` → 六部门工件
- `cameltv-bug-guard` → 迁移/路由/权限核对（本批新增路由已登记 route_inventory；Alembic 单头 drill）
- `cameltv-doc-check` → 主链路/白名单文档一致性
