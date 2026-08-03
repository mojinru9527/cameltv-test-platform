# Batch 71 — PM Plan（内部收尾优化）

> **PM (🟨)** | Date: 2026-08-04

## 开发任务

### [ ] Task 1: C70-3 登录限流环境化
**描述**: `core/rate_limit.py` 登录限流参数改为 settings 注入（`login_rate_limit_max` / `login_rate_limit_window_seconds`）；
settings 默认按环境（production=10/900，development/test=100/900）；`.env.example` 注释说明。
**验收标准**: 单测（settings 注入生效）；dev 环境连续 100 次登录不 429；prod 默认不变。
**涉及文件**: `backend/app/core/rate_limit.py`、`core/config.py`、`backend/.env.example`、`tests/`

### [ ] Task 2: C69-3 AI 分批并发
**描述**: `ai_service.generate_test_cases` 分批循环改为 asyncio.Semaphore(2) 限并发并行，按块序合并；
保留块级截断重试与告警语义。
**验收标准**: 单测（mock：并发调用次数/顺序/结果一致）；实测 147 FP 文档耗时下降。
**涉及文件**: `backend/app/services/ai_service.py`、`tests/test_ai_generate_chunked.py`

### [ ] Task 3: C70-2 报告模板增强
**描述**: TemplateManager 行内「设为默认」切换（`updateTemplate({is_default:true})`）+ 章节启用勾选
（`sections` 编辑保存）。
**验收标准**: 浏览器 E2E（默认切换 + 章节勾选持久化）；Vitest。
**涉及文件**: `frontend/src/pages/report/TemplateManager.tsx`、`api/reportTemplate.ts`、`__tests__/`

### [ ] Task 4: C65-2 过时手册删除
**描述**: 审计并删除《生产测试平台固定配置与双VPN切换验收手册.md》，同步更新引用与 doc-check。
**验收标准**: 文件删除、引用清理、`cameltv-doc-check` 通过。
**涉及文件**: `docs/`、`work-logs/`

### [ ] Task 5: QA + Leader + PR
**描述**: 六部门工件 + 看板；走 push 授权 → Draft PR → checks → 二次确认 → 合入。

## 质量要求
- [ ] ruff F821、受影响 pytest、前端 typecheck/build、受影响 Vitest 全绿
- [ ] 无新依赖；生产安全默认不变；每 PASS 带证据
