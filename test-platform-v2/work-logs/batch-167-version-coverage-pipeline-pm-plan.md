# Batch 167 — PM Plan
> **PM (🟨)** | Date: 2026-08-13

## 规格摘要
**原始需求**: 版本级三类型模块覆盖主链路 Phase 0–3（覆盖矩阵 / 需求源适配与完整提取 / 接口真实绑定 / 功能→UI 自动执行与计划三类型关联）。
**目标时间**: 本批次一次交付，全部落地后才推送合并。

## 开发任务（按依赖排序）

### [ ] Task 1: Schema 迁移
**描述**: 一次性迁移 `requirement_document.source_url/extraction_meta`、`release_bundle` 五个接入字段、`version_mission.api_spec_url`；模型与 schema 同步。
**验收标准**: - `alembic heads` 单头；fresh DB 可建表；旧 DB upgrade 不丢数据。
**涉及文件**: `backend/app/models/requirement.py`、`models/release_bundle.py`、`models/version_mission.py`、`schemas/requirement.py`、`schemas/release_bundle.py`、`schemas/version_mission.py`、`alembic/versions/20260813_b167_*.py`
**参考**: PRD §5

### [ ] Task 2: 版本级覆盖矩阵（Phase 0）
**描述**: `version_coverage_service` 计算 bundle 模块 × 三类型 × 执行状态矩阵与覆盖率；API `GET /release-bundles/{id}/coverage`。
**验收标准**: - 每模块返回 func/api/ui 用例数、执行数；all-three 覆盖率与 60% 门禁字段；空模块树返回空矩阵。
**涉及文件**: `backend/app/services/version_coverage_service.py`、`api/v1/release_bundles.py`、`schemas/release_bundle.py`
**参考**: PRD §4 用户故事 1

### [ ] Task 3: 需求源适配与完整提取（Phase 1）
**描述**: `requirement_source_service` 支持 generic HTML / PingCode / Confluence URL 抓取（token 走 settings，缺则 fail closed）；upload 接受 `source_url`；`ai_service` 大文档分块提取与合并；`extraction_meta` 记录 mode/truncated/fallback/chunk 数；`GET /requirements/{id}/extraction-quality`。
**验收标准**: - 超时/403/HTML 解析失败错误分类；分块合并去重 FP；降级/截断在 meta 透出。
**涉及文件**: `backend/app/services/requirement_source_service.py`、`services/ai_service.py`、`api/v1/requirement.py`、`schemas/requirement.py`、`core/config.py`
**参考**: PRD §4 用户故事 2/3

### [ ] Task 4: 接口用例绑定真实端点（Phase 2）
**描述**: `POST /requirements/{id}/generate-api-from-endpoints`：对 integration FP 用 match_api_endpoints 定位已导入端点，再用确定性生成器生成用例并回填 `requirement_module_id`/module/断言，幂等 upsert，回写 linked_api_endpoint_ids。
**验收标准**: - 端点存在时生成真实 method/path 与 schema 断言；无端点 fail closed；重复调用不重复建用例。
**涉及文件**: `backend/app/services/requirement_service.py`、`services/api_case_generation_service.py`、`api/v1/requirement.py`
**参考**: PRD §4 用户故事 4

### [ ] Task 5: 功能→UI 变体与计划三类型关联（Phase 3a）
**描述**: `generate_ui_cases_from_functional` 为 P0/P1 有步骤功能用例创建 case_type=ui 变体并关联模块；`import_cases(create_ui_cases=True)` 创建计划时三类一起关联。
**验收标准**: - UI 变体继承 title/module/steps 与模块关联；幂等；计划含三类。
**涉及文件**: `backend/app/services/case_generation_service.py`、`services/requirement_service.py`
**参考**: PRD §4 用户故事 5

### [ ] Task 6: 计划 auto_ui 执行（Phase 3b）
**描述**: `execute_all_cases(auto_ui=True)`：UI 用例用 LLM 优先编译执行；manual P0/P1 有步骤自动转 UI；失败如实落库；回写 UiTestJob；无步骤才 skip。路由与前端开关。
**验收标准**: - 有步骤 manual 不再 skip；LLM 未配置时回退规则引擎；TODO 编译失败不伪造 pass。
**涉及文件**: `backend/app/services/test_plan_service.py`、`api/v1/test_plan.py`、`schemas/test_plan.py`
**参考**: PRD §4 用户故事 6

### [ ] Task 7: 前端接入（Phase 0–3 UI）
**描述**: 版本详情覆盖面板与接入配置字段；需求页提取质量徽标与「按已导入接口生成接口用例」按钮；AiResultModal 创建计划默认生成 UI 变体；计划页 auto_ui 开关。
**验收标准**: - typecheck/build/vitest 全绿；无 N+1；useEffect 有 cleanup；无 console 报错。
**涉及文件**: `frontend/src/api/releaseBundles.ts`、`api/requirement.ts`、`pages/release-bundles/BundleDetail.tsx`、`pages/requirement/AiResultModal.tsx`、`pages/requirement/index.tsx`、`pages/testplan/PlanDetail.tsx`、`types/api.d.ts`
**参考**: PRD §4；cameltv-ui-conventions

## 质量要求
- [ ] 后端 ruff F821 / app import / alembic 单头 / 受影响 pytest
- [ ] 前端 typecheck / build / vitest 全量
- [ ] 无调试遗留、无硬编码密钥；新增依赖同步 requirements.txt（本批不新增运行时依赖）
- [ ] 每切片本地 commit，总确认前不 push
