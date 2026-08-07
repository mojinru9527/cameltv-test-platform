# Batch 121 — PRD Summary（全量拓扑入库 + 多 worker 验证）

> **Product (🟦)** | Date: 2026-08-08 | Status: Review | **mode: full**
> 判定：含新能力（interaction_edge 表+迁移+全量缺口计算、C120-2 多会话验证）→ 完整批次。

## 1. 问题陈述

1. **C120-1 缺口计算不完整**：batch-120 的 InteractionGapPanel 只内置 8 条模块级代表边；3172 条完整交互拓扑（evidence/batch-113/interaction-paths.json）未入库，全量覆盖无法计算。
2. **C120-2 多 worker 未实测**：C117-2 的 DB 队列认领是代码级实现，未验证多会话/多 worker 同时认领时不会重复执行，也未在部署后验证生产链路。
3. **追踪器卫生复发**：C120-1/2 写在 batch-120 判决但未同步 Open 表（C118-1/C119-1/2 同款问题第三次出现）。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 拓扑入库 | 8 条内置 | 3172 条全量入库（interaction_edge 表），缺口端点按全量计算 | 本批 |
| 多会话认领 | 单会话单测 | 双会话竞态测试：同任务仅一个 worker 认领成功 | 本批 |
| 生产验证 | 未验证 | 部署后 ai_task 提交→轮询 done 全链路 + Railway 实例数登记 | 本批 |
| 追踪器 | C120-1/2 未登记 | 补登记 Open 表 → 本批 Closed 带证据 | 本批 |

## 3. 非目标（本次不做 + 豁免理由）

- **C106-2 邀请链接观察**：用户明确继续跳过。
- **外部项**（Test5 IP 封禁待运维解封、iOS DDI 26.5.2 待提供）：维持 Deferred。
- **C120-2 不做 Railway 实例扩容操作**：只做多会话竞态测试 + 部署后链路验证与实例数登记（扩容属运维操作，如需另行执行）。

## 4. 用户故事 + 验收标准

- **US-1 C120-1**：As a 测试工程师, I want 缺口计算基于全量拓扑 so that 覆盖评估完整。
  验收：Given 3172 边入库 / When 缺口端点计算 / Then total_edges=3172，前端面板显示全量结果；单测覆盖。
- **US-2 C120-2**：As a Dev, I want 多 worker 认领互斥可证 so that 多副本部署不丢任务。
  验收：Given 同一 pending 任务 + 两个独立会话 / When 同时认领 / Then 仅一个成功（rowcount 守卫），无重复执行；单测覆盖。部署后生产提交 extract/generate 异步任务轮询 done。
- **US-3 追踪器**：C120-1/2 补登记 Open 表并带证据关闭。

## 5. 技术考量

- C120-1：新增 `interaction_edge` 表（id/project_id/from_module/entry/to/evidence/来源 batch）；迁移幂等；导入脚本读 evidence JSON 批量入库；`GET /interaction-coverage/topology` 返回全量；gaps 端点 body 无 edges 时用 DB 全量。
- C120-2：多会话竞态测试用文件型 SQLite（两个独立 Session 指向同一文件），验证 UPDATE 守卫；生产验证用平台 API 提交异步任务轮询 done，登记 Railway 实例数。
- 前端 InteractionGapPanel 改为后端全量模式（去掉内置 8 条，或保留为编辑样本但默认走全量）。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main → Railway 部署（迁移建表+导入） | 全平台 | 门禁全绿；生产全量拓扑可查 |
| 部署后验证 | QA | ai_task 提交→done；缺口端点 total=3172 |

## 7. 技能使用

- `cameltv-agent-team`：六部门流水线。
- `cameltv-bug-guard`：迁移/并发实现避坑。
- `cameltv-ui-conventions`：面板微调。
