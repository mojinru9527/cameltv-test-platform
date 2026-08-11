# Batch 149 — Leader Verdict（统计口径收敛 + 计划进度）

> **Leader (🎯)** | Date: 2026-08-11 | Decision: APPROVED

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 4.5/5 | 单一统计源 + 口径文档化；批量查询无 N+1 |
| 风险 | 低 | 仅后端查询层重构；响应字段新增，无破坏性变更 |
| 覆盖 | 4.5/5 | 39 pytest + 450 vitest + 冒烟三端一致性 |

## 关键决策（已批准）
1. 用例域统计收敛到 `statistics_service`；执行计数不因用例删除丢失（保留真实执行），用例总数/类型分布过滤 is_deleted。
2. report_aggregator（ApiExecutionTask/UI 运行域）口径独立并文档化边界，不强行合并。
3. 计划进度以 `PlanOut.stats`（plan_case last_status）为锚，与详情一致。

## 抽检通过
- ✅ statistics_service 口径（active 子查询 / execution 不过滤删除 / distinct case_id）
- ✅ dashboard case_type_stats 复用 by_type，删除 is_deleted 关联过滤
- ✅ trace total_cases/by_type/by_domain 过滤一致
- ✅ PlanOut.stats 输出（schema 单测 + 冒烟 UI 1/2）
- ✅ 冒烟证据 evidence/batch-149/（三端数字 + plan-list-progress.png）

## 判决
APPROVED → 按用户一次性授权推送、创建 Draft PR，required checks 全绿后合入 main。
合入后关闭 C147-3/C147-4（C146-2 由 C147-3 承接一并关闭）。

## 下一批次 Leader 条件
- 无新增；Batch 150 承接 C147-5（请求缓存/防抖/退避/mindmap 聚合）。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| 统计口径需先定义再编码 | 设计工件内置口径表（statistics_service docstring + design-spec） | 本批 design-spec |
| dashboard 执行 0 根因=按类型子查询带 is_deleted | 已修复并回写测试 | test_batch149_statistics.py |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h vs 实际 2.5h | 0/0/0/0 | 0 | - | 统计先口径表再编码 |

**技能使用**: cameltv-agent-team 流水线；audit-ai-pr（推送后执行）
