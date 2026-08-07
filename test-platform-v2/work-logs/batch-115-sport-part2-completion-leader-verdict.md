# Batch 115 — Leader Verdict（Part 2 全部解决）

> **Leader (🎯)** | Date: 2026-08-07 | Decision: **APPROVED（有条件，C115-1/2/4 部署后验证）**

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 完整批次；7 项 Part 2 全覆盖（UI 定时/接口依赖/XHR 采集/知识导入/Runner/口径/生成链路） |
| 实现质量 | PASS | B112-3 7 单测 + C107-2 4 单测 + 注入 4 单测；迁移单头；前端 typecheck/build + 19 vitest |
| 证据 | PASS | 知识 capture source#31、981 XHR 样本含请求头、采集/注入证据、回归 37 passed |
| 诚实性 | PASS | 平台级验证登记部署后（C115-1/2/4）；B112-1 外部口径如实待确认；B10 平台 API 集成登记 C115-3 |

## 关键决策（已批准）

1. B112-3 采用「UI job 自带 cron + schedule job_type=ui」方案，UI 页一处配置、调度器复用 APScheduler。
2. C107-2 依赖链执行前置用例并注入 `$prev.{id}.{path}`，拓扑+环检测；场景用例落库待部署后实跑。
3. B10 以采集脚本交付（立即可用 + 981 样本证据），平台 API/UI 集成登记 C115-3（P3）。
4. 生成链路在 functional 提示注入关联基座（用户方向闭环）。

## 抽检通过

- ✅ `test_batch115_ui_schedule.py` 7/7（create/update ui、联动禁用、plan 校验）
- ✅ `test_api_dependency_chain.py` 4/4（注入/缺失/环/单请求）
- ✅ `test_association_baseline_injection.py` 4/4（基座命中/提示注入）
- ✅ 回归 37 passed + ruff F821 + alembic 单头
- ✅ 前端 typecheck/build + uitest vitest 19/19
- ✅ 知识 capture source#31 + 981 XHR 样本（含请求头）

## 判决

**APPROVED（有条件通过）**：一次总确认 → push → Draft PR → checks → 合入 main →
部署后执行 C115-1（UI 定时任务触发 10/10）、C115-2（场景链 depends 回填+实跑）、C115-4（交互 job 连续 2 次 10/10）。

## 下一批次 Leader 条件

- C115-1（P1）：部署后创建 UI 定时任务（cron 每日）并触发核对 10/10（B112-3 平台验证）。
- C115-2（P2）：部署后回填场景用例#1833 depends_on_ids 并实跑串联（C107-2 平台验证）。
- C115-3（P3）：B10 采集工具平台 API/UI 集成。
- C115-4（P2）：平台交互 job 连续 2 次 10/10（B114-2 平台验证）。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| UI job 无法定时 | schedule job_type=ui + UI job cron | `schedule_service/ui_test_service` + C115-1 |
| 接口用例无串联 | depends_on_ids + $prev 注入 | `api_execution_service` + C115-2 |
| XHR 样本缺请求头 | 采集脚本含 headers | `capture-page-xhr.py` + C115-3 |
| 生成不消费关联基座 | functional 提示注入 | `association_baseline.py` |
| 本地依赖漂移（deep-eql） | npm ci 修复 | B115-1 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 2d / 实际 1d | 0/0/0/2 | 2 | 工具链 | 大功能批次先拆后端单测再合前端；DB 列依赖迁移先确认部署窗口 |

**技能使用**：`cameltv-agent-team`、`cameltv-bug-guard`、`playwright-cli`、`test-case-design`。