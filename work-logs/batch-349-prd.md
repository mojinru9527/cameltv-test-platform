# Batch 349（M10-4：学习候选/BugPattern Console API）— PRD / Design / Dev

> mode: **full**（新接口 + 权限点）· 分支：`feature/batch-349-learning-api` · 基线：`origin/main 44b658202`
> 说明：M10-346/347/348 受外部环境阻塞（future-wayu / 真机 / IoT），先执行不依赖外部环境的 349。

## 1. 背景

A6 Learning Curator 的服务层已具备 `draft→benchmarked→approved→active` 状态机与误报率门禁，
但没有 HTTP API/Console 入口：

- 学习候选只能脚本创建、脚本批准；
- BugPattern 无查询入口，无法确认规则是否已生效；
- 审批权限与 Workflow 审批混用同一点，无法区分"图审批"和"学习规则发布"。

## 2. 目标

1. `POST/GET /api/v1/aiqe/learning/candidates`：创建/列表学习候选；
2. `POST /candidates/{id}/evaluate`：写入 benchmark（误报率 + 样本量）；
3. `POST /candidates/{id}/approve`：人工批准（新权限 `aiqe:learning:approve`，默认仅管理员）；
4. `POST /candidates/{id}/activate`：激活为 BugPattern；
5. `GET /api/v1/aiqe/learning/bug-patterns`：查询已激活规则；
6. 全部沿用 `menu:aiqe_runs` 门禁；误报率 >20% / 未 benchmark 直接批准 → 400。

## 3. 设计

| 点 | 实现 |
|----|------|
| 服务 | 复用 `learning_service`（create/evaluate/approve/activate）；新增 `list_bug_patterns` |
| 权限 | seed 新增 `aiqe:learning:approve`（button，默认仅管理员 `*`） |
| 错误 | `LearningError` → 400（含误报率、重复候选、状态机顺序） |
| 路由 | `api/v1/aiqe_learning.py`；路由层不碰 ORM |

## 4. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 创建/列表 | `test_create_and_list_candidate` |
| A2 | 全状态机 + BugPattern 生成 | `test_evaluate_and_approve_and_activate` |
| A3 | 误报率 35% 拒绝批准 | `test_high_false_positive_rate_rejected` |
| A4 | 无 `aiqe:learning:approve` → 403 | `test_approve_requires_dedicated_permission` |
| A5 | 未 benchmark 先批准 → 400 | `test_approve_before_benchmark_rejected` |
| A6 | 空 pattern / 无菜单权限拒绝 | 2 条 |
| A7 | 路由基线 +6 | `test_route_inventory` |

## 5. 风险

| 风险 | 等级 | 处置 |
|------|:----:|------|
| 误报率门禁被绕过 | 低 | 服务层 fail-closed；API 只透传 |
| 重复候选静默发布 | 低 | `duplicate_of` + `acknowledge_duplicate` 既有语义保留 |
| 学习规则污染现有用例 | 中 | 仅生成 BugPattern，供人工/A6 后续消费；本批不自动改写用例 |
