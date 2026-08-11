# Batch 153 — PM 计划（需求覆盖率 + AI 置信度）

> **PM (🟨)** | Date: 2026-08-11

## 开发任务
### [ ] T1: 脚手架
### [ ] T2: artifact_confidence 模块（severity + output 提取）
**涉及**: backend/app/services/knowledge/artifact_confidence.py
### [ ] T3: 三处 AiArtifact 创建接入置信度
**涉及**: agent_orchestrator.py、wiki/compare_service.py、wiki/lint_service.py
### [ ] T4: 需求覆盖率口径修复
**涉及**: services/trace_service.py（get_project_coverage）
### [ ] T5: 测试
**涉及**: backend/tests/test_batch153_coverage_confidence.py（覆盖率 + 置信度 helper + 差异项置信度）
### [ ] T6: QA + 冒烟
**涉及**: 证据（覆盖率/置信度接口返回）

## 质量要求
- [x] 覆盖率以实际关联为锚
- [x] confidence ∈ [0,1] 校验
- [x] 单测覆盖
