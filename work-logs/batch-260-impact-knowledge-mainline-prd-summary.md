# Batch 260 — PRD Summary

> **Product (🟦)** | Date: 2026-09-19 | Status: Review
> **批次档位**: 完整批次（六件）

## 0. 批次模式判定

```text
mode: full
判定依据: 数据模型变更（B3-1 新增 ImpactEdge + Alembic 迁移）+ 新接口（B3-3 影响面查询 API）+ 前端行为变更（B3-5 知识中心 Tab 收敛）
豁免记录: 无
```

## 1. 问题陈述

09 方案 §2.4 把知识库收敛成**一个问题**：「这个版本改了哪些需求/功能模块 → 要跑哪些用例 → 上次跑得怎么样？」

开工前的只读侦察发现一件必须写进 PRD 的事实：**B3 的大部分能力已经以 B11/B12 的形式存在**，但它们各说各话，没有回答上面这个问题。逐条实测（`main@573f5c12`）：

| 已有实现 | 它回答的问题 | 与 B3 的关系 |
|---|---|---|
| `app/services/api_change_impact_service.py:186` `analyze_openapi_change`（已接入 `api/v1/apitest_cases.py:186`） | **接口级**：OpenAPI diff → 变更清单 + 受影响用例 + 建议 | 输入是两份 spec，不是"改了哪个模块"；粒度是端点 |
| `app/api/v1/trace.py` 的 `/coverage`、`/case/{id}`、`/requirement/{doc_id}` | 覆盖率矩阵、用例追溯、需求覆盖率 | 三个分散的只读视角，不是"改了 X 要跑哪些" |
| `app/api/v1/interaction_coverage.py:27` 的 `/gaps` | 交互拓扑边 vs 用例的**未覆盖边** | 有"缺口"概念，但基于 InteractionEdge（3172 条），与需求变更无关 |
| `GET /version-tasks/knowledge/reuse` + `version_task_service.get_reuse_suggestions:601` | **B11 复用建议**：上一版知识记录 → 下版建任务自动带出 | B3-4 的主体**已存在**；缺的是命中率埋点 |
| `version_task_service.py:638`（B12 推荐回归集） | 建任务即给推荐回归集（采纳方案条目 + 变更模块 + 上版复用建议） | 已部分回答"要跑哪些" |
| `app/models/interaction_edge.py`（3172 条边） | 交互拓扑（from_module/entry/to/evidence） | **`ImpactEdge` 不存在**；新建时必须先讲清两者关系 |
| 知识中心 `NORMAL_KNOWLEDGE_TABS` = 5 个（project/platform/versionrecords/reuse/search） | — | 该文件自己的 docblock 写「普通用户只读 3 Tab」→ **代码与自己的注释已经不一致** |

一句话：**B3 不是"从零建知识主线"，而是"把已有的 B11/B12/影响面/追溯/缺口拼成一条主线，并把缺的那一段补上"**——缺的是"需求↔模块↔用例"的边图、统一查询、以及复用命中率。
PRD 口径：凡是已存在的都必须收敛复用；重复造会立刻产生第二份"影响面实现"，这正是审计 S1（守卫存两份）与 S5（密钥派生两套）的同一个失败模式。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 「改了 X 要跑哪些」可用 | 不存在（只有接口级 diff 与分散 trace） | 输入变更模块 → 用例集 + 最近结果 + 缺口，一次返回 | 本批 |
| 查询响应 | — | ≤2s（B3-3 DoD） | 本批 |
| 体育试点模块关联覆盖率 | 未知 | ≥90%（B3-2 DoD） | 本批（由回填脚本产出证据） |
| 复用命中率可统计 | 不可统计 | 有埋点且可聚合（B3-4 DoD；≥50% 进入 B4 验收） | 本批 |
| tester 知识中心 Tab | 5 | ≤3（B3-5 DoD） | 本批 |
| 影响面实现份数 | 1（接口级） | 仍 1 份：新查询复用既有服务，不新建平行实现 | 本批 |

## 3. 非目标（本次不做）

- **不合并** `ImpactEdge` 与 `InteractionEdge`：前者是"变更/覆盖/依赖"，后者是"交互拓扑（页面/入口跳转）"，语义不同。本批只要求在模型 docstring 写明两者关系与各自用途，禁止互相冒充。
- **不重做** B11 复用建议与 B12 推荐回归集：只补命中率埋点与聚合。
- **不改** `analyze_openapi_change` 的接口级语义（已被 apitest 页面使用）；新查询需要时**调用它**，不复制其逻辑。
- **不引入新的知识玩法**：图谱/实体/迭代/Wiki/差异对比/Skills 全部保持原样，只对 tester 收起。
- **不做 B4 的证据包定型**（仍属 B4-1）。

## 4. 用户故事 + 验收标准

- As a 测试工程师, I want 输入"这版改了 X 模块"就得到该跑哪些用例, so that 我不用凭经验猜回归范围。
  验收：Given 变更模块 X 与历史执行数据 / When 调用查询 / Then ≤2s 返回「受影响模块 → 关联用例（功能/接口/UI）→ 最近一次执行结果 → 未覆盖缺口」，且每条结论都能点回原始用例/执行记录。

- As a 版本负责人, I want 复用建议的命中率可统计, so that 我能判断"上一版经验是否真的被用上"。
  验收：Given 下版任务带出复用建议 / When 人工采纳或否掉 / Then 埋点落库且可聚合出命中率。

- As a 测试工程师, I want 知识中心只看到我需要的 3 个页签, so that 我不用在一堆引擎概念里找入口。
  验收：Given tester 登录 / When 打开知识中心 / Then Tab ≤3；管理类 Tab 需权限才可见。

## 5. 技术考量

- **B3-1 的边怎么建**：`ImpactEdge(source_ref, target_ref, kind, version, confidence)`，kind ∈ {changed, covers, depends}；与 `InteractionEdge` 的关系写在模型 docstring。
- **B3-2 的关联从哪来**：需求变更→模块 复用既有 `knowledge/version_differ` 与 `requirement_module_service`；模块→用例 复用既有 `knowledge/test_case_linker`。先用规则 + 既有数据回填，不引入新的猜测模型。
- **B3-3 的查询**：一次查询拼三段（关联用例 / 最近执行 / 缺口），复用 `version_coverage_service`、`trace`、`interaction_coverage` 的能力，不新建平行的覆盖计算。
- **B3-5 的判据**：以该文件自己的 docblock（3 Tab）为准，把漂移进来的 `versionrecords/reuse` 收敛进主线视图或维护视图，并补断言防回涨。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批合入 main | 平台研发 | required checks 全绿 + Leader APPROVED |
| 随发布火车上 test | 测试团队 | 迁移生效 + 查询走查 |
| B4 | 试点 | 复用命中率 ≥50% 进入 SLO 验收 |

## 7. 技能使用

- `cameltv-bug-guard` → 开工前对照「未关闭已知风险」表；本次重点核对"同一能力存两份"的复发风险（S1/S5 模式），结论落在 §1 与 §3（非测试证据）。
- `cameltv-agent-team` → 批次档位与工件骨架（非测试证据）。
