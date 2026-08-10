# Batch 145 — 知识入库 Notes（OCR 引擎接入）
> 来源: batch-145-ocr-engine | 2026-08-11 | 供 RAG/KB 检索

## 1. rapidocr_onnxruntime 选型与部署要点
- **选型结论**: CPU 中文 OCR 最优解 = rapidocr_onnxruntime（PP-OCRv4 det/rec/cls，模型随 wheel 打包 ~16MB，无 torch/paddle 重依赖）。PaddleOCR 精度略高但重一个量级；EasyOCR 需 torch；Tesseract 中文弱；云 API 需联网+费用。
- **模型无运行时下载**: 1.4.x 模型在包内 `rapidocr_onnxruntime/models/*.onnx`，无需下载；Docker 无需预下载步骤。
- **opencv-python 系统库**: slim 镜像缺 `libxcb.so.1 / libGL.so.1 / libglib-2.0 / libgthread / libX11 / libXext / libSM / libICE`。Dockerfile 需 `apt-get install libgl1 libglib2.0-0 libxcb1 libx11-6 libxext6 libsm6 libice6`（ldd 实测证据）。
- **输出契约**: `RapidOCR(img)` 返回 `(result, elapse)`，result 为 `[box4点, text, confidence]`；转 `{"text","confidence","bbox":[x1,y1,x2,y2]}` 即可复用 `parse_command_output`。

## 2. requirements.lock 增量生成（pip-compile 7.6.0）
- pip-compile 7.6.0 `--generate-hashes` 默认输出**全平台哈希**（win/linux 哈希集合一致），可避免 batch-67 的「Windows 锁缺 Linux 标记」问题。
- 增量合并：用现有锁版本提取 `constraints.txt`（112 个精确 pin），只对新增包解析，再把新包块按字母序插入原锁；**必须保留原锁头部注释与块间无空行格式**，否则 diff 噪音巨大。
- 验证：Windows `pip install --require-hashes --dry-run` + Linux 容器 `pip install --no-cache-dir --require-hashes` 双平台实测。

## 3. 子进程 OCR 命令必须用 sys.executable
- 模板用 `{python}` 占位，provider 替换为 `f'"{sys.executable}"'`。否则 Windows venv 未激活时子进程 `python` 解析到系统解释器（无 rapidocr）→ OCR failed。
- 子进程 stdout 解码：`subprocess.run(..., text=True, encoding='utf-8', errors='replace')`，CLI 侧 `sys.stdout.reconfigure(encoding='utf-8')`，避免 GBK 控制台乱码。
