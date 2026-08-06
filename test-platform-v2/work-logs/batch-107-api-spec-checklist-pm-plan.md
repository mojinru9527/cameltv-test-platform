# Batch 107 — PM Plan（接口用例生成「测试考虑点」全量固化）

> **PM (🟨)** | Date: 2026-08-06 | Status: Review

## 任务拆解（30–60 分钟/任务）

| # | 任务 | 描述 | 验收标准 | 涉及文件 | 参考 |
|---|------|------|---------|---------|------|
| 1 | 批次工件 | PRD/PM/Design/看板/C 条件引用 | 六件齐备；C103-3/C103-4 纳入说明、C103-5/C103-6 豁免理由记录 | `work-logs/batch-107-*-*.md`、`work-logs/kanbans/DEV-batch-107-api-spec-checklist.md` | Batch 103 工件 |
| 2 | 规范落盘 | XMind 101 节点全量转写为 `接口测试考虑点.md`；api-checklist 增引用 | 文档与 XMind 节点一一对应；skill 引用可解析 | `tests/test-case-standards/接口测试考虑点.md`、`tests/test-case-standards/CLAUDE.md`、`.agents/skills/test-case-design/api-checklist.md` | 用户 XMind 解析输出 |
| 3 | 规则生成器扩展 | 新增 9 类模板：smoke/scenario/extra_param/security_ext/performance_low/data_test/stability/compatibility/monitoring；默认模板集扩展 | 每类模板生成有界条数用例；api_body/api_assertions/design_method/正负向齐全；性能 P2/P3 | `backend/app/services/api_case_generation_service.py` | PRD §4 |
| 4 | 真实样本响应结构断言 | `generate_cases_from_real_sample` 消费 response_envelope_keys/data_keys/record_count/first_record_fields/assertion_design_hints，新增返回值结构用例 | list_visible 生成结果含业务断言（status=0/records≤size/排序/核心字段非空） | `backend/app/services/api_case_generation_service.py` | `work-logs/evidence/batch-103/real-request-sample-news-list-visible.json` |
| 5 | AI 提示词注入 | `ai_service.py` api 生成上下文加载 api-checklist + 接口测试考虑点；api_cases 断言要求升级 | 提示词包含检查点；api_cases 断言要求含响应结构/关键字段 | `backend/app/services/ai_service.py` | PRD §4 |
| 6 | 前端/schema 模板默认值 | AssetTab 默认模板数组 + schema 默认值加入新模板 | 一键生成即含新类别 | `frontend/src/pages/apitest/components/AssetTab.tsx`、`backend/app/schemas/api_asset.py` | Batch 103 前端变更 |
| 7 | 单测 | 新模板断言 + 响应结构断言 + 默认模板集 | pytest 全绿（含新用例）；现有接口用例测试无回归 | `backend/tests/test_api_case_spec_checklist.py` | `backend/tests/test_api_case_real_sample.py` |
| 8 | QA+Leader | 硬门禁、生成证据、判决、C 条件、流程回写 | 见 QA 报告与 Leader 判决模板 | `work-logs/batch-107-*-{qa-report,leader-verdict}.md`、`C-CONDITIONS.md` | DEPARTMENTS.md |

## 排期

| Slice | 内容 | 计划耗时 |
|-------|------|---------|
| S1 | 工件 + 规范落盘（任务 1–2） | 1h |
| S2 | 生成器扩展 + 响应结构断言（任务 3–4） | 2h |
| S3 | AI 提示词 + 前端/schema + 单测（任务 5–7） | 1.5h |
| S4 | QA 证据 + Leader + 一次总确认（任务 8） | 1h |

## 风险

- 场景测试需要接口关联信息：当前单接口生成器无关联图谱，先产出「场景测试建议（依赖关联接口）」模板用例，标注待关联，不阻塞。
- 安全/性能/数据/监控类用例属「辅助考虑点」，断言以「不应 5xx + 检查建议」为主，避免对生产造成压力；性能明确 P2/P3。
- 知识中心导入依赖生产 API；若 C102-2 capture 问题仍存在，登记障碍并移交下一批。
