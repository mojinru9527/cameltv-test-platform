# Batch 69 — PM Plan（AI 验收跟进修复：C68-2/C68-3/C68-4）

> **PM (🟨)** | Date: 2026-08-03

## 开发任务

### [ ] Task 1: C68-2 — TestCaseUpdate 支持 source_doc_id
**描述**: `schemas/test_case.py` 的 `TestCaseUpdate` 增加 `source_doc_id: Optional[int] = None`；
`update_case` 沿用 setattr 路径即可；校验 source_doc_id 指向的文档存在且属于同项目（不越权关联）。
**验收标准**: PUT /test-cases/{id} 提交 source_doc_id 后 DB 生效；越权/不存在文档返回 400/403；
`/trace/requirement/{doc_id}` 计数更新；用 API 重建 batch-68 的 50 条用例关联（替换种子）。
**涉及文件**: `backend/app/schemas/test_case.py`、`backend/app/services/test_case_service.py`、`backend/tests/`

### [ ] Task 2: C68-3 — AI 用例生成分批合并
**描述**: `ai_service.generate_test_cases` 在 extraction 存在时按模块分批（单批功能点上限 25）调用
`_call_ai_api`，合并 functional_cases；块级截断重试 1 次，仍失败记 warning 继续，不整体失败。
**验收标准**: 147 功能点文档生成成功（functional_cases 非空且无重复）；小文档（≤25 FP）单次调用行为不变；
截断场景单测覆盖（mock 截断 → 重试 → 告警）。
**涉及文件**: `backend/app/services/ai_service.py`、`backend/tests/test_ai_service*.py`

### [ ] Task 3: C68-4 — 正式域名发布决策登记
**描述**: `docs/production-delivery/生产环境交付清单.md` 登记 batch-68 演练结论（Vercel/Railway 全链路 200）
与待决策项（是否启用自定义域名、ALLOWED_ORIGINS 已对齐）；C-CONDITIONS C68-4 备注更新。
**验收标准**: 交付清单含「发布演练结论 + 待用户决策」；C68-4 登记状态明确。
**涉及文件**: `docs/production-delivery/生产环境交付清单.md`、`C-CONDITIONS.md`

### [ ] Task 4: QA 报告 + Leader 判决 + 看板 + PR
**描述**: 汇总证据写 QA/Leader/看板；走 push 授权 → Draft PR → checks → 二次确认 → 合入。
**验收标准**: 六部门工件齐全；QA 硬门禁（ruff F821 / pytest 受影响模块 / 前端 typecheck/build）全绿。
**涉及文件**: `test-platform-v2/work-logs/batch-69-ai-followup-fixes-{qa-report,leader-verdict}.md`、`kanbans/DEV-batch-69-ai-followup-fixes.md`

## 质量要求
- [ ] 硬门禁：`ruff check app --select F821`、受影响 pytest、`npm run typecheck && npm run build`
- [ ] TDD：先写失败测试再实现（分批合并、截断重试、source_doc_id 校验）
- [ ] 无调试遗留、无密钥入库；`git diff --check` 通过；每次 push 前按 §2.4 确认
