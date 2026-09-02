# Batch 213 后端全量回归摘要（2026-09-02）

命令：`python -m pytest tests -q --disable-warnings`

结果：**2362 passed, 49 skipped, 1 xfailed, 1 baseline failed**（2413 collected，运行 9m13s）

本批新增路由 `/api/v1/dashboard/todo` 导致 `tests/test_route_inventory.py::test_route_paths_match_baseline`
失败 → 已更新 `test-platform-v2/backend/tests/fixtures/route_inventory.json`（count 607→608，加入该路由）
并复跑通过（`pytest tests/test_route_inventory.py -q` → 1 passed）。

剩余 1 个失败为**独立于本批的基线失败**（非本批引入）：
- `tests/test_batch148_p0_fixes.py::TestExecutionErrorFields::test_execute_all_records_error_fields`
  → `sqlite3.OperationalError: no such table: notification_channel`
  → 该测试 fixture 未创建 `notification_channel` 表，与本批无关（本批未改 execution/notification 模块）；
   独立复跑同样失败，判为 pre-existing 基线。

结论：本批无新增失败。硬门禁（ruff F821 + 受影响 pytest + app 导入）全绿。
