# Batch 153 — QA 报告（需求覆盖率 + AI 产物置信度）

> **QA (🔍)** | Date: 2026-08-11 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 2 (C126-2/C126-3) | 2 | 0 | 0 |

## 可执行门禁
| 门禁 | 命令 | 结果 |
|------|------|------|
| ruff F821 | `python -m ruff check app/ --select F821` | ✅ |
| 本批 pytest | `pytest tests/test_batch153_coverage_confidence.py` | ✅ 8/8 |
| 受影响 pytest | `pytest tests/test_batch149_statistics.py tests/test_coverage_report.py tests/test_wiki_diff.py tests/test_wiki_lint.py tests/test_knowledge.py tests/test_knowledge_ai_closure.py` | ✅ 136 passed |
| alembic heads | `python -m alembic heads` | ✅ 单头 |
| 前端 typecheck/build/vitest | `npm run typecheck` / `build` / `vitest` | ✅ 455 tests（无前端改动） |

## 逐条件验证

### C126-2 需求覆盖率口径核对
**变更文件**: services/trace_service.py（get_project_coverage）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 覆盖率以 source_doc_id 实际关联为锚 | ✅ | 单测：AI 路径（imported_count=0）文档计入覆盖率 |
| 无用例文档不计数 | ✅ | 2 文档 1 覆盖 → 50% |
| 与单文档覆盖率口径一致 | ✅ | 均按实际用例关联 |

### C126-3 AI 审核台置信度计算
**变更文件**: services/knowledge/artifact_confidence.py（新增）、agent_orchestrator.py、wiki/compare_service.py、wiki/lint_service.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| severity 映射 | ✅ | P0→0.9/P1→0.85/P2→0.75/P3→0.65 |
| LLM 显式 confidence | ✅ | 0-1 收敛（>1→1，<0→0） |
| review_items 平均 | ✅ | 0.4/0.8 → 0.6 |
| 兜底 | ✅ | 0.6 |
| 差异项转产物置信度 | ✅ | 集成测试 P0→0.9 且回写 resolved_artifact_id |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 无 | - | - | - | - |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h vs 实际 2.5h | 0/0/0/0 | 1 | 正则导入补丁破坏多行 import | 改 import 块用整块替换并复核 |

**技能使用**: cameltv-bug-guard（口径一致性、类型校验）
