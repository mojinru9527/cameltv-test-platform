# Batch 115 — PM Plan（Part 2 全部解决）

> **PM (🟨)** | Date: 2026-08-07

## 规格摘要

**原始需求**: PRD §1（C107-1/B112-3/C107-2/B10/B114-2/B112-1/生成链路 7 项）
**目标时间**: 2 开发日
**执行器**: codex（用户确认延续）

## 开发任务

### [ ] Task 1: 工件 + C107-1 知识导入 + B114-2 Runner 加固
**描述**: 写 PRD/PM/Design/看板；capture 导入「接口测试考虑点」文档；playwright_executor chromium
launch args 加固（--disable-dev-shm-usage 等）。
**验收标准**: capture code=0 + sources 可见；平台交互 job 连续 2 次 10/10。
**涉及文件**: - `scripts/sports/sync-case-standards.py`（新增）— 考虑点文档入库
            - `backend/app/services/playwright_executor.py` — launch args

### [ ] Task 2: B112-3 UI job 定时能力
**描述**: UiTestJob 增加 cron_expression/schedule_enabled；schedule 服务支持 job_type=plan|ui + job_id；
APScheduler 触发 UI job；迁移 + 单测；前端 UI job 管理页定时设置入口（minimal）。
**验收标准**: 单测全绿；平台创建 UI 定时任务并触发核对 10/10。
**涉及文件**: - `backend/app/models/ui_test.py`、`test_schedule.py`、`schedule_service.py`、`api/v1/schedule.py`
            - `alembic/versions/`（新增迁移）
            - `frontend/src/pages/uitest/`（定时设置）

### [ ] Task 3: C107-2 接口依赖（前置接口配置 + 执行链）
**描述**: TestCase 增加 depends_on_ids；执行器先执行前置用例并把响应注入后置（$prev.{key}.{jsonpath}）；
拓扑顺序 + 环检测；单测；场景串联用例落库与实跑。
**验收标准**: 单测全绿；串联场景实跑通过。
**涉及文件**: - `backend/app/models/test_case.py`、`api_execution_service.py`
            - `backend/tests/test_api_dependency_chain.py`（新增）

### [ ] Task 4: B10 XHR 采集工具 + 生成链路消费关联基座
**描述**: UI 采集任务（只读 playwright 采集页面 XHR 含请求头 → 样本 JSON）；case_generation 提示词注入
关联基座检索（RAG module 查询）。
**验收标准**: 采集证据 JSON；单测断言提示注入含模块-接口映射。
**涉及文件**: - `backend/app/services/xhr_capture_service.py`（新增）+ `api/v1/ui_test.py`
            - `backend/app/services/case_generation_service.py`、`api_case_generation_service.py`

### [ ] Task 5: B112-1 重探/口径 + QA/Leader + 一次总确认
**描述**: 重探 news/get；用户口径确认；写 QA/Leader；一次总确认 → push → PR。
**验收标准**: 工件齐全；audit-cconditions 0 硬错。

## 质量要求

- [ ] TDD：调度/依赖链/提示注入先写失败测试
- [ ] 后端受影响模块 pytest + ruff F821；前端 typecheck/build（若改前端）
- [ ] Alembic 单头 + 迁移离线校验
- [ ] scan-common-bugs HARD=0；无调试残留