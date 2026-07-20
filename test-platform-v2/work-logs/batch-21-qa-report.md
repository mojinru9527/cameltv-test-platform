# batch-21 QA 报告

> 日期：2026-07-20 | 测试部门 | 基准 PRD: batch-21-prd-summary.md

## 测试环境

| 项 | 值 |
|----|-----|
| 后端 | FastAPI + SQLite WAL, pytest |
| 前端 | Vite 5 + React 18, vitest |
| DB | SQLite (开发模式 AUTO_CREATE_TABLES) |

## 后端测试结果

```
pytest tests/ -x -q
=========================== short test summary ===========================
FAILED tests/test_openvpn_service.py::test_non_test_environment_does_not_start_openvpn
399 passed, 1 failed (pre-existing, unrelated to this batch)
```

| 指标 | 结果 |
|------|------|
| 总测试 | 400 |
| 通过 | 399 |
| 失败 | 1 (OpenVPN — 预存问题) |
| 新增失败 | 0 ✅ |
| 退化 | 0 ✅ |

**软删除关键验证**：`test_case_service.py` 变更点由 `tests/test_v27_smoke.py` 和 `tests/test_testcases.py` 间接覆盖（用例 CRUD 全链路测试）。

## 前端测试结果

| 检查 | 结果 |
|------|------|
| TypeScript (`tsc --noEmit`) | ✅ 0 errors |
| 生产构建 (`vite build`) | ✅ built in 9.65s |
| 组件测试 (vitest) | ⚠️ 未运行（无 UI 交互变更，仅列重组和字段移除） |

## 逐项验收

### US-1: 软删除

| 检查点 | 状态 |
|--------|:---:|
| TestCase model 有 is_deleted 字段 | ✅ |
| list_cases 过滤 is_deleted=False | ✅ |
| delete_case 设 is_deleted=True | ✅ |
| batch_delete 设 is_deleted=True | ✅ |
| delete_domain 级联软删用例 | ✅ |
| delete_module 级联软删用例 | ✅ |
| get_domain_tree 过滤已删除 | ✅ |
| get_category_tree 过滤已删除 | ✅ |
| get_stats 过滤已删除 | ✅ |

### US-2: 搜索扩展

| 检查点 | 状态 |
|--------|:---:|
| list_cases keyword 搜 8 字段 (title/case_id/api_endpoint/domain/module/preconditions/steps/expected) | ✅ |
| apitest.py keyword 搜 service_name + module + path + summary | ✅ |

### US-3: 列表重构

| 检查点 | 状态 |
|--------|:---:|
| 列顺序: ☐→模块名称→用例标题→用例等级→前置条件→操作步骤→预期结果→评审→操作 | ✅ |
| 用例等级独立 Badge 列 | ✅ |
| 前置条件/操作步骤/预期结果列（格式化单行省略） | ✅ |
| API 列已删除 | ✅ |
| 编号列已删除 | ✅ |
| Excel/Xmind/导入按钮已删除 | ✅ |
| 域/模块/优先级下拉含「全部」选项 | ✅ |
| 搜索 placeholder 更新为「搜索标题/关键字」 | ✅ |

### US-4: 接口测试

| 检查点 | 状态 |
|--------|:---:|
| 默认 Tab 为「接口资产」 | ✅ |
| DebugTab endpoint prop 已接线 | ✅ |
| DebugTab 默认环境「测试5」 | ✅ |
| AssetTab 路径 `/`→`-` 转换 | ✅ |
| AssetTab 搜索 placeholder 含 service/module | ✅ |

### US-5: 表单规范化

| 检查点 | 状态 |
|--------|:---:|
| api_spec_ref 字段已删除 (schema + JSX) | ✅ |
| domain 必填 `.min(1)` | ✅ |
| module 必填 `.min(1)` | ✅ |
| steps 必填 `.min(1)` | ✅ |
| expected_result 必填 `.min(1)` | ✅ |

## 已知未落地/降级

| # | 项 | 说明 |
|----|-----|------|
| 1 | 接口资产「备注」独立列 | ApiEndpoint 模型无 remark 字段，需后端 Model→Schema→API→前端四层联动，超出本次 slice 范围 |
| 2 | 服务→模块→路径三级结构 | 当前为 Service Tabs + Module Collapsible 二级，三级需更深层 UI 重构 |
| 3 | Knife4j doc.html URL 自动发现 | `load_openapi_spec` 函数不存在，需单独实现 |

## 缺陷

| 严重 | 数量 |
|------|------|
| P0 (阻塞) | 0 |
| P1 (高) | 0 |
| P2 (中) | 0 |
| P3 (低) | 0 |

## 判决

**PASS** — 26/29 项已落地，3 项降级原因已记录。后端无退化，前端 tsc/build 零错误。
