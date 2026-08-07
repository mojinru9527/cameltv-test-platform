# Batch 116 — PM Plan（AI 生成链路加固 + B10 平台采集）

> **PM (🟨)** | Date: 2026-08-07

## 开发任务

### [ ] Task 1: C102-1 异步生成（后端 + 前端轮询）
**验收标准**: 大文档提取/生成走后台任务，GET 状态轮询；单测（任务创建/状态/结果）。
**涉及文件**: `backend/app/api/v1/requirement.py`、`ai_service.py`、`frontend/src/pages/requirement/*`

### [ ] Task 2: C103-6 截断补全 + 覆盖缺口报告
**验收标准**: 截断块自动补生成；覆盖缺口报告 JSON（功能点 vs 用例覆盖矩阵）；单测。
**涉及文件**: `backend/app/services/ai_service.py`

### [ ] Task 3: C115-3 平台采集 API/UI
**验收标准**: POST /uitest/capture 创建采集任务 + GET 结果；样本 JSON 落库；单测/证据。
**涉及文件**: `backend/app/api/v1/ui_test.py`、`playwright_executor.py` 或新 capture service

## 质量要求

- [ ] 受影响模块 pytest + ruff F821；前端 typecheck/build（若改前端）
- [ ] scan-common-bugs HARD=0；无调试残留