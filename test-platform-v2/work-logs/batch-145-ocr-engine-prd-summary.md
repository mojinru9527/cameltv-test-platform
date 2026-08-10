# Batch 145 — 蓝湖证据 OCR 引擎接入与识别质量修复
> **Product (🟦)** | Date: 2026-08-11 | Status: Approved

## 0. 批次模式判定
**完整批次**：引入新依赖（rapidocr_onnxruntime）、新配置（`lanhu_ocr_command` 默认内置 CLI、`lanhu_capture_device_scale_factor`）、新行为（内置 CPU OCR 引擎、保留低置信度文本、截图 2x）。按 `pipeline-modes.md`「是否引入新行为/新接口/新配置/新依赖 → 是 → 完整批次」执行六部门流水线。

## 1. 问题陈述
用户在 batch-144（预览弹窗增强）验收后反馈：**OCR 并没有准确识别每一张截图里的文字内容，会出现缺失遗漏**。审查现有链路确认 4 个叠加根因：

- **R1（主因）后端未安装任何 OCR 引擎**：`backend/requirements.txt` / `requirements.lock` / `Dockerfile` 均无 OCR 依赖；`config.py:202` `lanhu_ocr_command` 默认空 → `local_ocr_provider.recognize()` 直接返回 `status="unavailable"` → 页面 `ocr_text` 为空，`merged_text` 仅含 DOM/Axure 文本兜底，纯图片页（设计图板原图）几乎没有任何文本。
- **R2 低置信度文本被丢弃**：`local_ocr_provider.py:78` `kept = [b for b in blocks if b.confidence >= min_conf] or blocks`（`lanhu_ocr_min_confidence=0.60`），小字/模糊字块被过滤，是「缺字」的直接来源。
- **R3 截图分辨率不足**：`screenshot_service.py:182` 以 1440×1200 视口、1x DPR 截图，小字在 2x 缩放预览下辨识度低，OCR 命中率低。
- **R4（batch-144 已修复）前端数据链路**：`requirement/index.tsx:404-407` 已优先取 `merged_text || ocr_text || dom_text`，无需再改前端主链路。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| OCR 引擎可用 | 默认 `unavailable`（无命令） | 内置 rapidocr 默认可用，`ocr_status=success` | 本批验收（本地实测中文截图） |
| 识别文本量 | 低置信度块被过滤 | 保留全部识别块（置信度仅作参考展示） | 本批验收（单测 + 实测） |
| 截图清晰度 | 1x DPR | 2x DPR（新增配置，默认 2.0） | 本批验收（代码核对 + 单测） |
| 依赖可部署 | 锁文件缺 OCR 依赖 | `requirements.lock` 在 Windows/Linux 均 `pip install --require-hashes` 通过 | 本批验收（实测） |
| 回归 | - | 后端 pytest/ruff + 前端 typecheck/build 全绿 | 本批验收 |

## 3. 非目标（本次不做）
- 不做云 OCR / GPU 加速 / 多语言扩展（CPU 离线为本项目约束，rapidocr 已覆盖中英文）。
- 不引入 PaddleOCR / EasyOCR / Tesseract（重依赖或中文弱，选型已否决）。
- 不改变 DOM/MCP 文本提取与 `merge_service` 合并策略（现有合并已保留 OCR+DOM 双证据）。
- 不做 OCR 模型微调/训练。
- 不新增前端页面/接口（`merged_text` 链路 batch-144 已通）。

## 4. 用户故事 + 验收标准
- As 需求/QA 用户, I want 采集任务的截图文字能被 OCR 准确提取, so that 证据包导入需求/RAG 后文本完整可检索。
  - Given 后端已安装 rapidocr（默认配置）/ When 执行蓝湖证据采集 / Then 每个截图段 OCR 成功，`ocr_text` 非空且含截图中的中文文本。
- As 用户, I want 小字/模糊字不被丢弃, so that OCR 不再缺字。
  - Given 含低置信度文本块的截图 / When OCR 完成 / Then 全部识别块保留在 `ocr_text`，置信度仅记录不过滤。
- As 用户, I want 截图更清晰, so that OCR 命中率更高。
  - Given 采集任务 / When 执行截图 / Then 截图以 2x DPR 输出，小字更清晰。

## 5. 技术考量
- **引擎**：`rapidocr_onnxruntime==1.4.4`（CPU 中文 OCR，PP-OCRv4，模型随 wheel 打包约 16MB，无需运行时下载；已实测中文识别正确）。
- **新依赖**：`rapidocr-onnxruntime`、`opencv-python`、`pyclipper`、`shapely`、`six`（onnxruntime/Pillow/numpy/PyYAML/tqdm 已在锁中）。
- **opencv-python 系统库**：Linux slim 镜像缺 `libxcb/libGL/libglib` 等，需 Dockerfile 补 `libgl1 libglib2.0-0 libxcb1 libx11-6 libxext6 libsm6 libice6`（已用 ldd 实测确认）。
- **锁文件**：pip-compile 7.6.0 增量生成 5 个新包块，win/linux 哈希一致；已在 Windows venv 与 Linux 容器分别 `--require-hashes` 安装验证通过。
- **风险**：opencv-python 5.0.0.93 为新大版本（rapidocr 约束 `>=4.5.1.48` 解析所得）；内置 CLI 每截图段启动一次 Python 进程加载模型（实测约 0.5-1s），单页多段累计可接受（后台任务 + 心跳）。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 平台全量 | PR 必需检查全绿，QA 判决 PASS，Leader APPROVED |
| 随发布火车部署 | test → 生产 | 部署后采集任务 OCR 成功，证据包文本完整 |

## 7. 技能使用
- `cameltv-agent-team` → 六部门流水线 + 批次档位判定。
- `cameltv-bug-guard` → 依赖/部署铁律（新依赖同步 requirements、跨平台锁、镜像系统库）。
- `cameltv-ui-conventions` → 前端文案/展示走查（本批前端仅文案微调）。
