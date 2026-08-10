# Batch 137 — 蓝湖采集"仅最新版本" + DOM 文本兜底 + OCR 诊断 PRD
> **Product (🟦)** | Date: 2026-08-10 | Status: Approved

mode: full（完整批次）
判定理由: 新增采集选项（latest_version_only，接口新增可选参数）与"DOM 文本作为文本证据"行为变更，属新行为。

## 1. 问题陈述
1. 用户希望蓝湖采集**只针对最新版本（16.0.0）**，当前是全量 109 页（含多版本）。
2. 采集结果"部分完成、不可导入"：生产 OCR 未生效（LANHU_OCR_COMMAND 未配置/路径为本地不存在/引擎未装），OCR=0；即使页面有 Axure HTML 的 DOM 文本，质量门禁只认 OCR → 不达标。
3. OCR 不可用原因（lanhu_ocr_command 未配置）未透出，难以定位。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 仅最新版本采集 | 全量 109 页 | 勾选"仅最新版本"后只采集最新版本文件夹页面（如 16.0.0） | 本批验收 |
| DOM 文本兜底 | OCR=0 则不可导入 | 页面有 DOM 文本即视为文本证据，质量达标可导入；纯图片页仍需 OCR/人工 | 本批验收 |
| OCR 诊断 | 原因不可见 | 质量报告含 ocr_note（如 LANHU_OCR_COMMAND 未配置） | 本批验收 |
| 回归 | - | 后端全量、前端 444 无新增失败 | 本批验收 |

## 3. 非目标与 C 条件
- 不新增后端接口路径（仅给 create 请求加可选参数）；不改生产数据。
- 生产 OCR 引擎安装属部署项（本批文档/提示，不强制）。
- C 条件维持。

## 4. 用户故事与验收标准
- As 测试平台用户, I want 只采集最新版本页面, so that 不重复采集历史版本。
  - Given 创建证据任务勾选"仅最新版本" / When 采集 / Then 仅返回最新版本文件夹（16.0.0）页面。
- As 测试平台用户, I want 有 DOM 文本的页面即使无 OCR 也能达标导入, so that 不因 OCR 未配置而"部分完成"。
  - Given 页面有 Axure HTML DOM 文本且 OCR 不可用 / When 质量评估 / Then ocr_status 视为成功，import_ready=true（纯图片页除外）。
- As 测试平台用户/运维, I want 知道 OCR 为什么没生效, so that 能配置修复。
  - Given OCR 不可用 / When 查看质量报告 / Then 含 ocr_note 说明原因。

## 5. 技术考量
- 版本过滤：按 sitemap 顶层路径段识别版本文件夹（如 16.0.0），语义排序取最新；无版本文件夹回退全量。
- DOM 文本兜底：job_runner 中 ocr_status 依据 (ocr_text or dom_text) 判定；OCR 不可用时质量报告附 ocr_note。
- 链路：前端开关 → createLanhuEvidenceJob.latest_version_only → 后端 schema → requested_options_json → worker → discover_pages → get_lanhu_pages_for_evidence 过滤。
- 风险：版本文件夹命名不统一时回退全量；纯图片设计图板无 DOM 文本仍需 OCR/人工。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批（test） | 内部 | 单测 + 门禁全绿 |
| 生产 | 用户 | 勾选仅最新版本采集 16.0.0 成功；有 DOM 文本任务可导入 |

## 7. 技能使用
- `cameltv-agent-team` / `cameltv-bug-guard`（外部依赖能力核对）。
