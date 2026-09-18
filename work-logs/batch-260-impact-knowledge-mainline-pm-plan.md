# Batch 260 — PM Plan

> **PM (🟨)** | Date: 2026-09-19
> 对应 PRD: [batch-260-impact-knowledge-mainline-prd-summary.md](batch-260-impact-knowledge-mainline-prd-summary.md)

## 规格摘要

**原始需求**: `10-landing-plan-task-backlog.md` §2「B3」表 B3-1…B3-5。
**范围纪律**: 只做 B3 表内任务；B4（3 版本验收）不在本批。**凡是既有能力必须复用，不新建平行实现**（PRD §1 §3）。

## 开发任务

### [ ] Task 1: ImpactEdge 模型 + 迁移（B3-1）
**描述**: 新增 `impact_edge` 表与 `ImpactEdge` 模型：`source_ref / target_ref / kind(changed|covers|depends) / version / confidence / (project_id)`；
Alembic 迁移单头可逆。模型 docstring 必须写明与 `InteractionEdge` 的分工，禁止互相冒充。
**验收标准**: 迁移单头、from-base 可升级可降级；kind 非法被拒；同 (source,target,kind,version) 唯一。
**涉及文件**: `app/models/impact_edge.py`（新）、`app/models/__init__.py`、`alembic/versions/*`、`tests/test_batch260_impact_edge.py`
**参考**: PRD §1 §5；backlog B3-1 DoD「迁移单头、可离线校验」

### [ ] Task 2: 关联构建（需求变更 → 模块 → 用例）（B3-2）
**描述**: 新增 `impact_graph_service.build_edges()`：从既有数据（`knowledge/version_differ`、`requirement_module_service`、`knowledge/test_case_linker`、用例的模块归属）
生成 changed/covers/depends 三类边；提供回填脚本对体育试点模块跑一次并输出关联覆盖率。
**验收标准**: 体育试点模块关联覆盖率 ≥90%（脚本输出可见）；重复构建幂等（同键不重复插入）。
**涉及文件**: `app/services/impact_graph_service.py`（新）、`backend/scripts/backfill_impact_edges.py`（新）、测试
**参考**: PRD §5

### [ ] Task 3: 查询 API「改了 X 要跑哪些」+ 未覆盖缺口（B3-3）
**描述**: 新增只读查询：输入变更模块（或版本 + 模块）→ 返回受影响模块 → 关联用例（功能/接口/UI）→ 最近一次执行结果 → 未覆盖缺口；
每条结论带可回溯引用（case_id / run_id / defect_id）。复用既有 `version_coverage_service`、`trace`、`interaction_coverage` 的能力，不新建覆盖计算。
**验收标准**: 响应 ≤2s；结论可点回原始用例/执行记录；无数据时明确返回"无关联"而非空对象。
**涉及文件**: `app/services/impact_query_service.py`（新）、`app/api/v1/impact.py`（新）、`app/api/v1/router.py`、路由基线
**参考**: PRD §2 §5

### [ ] Task 4: 复用建议命中率埋点（B3-4）
**描述**: 既有 B11/B12 复用建议**已存在**，本任务只补命中率：记录"带出的建议"与"人工采纳/否掉的结果"，并提供聚合接口（命中率 = 采纳/带出）。
**验收标准**: 埋点落库；可聚合出命中率；不改变既有 `get_reuse_suggestions` 的返回契约（新增字段而非改语义）。
**涉及文件**: `app/models/version_knowledge.py`（或新增埋点表）、`app/services/version_task_service.py`、`app/api/v1/version_task.py`、测试
**参考**: PRD §1 §3

### [ ] Task 5: 知识中心 Tab 收敛 ≤3（B3-5）
**描述**: 以 `src/pages/knowledge/index.tsx` 自己的 docblock（3 Tab）为准，把漂移进来的 `versionrecords/reuse` 收敛进主线视图或维护视图；
修复 docblock 与代码不一致；补 `tester Tab ≤3` 断言防回涨。
**验收标准**: tester Tab ≤3；管理类 Tab 需权限；被收起 Tab 的路由/权限仍在（隐藏 ≠ 删除）。
**涉及文件**: `frontend/src/pages/knowledge/index.tsx`、相关测试
**参考**: PRD §4；02 白名单 §3

## 质量要求

- [ ] 单元测试覆盖  - [ ] 无障碍（ARIA/键盘）  - [ ] 无 console 报错/告警
- [ ] 提交前 `pwsh scripts/git/dev-gate.ps1`：G0–G2 无 HARD/类型/守卫失败
- [ ] 每切片只 `git add` 本切片文件
- [ ] 新增路由同步 `tests/fixtures/route_inventory.json`
- [ ] **提交前本地跑 `python scripts/ci/quality_ratchet.py`**（B1/B2 各因新增 RUF100/mypy 项失败一次，本地预跑可省一轮 CI）
- [ ] 前端全量本地用 `--maxWorkers=2`（本机 OOM 已知）
