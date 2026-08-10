# Batch 137 — PM Plan
> **PM (🟨)** | Date: 2026-08-10

## 开发任务
### [ ] Task 1: 后端"仅最新版本"过滤
**描述**: lanhu_provider 增加 _filter_latest_version_pages（按顶层路径段识别版本文件夹、语义排序取最新）；get_lanhu_pages_for_evidence(url, latest_version_only=False)；page_discovery/job_runner 透传；create schema 加 latest_version_only 可选字段。
**验收**: 单测覆盖多版本/无版本/语义排序/空列表。
### [ ] Task 2: DOM 文本兜底 + OCR 诊断
**描述**: job_runner ocr_status 依据 (ocr_text or dom_text)；OCR 不可用时 quality 附 ocr_note。
**验收**: 有 DOM 文本的页面 ocr_status=success；质量报告含 ocr_note。
### [ ] Task 3: 前端开关
**描述**: LanhuEvidenceDialog 加"仅最新版本"开关并传入 latest_version_only；API 类型可选。
**验收**: typecheck/build/444 通过。
