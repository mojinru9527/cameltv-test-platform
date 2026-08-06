# Batch 107 — Leader Verdict（接口用例生成「测试考虑点」全量固化）

> **Leader (🎯)** | Date: 2026-08-06 | Decision: **APPROVED（待一次总确认）**

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 完整批次；范围=12 类缺失补齐（性能降优先级）+ 规范落盘 + 响应结构断言，无蔓延 |
| 实现质量 | PASS | 9 类新模板全部落地；真实样本响应结构断言（list_visible 35 条含业务断言）；AI 提示词注入检查清单 |
| 证据 | PASS | 生成器实测输出 + 54 pytest + 前端 typecheck/build/vitest + 生产 API 登录/知识库核实 |
| 诚实性 | PASS | 知识中心导入受阻（C102-2 409 复现）如实登记为 B107-1，未静默跳过 |
| 门禁 | PASS | pytest 54 / ruff / tsc / build / vitest 3 / alembic 单头 / scan HARD 0 / boundary PASS |
| 风险 | 低 | 场景测试为待关联模板（接口关联能力另批）；知识导入依赖 C102-2 |

## 关键决策（已批准）

1. 「测试考虑点」XMind（101 节点）固化为 `tests/test-case-standards/接口测试考虑点【辅助作用】.md`，作为接口用例生成/评审统一事实源。
2. 规则生成器新增 9 类模板（smoke/scenario/extra_param/security_ext/performance_low/data_test/stability/compatibility/monitoring），默认模板集 15 项；性能按用户指示 P2/P3 低优先级。
3. 真实样本生成器消费响应结构（envelope/data/record_count/核心字段/hints），把「返回值校验【必选】」从仅状态码升级为业务断言。
4. AI 提示词（api_cases）注入接口检查清单，断言要求升级为「状态码 + 响应结构/关键字段 + 业务规则」。
5. 知识中心导入受阻登记 C107-1（C102-2 复现），待 capture 去重修复后导入；场景测试关联登记 C107-2。

## 抽检通过

- ✅ 生成器实测：真实样本 35 条（positive/response_structure/smoke 3 条含业务断言）；默认模板 18 条覆盖全部新场景
- ✅ 单测 54/54（含新 10 条）；ruff F821 0；前端 tsc/build/vitest 3 全过
- ✅ 规范文档与 XMind 101 节点对应（CLAUDE.md/api-checklist 引用同步）

## 判决

**APPROVED**：进入一次总确认 → push → Draft PR → required checks → 合入 main。

## 下一批次 Leader 条件

- C107-1（P1）：知识中心 capture 409 去重误判修复（C102-2 落地）后，将 `tests/test-case-standards/接口测试考虑点【辅助作用】.md` 导入生产知识中心（sportsadmin，项目 1），导入后 sources 列表可见。
- C107-2（P2）：接口关联能力（依赖接口/前置接口配置）上线后，场景测试模板从「待关联」升级为真实多接口串联用例。
- 沿用 C103-5（真实样本批量采集 ≥20 接口）、C103-6（AI 块级截断补全）、C102-1~5、C99-1、C96-1、C95-1/C74-2、CP-C2/C84-1。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 「测试考虑点」此前只有飞书/XMind 未落盘，生成器未覆盖 | 规范落盘 + 生成器 9 类模板 + AI 提示词注入 | `tests/test-case-standards/接口测试考虑点【辅助作用】.md` + `api_case_generation_service.py` + `ai_service.py` |
| 真实样本已含响应结构但生成器不消费，断言仅状态码 | 消费 envelope/data/record_count/hints 生成业务断言 | `_response_structure_assertions` + real_sample 生成器 |
| 知识中心 capture 409 复现（C102-2） | 登记 C107-1 障碍，规范先落盘仓库 | C-CONDITIONS + QA B107-1 |
| 单接口生成器无接口关联图谱 | 场景测试先出「待关联」模板，登记 C107-2 | `_build_scenario_cases` + C-CONDITIONS |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/0/2/0 | 0 | 外部依赖+平台障碍 | 知识导入先行探测 capture；场景测试需接口关联数据 |

**技能使用**：`cameltv-agent-team`、`test-case-design`。
