# Batch 247 — RapidOCR 蓝湖识别引擎重建

mode: full
executor: codex
date: 2026-09-16
source: GitHub Issue #422

## 0. C-conditions check

当前 `C-CONDITIONS.md` 没有与本任务直接绑定的新 Open 条件。本批承接 Issue #422
“从最新 main 重建 rapidocr 蓝湖识别引擎（承接 #202）”；旧 PR #202 的实现可作为
行为与验收参考，但其分支已落后 200+ commits，不能直接合并。

## 1. 问题

当前线上蓝湖证据链路存在四个叠加问题：

- 后端只有可配置的外部 OCR 命令占位，默认没有内置 OCR 引擎，纯图片页
  `ocr_text` 为空，只能依赖 Axure DOM 文本兜底。
- `lanhu_ocr_min_confidence` 会把低置信度块整块丢弃，小字/模糊字更容易缺失。
- 截图使用 1x DPR，小字分辨率不足，进一步降低 OCR 命中率。
- 新增 OCR 依赖尚未进入当前 split 拓扑的 runner 锁和 Linux 容器系统库。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|---|---|---|
| 内置 OCR | 默认无引擎 | 默认 rapidocr CPU OCR 可用 |
| 低置信度文本 | 过滤后丢弃 | 全部保留，置信度仅作元数据 |
| 截图 DPR | 1x | 可配置，默认 2.0 |
| OCR 依赖 | 未进入 runner 锁 | runner lock 含 rapidocr/opencv 等 |
| Linux 容器 | 缺 opencv 系统库 | runner 镜像可导入 cv2 并跑 OCR |
| 回归 | 无新增失败 | backend/ruff/锁/架构门禁全绿 |

## 3. 非目标

- 不做云 OCR、GPU 加速、多语言扩展或 OCR 模型训练。
- 不改变 DOM/MCP 文本提取与现有 OCR+DOM 合并策略。
- 不新增前端页面或接口；本批只修复蓝湖证据链路的 OCR 能力。
- 不物理删除历史数据或改变 canonical ExecutionRun 体系。

## 4. 用户故事与验收

- Given 后端使用默认配置，When 执行蓝湖证据采集，Then 内置 rapidocr CLI 可用且
  返回真实中文识别块。
- Given 截图中有低置信度小字，When OCR 完成，Then 该块仍进入 `ocr_text`。
- Given 采集长页面截图，When Playwright 创建页面，Then 使用配置的
  `device_scale_factor`，默认 2.0。
- Given runner 镜像构建，When 在 Linux 容器执行 OCR，Then cv2/rapidocr 可导入并
  能识别真实截图。
