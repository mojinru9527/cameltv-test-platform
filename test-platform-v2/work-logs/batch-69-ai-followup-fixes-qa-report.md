# Batch 69 — QA 报告（AI 验收跟进修复：C68-2/C68-3/C68-4）

> **QA (🔍)** | Date: 2026-08-03 | Verdict: PASS

## 测试总览

| 条件 | 通过 | 失败 | 阻塞 |
|:----:|:----:|:----:|:----:|
| C68-2 用例-需求关联 API | 4 | 0 | 0 |
| C68-3 AI 生成分批合并 | 5+1 E2E | 0 | 0 |
| C68-4 发布决策登记 | 1 | 0 | 0 |
| 回归 | 27 | 0 | 0 |

## 可执行门禁（命令、退出码、结果）

| # | 门禁 | 命令/方式 | 结果 |
|---|------|-----------|------|
| G1 | ruff F821 | `ruff check app --select F821` | PASS：All checks passed |
| G2 | 新增单测 | `pytest test_case_source_doc_link.py test_ai_generate_chunked.py` | PASS：11/11 |
| G3 | 相关回归 | `pytest test_ai_extraction_fallback.py test_batch48_requirement_acceptance.py` | PASS：28/28（合计 39/39） |
| G4 | 端到端 C68-3 | batch-69 后端 8036：147 FP 文档 generate | PASS：200，331 条 functional_cases，无 warning（此前同文档连续两次截断失败） |
| G5 | 端到端 C68-2 | import 60 用例 + PUT source_doc_id | PASS：trace/requirement/1 total=60；PUT 关联 200；无效文档 400 |

## 逐条件验证

### C68-2 — TestCaseUpdate.source_doc_id
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| Schema 字段 | ✅ | `TestCaseUpdate.source_doc_id: Optional[int]`，缺省 None 向后兼容 |
| 校验 | ✅ | 无效文档 999 → 400「来源需求文档不存在或无权关联」；同项目文档通过 |
| 导入路径关联 | ✅ | `POST /requirements/1/import` 60 条 AI 用例 → source_doc_id=1 落库，`/trace/requirement/1` total_cases=60 |
| 手动关联 | ✅ | `PUT /test-cases/1 {source_doc_id:1}` → 200 |

### C68-3 — AI 用例生成分批合并
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 分批工具 | ✅ | `_split_extraction_chunks` 按 FP≤25 保序拆分（含单模块超限再切）；单测 3 项 |
| 去重/编号 | ✅ | `_dedupe_and_renumber` 按 title 去重并重编号唯一；单测 2 项 |
| 大文档端到端 | ✅ | 147 FP 文档（8 模块）→ generate 200，331 条用例、无截断告警（6 块分批合并） |
| 失败路径 | ✅ | 块级截断 → 重试 1 次 → 仍失败仅告警该块；全部失败才 400（代码路径，mock 单测覆盖拆分） |

### C68-4 — 正式域名发布决策登记
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 交付清单登记 | ✅ | 新增「正式域名发布演练（batch-68/69）」：Vercel/Railway 200、ALLOWED_ORIGINS 对齐；待决策项（自定义域名等）标注 ⏳ 用户 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| B69-Q1 | P3 | 测试隔离：初版 test_case_source_doc_link 直接覆盖 get_requirement 未恢复 → 污染后续测试 | 7 失败复现 | ✅ 已修复（monkeypatch） |

## 发布建议

状态: **PASS**。C68-2/C68-3 代码修复与端到端验证通过；C68-4 登记完成（决策项待用户）；
回归 39/39 无新增失败；C68-1/J15/J16 保持 DEFERRED（缺授权）。
