# Batch 210 — 收尾（C1b/C2b/测试基建）— QA 报告
> **QA (🔍)** | Date: 2026-09-02 | Verdict: READY（仅 1 项本地环境失败，CI 全绿）

## 测试总览
| 条件数 | 通过 | 失败 | 跳过 | 说明 |
|--------|------|------|------|------|
| 全量 backend pytest | 2359 | 1 | 49 | 失败=notification 本地环境项（CI 通过）；49 skip=lanhu/deploy 子模块缺失 |
| 定向 v33/v34/reality + lanhu/deploy | 249 | 0 | 44 | 全绿 |

## 可执行门禁
- ruff F821 exit 0；无迁移、无 API 路由变更
- 全量：2359 passed / 1 failed / 49 skipped / 1 xfailed（9m06s）——相比 Batch 209 的 6 项环境失败降为 1

## 逐条件
| 条件 | 结果 | 证据 |
|------|------|------|
| lanhu/deploy 子模块缺失 skip | PASS | 40 tests skipped（reason 明确）；CI 仍有子模块会执行 |
| C1b capability 观测 | PASS | test_batch209_execute_dispatch 3（capability false/true + runner）|
| C2b 单命令兜底物化 | PASS | test_batch209_materialize 5（幂等/approve/未匹配/兜底/多命令不臆测）|

## 缺陷列表
| # | 严重级 | 描述 | 状态 |
|----|--------|------|------|
| 1 | P3(环境) | notification_channel 本地 DB 环境失败（test_batch148） | CI 通过；本地随 DB 初始化消除，另批次可补本地 DB 预置 |
| 2 | P3(已修) | lanhu/deploy 无子模块硬失败 40 条 | 已转 skip |

## 发布建议
状态: READY。必修复: 0。

## 复盘卡
| 计划耗时 | 缺陷 | 返工次数 | 根因 | 下次避免 |
|----------|------|----------|------|----------|
| ~8h | 1(P3 环境) | 1 | 覆盖式写入误删既有测试 | 追加用 Add-Content/显式合并，覆盖前 git diff |

**技能使用**: cameltv-agent-team；cameltv-bug-guard；karpathy-guidelines；ADR-0025。
