# Batch 168 — PM Plan
> **PM (🟨)** | Date: 2026-08-13

## 规格摘要
**原始需求**: 修复 Batch 167 真实复测 D1–D8，使 16.0.0 三类型覆盖 ≥60%。
**目标时间**: 1 个批次内完成（约 6h）。

## 开发任务
### [ ] Task 1: 覆盖矩阵逐模块聚合（D1/D2）
**描述**: version_coverage_service 用 (module_id,module_name,type) 键聚合；fallback 优先 bundle 绑定需求文档的用例模块，再回退项目 distinct module；P0/P1 按模块自身 manual 用例优先级。
**验收标准**: 2 模块 3 类型混合场景逐行计数正确；fallback 同名模块不再共享全局计数。
**涉及文件**: app/services/version_coverage_service.py、tests/test_batch167_version_coverage.py(+168)

### [ ] Task 2: 接口生成 upsert 修复（D3）
**描述**: existing 查询加 is_deleted=false；模板变体独立成行（唯一键含 title），生成报告与可见数一致。
**验收标准**: 软删除行不被复活；7 变体=7 行；重复调用幂等。
**涉及文件**: app/services/requirement_service.py

### [ ] Task 3: UI 变体回填（D4）
**描述**: create_ui_cases=True 时扫描 source_doc_id 全部已导入 P0/P1 有步骤功能用例并幂等生成 UI 变体，不止本次新导入。
**验收标准**: 老数据重复 import 时 UI 变体生成且不重复。
**涉及文件**: app/services/requirement_service.py

### [ ] Task 4: 模块级端点匹配（D8）
**描述**: 模块名 token/双字重叠匹配已导入端点；未命中模块每模块绑定至多 1 个只读安全端点（confidence>=0.4），生成 basic/positive/negative 模板并回填模块。
**验收标准**: 16.0.0 18 模块中 ≥11 模块获得 API 用例；匹配只取真实端点。
**涉及文件**: app/services/requirement_service.py

### [ ] Task 5: 执行环境拆分 + 失败透出（D6/D7）
**描述**: ExecuteAllBody 增 ui_environment_id；_resolve_plan_base_url 支持 UI 环境；UI 失败 notes 含 error/exit_code/stdout 尾部。
**验收标准**: UI 用 ui 环境 base_url；失败 notes 非「未知」。
**涉及文件**: app/schemas/test_plan.py、app/services/test_plan_service.py、app/api/v1/test_plan.py

### [ ] Task 6: 前端修复（D5/D7）
**描述**: BundleDetail 修正 diff/coverage Tab 嵌套；PlanDetail 执行弹窗增加 UI 环境选择并透传 ui_environment_id；执行记录失败详情展示。
**验收标准**: 标签页显示「版本差异」「三类型覆盖」两个独立 tab；UI 环境选择可保存透传；typecheck/lint/build/vitest 全绿。
**涉及文件**: src/pages/release-bundles/BundleDetail.tsx、src/pages/testplan/PlanDetail.tsx、src/api/testplan.ts

## 质量要求
- [x] OpenAPI 同步（后端 schema 变更自动反映）  - [x] 后端 pytest 全量  - [x] 前端 vitest 全量
- [x] 无 console 报错  - [x] ruff F821 / typecheck / lint / build
