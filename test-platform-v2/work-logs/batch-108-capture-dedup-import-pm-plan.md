# Batch 108 — PM Plan（capture 去重误判修复 + 规范导入闭环）

> **PM (🟨)** | Date: 2026-08-06 | Status: Review

## 任务拆解（30–60 分钟/任务）

| # | 任务 | 描述 | 验收标准 | 涉及文件 | 参考 |
|---|------|------|---------|---------|------|
| 1 | 批次工件 | PRD/PM/Design/看板/C 条件引用 | 六件齐备；C102-2 capture 子项纳入、C107-1 关闭目标明确 | `work-logs/batch-108-*`、`kanbans/DEV-batch-108*` | 本批根因分析（临时复现脚本） |
| 2 | ingest 结果类型化 | `CaptureIngestResult(reason, source_id)`；disabled/duplicate/error/created；hooks try/except | 不再用 None 混义；hooks 失败不翻转成功 | `backend/app/services/knowledge/ingest_service.py` | 根因 1/3 |
| 3 | 路由错误映射 | capture_insight 按 reason 返回 503/409/500/200 | 开关关→503 明确提示；重复→409；异常→500+日志 | `backend/app/api/v1/knowledge.py` | 根因 2 |
| 4 | 配置对齐 | production.env 增加 KNOWLEDGE_INGEST_ENABLED=true | env 文件含开关项；部署清单登记 Railway 人工步骤 | `config/runtime/production.env` | docker-compose 默认 true |
| 5 | 单测 | capture 结果语义（disabled/duplicate/created/error）+ hooks 容错 | pytest 全绿；现有 knowledge 测试无回归 | `backend/tests/test_knowledge_capture_outcomes.py` | 现有 test_knowledge.py |
| 6 | 导入闭环 + QA/Leader | 生产库导入规范文档 → sources API 验证；QA/Leader 工件 | sources 列表可见该文档；C107-1 关闭证据 | `work-logs/batch-108-*-{qa-report,leader-verdict}.md`、`C-CONDITIONS.md` | C107-1 |

## 排期

| Slice | 内容 | 计划耗时 |
|-------|------|---------|
| S1 | 工件 + 根因文档（任务 1） | 0.5h |
| S2 | ingest 类型化 + 路由映射 + 配置（任务 2–4） | 1h |
| S3 | 单测 + 生产导入闭环（任务 5–6） | 1h |
| S4 | QA 证据 + Leader + 一次总确认 | 0.5h |

## 风险

- 生产导入依赖直接 DB 通道（已授权，Batch 102/103 模式）；hooks 可能依赖外部 AI 服务，已加容错不阻塞主结果。
- 部署后 API 验证依赖 Railway 环境变量（人工步骤），登记 C108 部署后复验项，不阻塞代码合入。
