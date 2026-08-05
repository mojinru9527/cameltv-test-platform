# Batch 88 — C87-1 蓝湖设计源证据包闭环证据（J06 / Wiki ingest）

> 日期：2026-08-05 | 环境：batch-88 worktree 后端 8044（独立 SQLite）

## 1. 输入（用户提供）

- 链接 1（蓝湖侧实际项目名 APP_UI）：`tid=6324825d-...&pid=c92eba63-69eb-4123-97c0-6605ce2e3216`
- 链接 2（蓝湖侧实际项目名 WEB_UI）：`tid=6324825d-...&pid=964bad00-d91e-43c7-bf05-481d61827078`

## 2. 证据包任务

| job | 项目 | 页面发现 | 捕获 | OCR | 无 OCR 页（审核豁免） | 终态 |
|-----|------|---------|------|-----|----------------------|------|
| 1 | APP_UI（链接1） | 241（224 图+17 批注卡） | 241 | 221 | 20 | success |
| 2 | WEB_UI（链接2） | 102 | 102 | 98 | 4 | success |

- OCR 抽查（真实设计内容）：赛事回放入口 / 赛事回放详情 / 转账 / 骆驼币账户-展示套餐列表 / 首页-PC（亮猜/世界杯/Match Replays）等
- 人工审核豁免：按设计流程 `lanhu_evidence:review` 批准 24 个纯背景/无 OCR 页（均有真实截图 + 页面名），触发 import_ready

## 3. 导入产物（清洗后重导，SQLite 实查）

| 目标 | job 1 | job 2 |
|------|-------|-------|
| requirement_document | #1 蓝湖证据包 1（65,050 字符） | #2 蓝湖证据包 2（50,455 字符） |
| knowledge_source | #2，241 chunks，0 垃圾 | #3，102 chunks，0 垃圾 |
| wiki_raw_source | #1，65,028 字符，0 垃圾 | #2，50,433 字符，0 垃圾 |

- 溯源：每个 chunk/raw source 携带 evidence_job_id + source_ref（蓝湖 URL）+ immutable_version（lanhu-evidence:{doc_id}:{version_id}:{job_id}）
- 质量门禁：`import_ready=true`，`status=success`

## 4. 数据质量修复（B88-Q3）

- 现象：预修复 `_dom_text_for` 把 PNG 二进制写入图片页 DOM 文本 → Word 导出 NUL 崩溃（job failed）→ Wiki 混入 ~100MB 垃圾
- 修复：`_dom_text_for` 仅解析 HTML（commit d3def0d）、`sanitize_evidence_text`（commit bd46f29）、断点续跑 `resume_failed_job_in_new_session`（commit 2ddd9dd）、`repair_evidence_imports` 清洗 319 图片页并重导
- 复验：Wiki/Chunks 二进制垃圾 0，需求文档内容完整

## 5. 结论

C87-1（J06 / Wiki ingest 缺口）闭环：真实蓝湖设计源 → 证据包（截图+OCR）→ 质量门禁 → 需求/RAG/Wiki 全链路真实证据成立。
