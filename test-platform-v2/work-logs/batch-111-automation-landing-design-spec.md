# Batch 111 — Design Spec（体育平台自动化落地）

> **Design (🎨)** | Date: 2026-08-06 | Status: Review

## 1. 后端回填设计（核心，C110-3/C103-7）

`api_task_worker.execute_task` 的 item 执行分支（`item.status = passed/failed` 处）追加：

```python
# 回填用例详情「请求结果」（Batch 111）
case = db.get(TestCase, item.case_id)
if case:
    case.last_response_json = _build_response_snapshot(result) if not result.get("error") else json.dumps(
        {"error": result["error"]}, ensure_ascii=False)
    case.last_run_status = item.status
    db.add(case)
```

- 复用 `_build_response_snapshot`（status/headers/body_preview/body_size/truncated）。
- `last_run_status` 取值 `passed|failed`（与用例详情徽标口径一致）。
- 失败（POLICY_DENIED/断言失败）也回填错误快照，保证「执行过必有结果」。

## 2. 前端链路（验证为主）

| 环节 | 现有 | Batch 111 |
|------|------|-----------|
| 选用例建任务 | apitest TasksTab | 验证可直接跑（若缺「从用例列表勾选→建任务」入口则补） |
| 任务结果 | TasksTab 列表 | 验证通过率/失败明细 |
| 用例详情 | CaseDrawer「接口数据」Tab（请求参数/断言/请求结果） | 验证批量执行后 last_response 可见 |

## 3. 生产批量执行参数

```text
POST /api/v1/apitest/tasks
{ case_ids: [170 条 api 用例 id], environment_id: 体育平台-生产, confirm_prod: true, name: "体育平台-批量执行-Batch111" }
轮询 GET /apitest/tasks/{id} 至终态；核对 TestCase.last_run_status 分布。
```

## 4. UI 定时回归

```text
POST /ui-tests { name:"体育平台-P0-每日生产只读回归", test_spec:"specs/production-p0-modules.spec.ts",
                 browser:"chromium", environment_id: 体育平台-生产 }
POST /schedules { name:"体育平台-P0-每日回归", cron_expression:"0 2 * * *", ...（按平台 schedule 绑定 ui job/plan）}
POST /schedules/{id}/trigger → 运行报告
```

## 5. wiki 差异评审

```text
GET  /wiki/diff/tasks?page_size=50 → 10 组任务
GET  /wiki/diff/tasks/{id} → items
POST /wiki/diff/items/{id}/accept|reject（评审）
POST /wiki/diff/items/{id}/create-artifact {artifact_type:"test_case"|"business_rule"|...} → pending AiArtifact
```

## 6. Test5 契约补拉 / CI

- konfi-service/admin-service：Test5 Swagger 拉取 OpenAPI → `/apitest/import/preview|confirm`；
  内网不可达 → Deferred 登记（保留证据）。
- api-regression：审查 workflow 触发条件（push 是否应触发）+ runner（internal-network）配置；
  Test5 恢复后本地/CI 验证一次。

## 7. 设计走查

本期 UI 改动以验证为主（如需新增按钮则按 shadcn/ui 规范）；后端改动集中在 worker 回填（无 schema 变更）。
