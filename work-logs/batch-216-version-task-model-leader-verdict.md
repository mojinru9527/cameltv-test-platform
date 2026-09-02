# Batch 216 — Leader Verdict：VersionTask 统一事实源（B6）
> **Leader (🎯)** | Date: 2026-09-05 | Decision: **APPROVED** | Executor: Codex | 完整批次

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 高 | 数据模型 + 状态机 + 关联表 + 兼容映射全链路；JSON 列 validator + 路由基线同步 |
| 风险 | 低 | 纯后端新增表/路由，未破坏既有 API；Alembic 单头可逆 drill 通过 |
| 覆盖 | 完整 | B6 出口标准（单头 migration + 可逆 drill + 旧数据只读不双写）已核对 |

## 关键决策（已批准）
1. **VersionTask 为版本验收唯一事实源**：以 project_id+version 建唯一约束收束「需求→方案→执行→缺陷→放行」。
2. **状态机**：draft→plan_review→approved→executing→executed→verdict→released；blocked 可返工 draft；cancelled 终态；非法流转抛业务码。
3. **旧数据只读兼容**：VersionMission 经 `compat/missions/{id}` 投影为 VersionTask 视图，绝不落库（C205 口径：可读不双写）。
4. **新增 9 条 API**：/version-tasks CRUD + transition + executions + defects + compat；已登记 route_inventory（617 条）。
5. **不删旧容器**：TestPlan/VersionMission 降级/收敛留到 B14。

## 抽检通过
- ✅ `app/services/version_task_service.py:TRANSITIONS` — 状态机集中定义，非法流转统一抛 `APIException(code=1)`；单测 6/6 绿
- ✅ `alembic/versions/20260905_version_task_model.py` — down_revision=`20260904_aitde_v40_governance`，upgrade→downgrade→upgrade 全通过
- ✅ `tests/fixtures/route_inventory.json` — 617 条，路由集合与 live 一致
- ✅ 后端全量回归：2368 passed / 1 baseline fail（test_batch148_p0_fixes，batch-212 已确认）

## 判决
**APPROVED** —— 允许进入合入流程。创建 Draft PR，待 required checks 全绿 + `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过后 squash 合并到 main（用户已提前授权 B6-B15 推送+PR+合入）。

## 下一批次 Leader 条件
- C216-1: B7 建任务向导必须消费 `/api/v1/version-tasks` 状态机（draft→plan_review→approved），**不得另造任务容器**；如需扩展字段先走单头 migration。解除条件=B7 合入 + 前端向导绑定 version_task API。

## 流程回写（Batch 75 起强制）
| 发现 | 处理 | 落点 |
|------|------|------|
| 新增 JSON 列（scope/coverage/risk）在 ORM 存字符串，Out schema 校验报 dict_type | schema 用 `field_validator(mode="before")` 解析 | app/schemas/version_task.py |
| 新增路由让 route_inventory 基线漂移，守卫测试失败 | 同步更新 fixture count 617 | tests/fixtures/route_inventory.json |
| 本地 Windows 跑全量 pytest 偶发 AccessViolation（teardown） | 记录为非结果性，CI Linux 无此现象 | batch-216 qa-report §门禁 |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~4h / ~4.5h | 0/0/0/0 | 2 | 约定/基线 | 新 JSON 列配 validator；新路由同步 route_inventory |

**技能使用**: `cameltv-agent-team`、`cameltv-bug-guard`、`cameltv-doc-check`、`audit-ai-pr`
