# Batch 108 — QA Report（capture 去重误判修复 + 规范导入闭环）

> **QA (🔍)** | Date: 2026-08-06 | Verdict: 需改进（功能落地，部署后 API 复验登记）

## 1. 交付与生产证据

| 资产 | 结果 | 证据 |
|------|------|------|
| 根因定位 | capture 一律 409 = 部署环境 `KNOWLEDGE_INGEST_ENABLED=false` + 路由把 disabled/duplicate/error 混义 + hooks 失败翻转成功 | 生产库直连核查（hash 无匹配）+ 本地复现脚本（同内容去重/异内容新建/开关关 None） |
| ingest 结果类型化 | `CaptureIngestResult(reason, source_id)`：created/disabled/duplicate/error，不再 None 混义 | ingest_service.py + 单测 6 项 |
| 路由错误映射 | disabled→503 明确提示；duplicate→409；error→500；created→200 | knowledge.py + 路由单测 4 类响应 |
| hooks 容错 | `_post_ingest_hooks` 失败仅记日志，不翻转已提交成功 | 单测 `test_capture_hooks_failure_does_not_flip_created` |
| 配置对齐 | `production.env.example` 增加 `KNOWLEDGE_INGEST_ENABLED=true`；本地 production.env 同步 | 文件 diff |
| **C107-1 闭环** | 规范文档已入库生产知识中心：knowledge_source id=6（capture/parsed）+ 1 切片；API sources total=6 可见 | 生产库核查 + sportsadmin API 实测 |

## 2. 硬门禁

| 门禁 | 结果 |
|------|------|
| 后端受影响模块 pytest | ✅ 107 passed（capture_outcomes 6 + knowledge 75 + search_rag 17 + ai_closure 9） |
| ruff F821（3 个文件） | ✅ All checks passed |
| Alembic | ✅ 单头（20260806_batch106_project_invite，本批无迁移） |
| scan-common-bugs | ✅ HARD 0 / WARN 209（基线持平） |
| validate_repo_boundaries --check | ✅ PASS |
| 调试残留 | ✅ 无 console.log/print/breakpoint/debugger |

## 3. 缺陷/障碍（P0–P3）

| # | 级别 | 问题 | 实测证据 | 处理 |
|---|:----:|------|---------|------|
| B108-1 | P2 | 部署环境（Railway）`KNOWLEDGE_INGEST_ENABLED` 未显式开启，API capture 路径在开关开启前仍不可用（代码已区分 503 明确提示） | 生产 API 2026-08-06 实测 409 误报；本地复现确认代码侧已修复 | 登记 C108-1：Railway 增加环境变量后复验 API capture（200/409/503 语义） |

## 4. 诚实性说明

- 规范文档导入走生产库直连 ingest 通道（Batch 102/103 已授权模式），非模拟数据；导入后未清除任何既有数据（生产 5 条体育文档保留，新增 id=6）。
- 本批无数据库 Schema 变更（无需迁移）；仅后端行为语义修复 + 配置模板。
- vector_search 非 functional（C102-2 另一子项）不在本批范围，保持 Open。

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/0/1/0 | 0 | 配置+错误语义 | 部署环境开关先行探测；API 错误语义不要用单一业务码掩盖多种原因 |

**技能使用**：`cameltv-agent-team`（六部门流水线）、`test-case-design`（规范文档导入闭环）。
