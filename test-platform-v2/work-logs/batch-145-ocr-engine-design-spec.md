# Batch 145 — Design Spec
> **Design (🎨)** | Date: 2026-08-11 | Status: 就绪

## 0. 技术体系确认
后端 Python 3.12 + FastAPI；前端 shadcn/ui + Radix + Tailwind。本批主体为后端能力接入，前端仅 1 处文案微调。`cameltv-ui-conventions` Red Flags 已比对（无新组件/无样式改动风险）。

## 1. 内置 OCR CLI 设计
| 项 | 规范 |
|----|------|
| 入口 | `python -m app.services.lanhu_evidence.rapidocr_cli --image <path>` |
| 输入 | `--image` 截图路径（可选 `--min-side` 等预留参数，本批不加） |
| 输出 | stdout 逐行 JSON：`{"text":"...","confidence":0.99,"bbox":[x1,y1,x2,y2]}` |
| bbox | rapidocr 返回 4 点框 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] → `[min_x, min_y, max_x, max_y]`（整数） |
| 失败 | 模型加载/识别异常 → stderr 错误信息，退出码非 0 |
| 兼容 | 输出与 `local_ocr_provider.parse_command_output` 契约一致（已有单测覆盖解析） |
| 性能 | 每进程加载一次模型（随 wheel 打包，无下载）；单段识别实测 <2s（CPU） |

## 2. 配置项设计
| 配置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `lanhu_ocr_command` | str | `python -m app.services.lanhu_evidence.rapidocr_cli --image "{image}"` | 命令模板，`{image}` 为截图路径；可被外部引擎覆盖（paddleocr 等） |
| `lanhu_capture_device_scale_factor` | float | `2.0` | Playwright `device_scale_factor`，截图 2x 输出 |
| `lanhu_ocr_min_confidence` | float | 移除（不再过滤） | 置信度仅记录在块上作参考，不参与过滤 |

## 3. 数据链路
```
截图段 → LocalCommandOcrProvider(rapidocr CLI) → parse_command_output → OcrTextBlock[]（全部保留）
       → job_runner ocr_text → merge_page_text → merged_text
       → LanhuEvidencePage{ocr_text, merged_text} → 前端 PrototypePreview 展示 merged_text（batch-144 已通）
```

## 4. Dockerfile 变更
apt 安装追加（opencv-python 5.0.0.93 Linux 实测缺失，ldd 证据）：
`libgl1 libglib2.0-0 libxcb1 libx11-6 libxext6 libsm6 libice6`

## 5. 前端文案微调
| 文件 | 现值 | 改后 |
|------|------|------|
| `PrototypePreview.tsx` OCR 面板副标题 | 「该页 OCR 提取文字 · {n} 字」 | 「该页提取文字（OCR+DOM）· {n} 字」 |

## 6. 设计签核
结论：通过（后端为主，前端无样式/布局变更）。
