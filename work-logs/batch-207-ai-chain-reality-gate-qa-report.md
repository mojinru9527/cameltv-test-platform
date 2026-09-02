# Batch 207 — AI 全链路 Reality Gate — QA 报告
> **QA (🔍)** | Date: 2026-09-02 | Verdict: READY（6 项环境/基线失败与本批次无关，见缺陷表）

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 | 说明 |
|--------|------|------|------|------|
| 全量 backend pytest | 2362 | 6 | 0 | 6 项均环境/基线：lanhu-mcp 子模块未初始化、notification 表夹具缺失 |
| 新增/相关单测 | 35 | 0 | 0 | S1-S6 新测试 + 相关目录回归全绿 |

## 可执行门禁（命令 + 退出码）
- `ruff check app --select F821` → exit 0（All checks passed）
- `python -m pytest -q`（backend 全量）→ 2362 passed / 6 failed / 9 skipped / 1 xfailed（9m06s）
- Alembic 单头：heads == [20260904_aitde_v40_governance] → 通过
- 前端未改动（scope=backend），不跑 typecheck/build；CI 按文件域自动跳过前端
- 相关目录回归：v31/v33/v34/v35/v38/v39/reality + scope/ambiguity/contract/scenario/ai_ops/ai provider 单测 → 全绿

## 逐条件验证（关键）
| 条件 | 结果 | 证据 |
|------|------|------|
| C1 AI provider 5 方法真调 LLM（mock） | PASS | tests/test_ai_intelligence_provider.py（10 passed）|
| C2 无 AI 配置确定性降级 + 既有测试全绿 | PASS | test_factory_gating + 相关 service 回归 |
| C3 溯源诚实（DETERMINISTIC vs AI） | PASS | tests/test_intelligence_runner_and_services.py（6 passed）|
| C4 ActionPlanner 服务端生成 + registry 校验 | PASS | test_batch207_trust_chain.py |
| C5 run fail-fast（PLAN_MISSING/ORACLE_NOT_BOUND） | PASS | test_batch207_trust_chain.py::test_oracle_binding_producer_and_fail_fast |
| C6 Oracle promote 显式信任升级 | PASS | test_batch207_trust_chain.py::test_review_oracle_promote_requires_explicit_flag |
| C7 闭环自动 triage + suggestion 生产者 | PASS | test_batch207_closed_loop.py（3 passed）|
| C8 ai_ops 生产者 + operation_id 回传 | PASS | runner/service 单测 + API 编译 |
| C9 路由漂移同步 | PASS | regenerate_route_inventory.py 后 test_route_inventory.py 通过 |
| C10 loader 报错可操作化 | PASS | test_batch207_loader_message.py |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|----|--------|------|------|------|
| 1 | P2(环境) | test_lanhu_provider/test_lanhu_login_hook：lanhu-mcp 子模块未初始化（FileNotFoundError lanhu_mcp_server.py） | 复跑输出 | 基线/环境，与本批无关 |
| 2 | P2(环境) | test_deploy_compose_contract：build context 依赖 lanhu 子模块文件 | 复跑输出 | 基线/环境 |
| 3 | P2(基线) | test_batch148_p0_fixes：夹具缺 notification_channel 表（sqlite OperationalError） | 复跑输出 | 测试夹具基线问题 |
| 4 | P2(已修) | test_route_inventory：新增 oracle-bindings 2 条路由 | 重生成后通过 | 已修复（合法新增） |

## 发布建议
状态: READY。必修复: 0。建议修复（另批次）: lanhu-mcp 子模块初始化、notification 夹具。

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~10h vs 单会话推进 | 0/0/1(环境)/0 | 2 | 大文件手工 patch 易碎（误删 def、引号未闭合） | 大块重写整文件重生成 + py_compile + 单文件 pytest 即时验证 |

**技能使用**: cameltv-bug-guard（StaticPool/别名导入/except 顺序）；karpathy-guidelines（小切片+验收标准）。
