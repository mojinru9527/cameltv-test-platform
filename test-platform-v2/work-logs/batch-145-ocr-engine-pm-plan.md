# Batch 145 — PM Plan
> **PM (🟨)** | Date: 2026-08-11

## 规格摘要
**原始需求**: 用户反馈 OCR 识别截图文字缺失遗漏；选型确认 rapidocr（onnxruntime）为 CPU 中文 OCR 最优解；按授权方案接入（内置引擎 + 保留低置信度 + 2x 截图 + 前端展示最全文本）。
**目标时间**: 2026-08-11（单批完成）
**批次档位**: 完整批次（新依赖 + 新配置 + 新行为）

## 开发任务
### [ ] Task 1: 依赖接入与锁文件更新
**描述**: `requirements.txt` 增加 `rapidocr_onnxruntime>=1.4.4`；用 pip-compile 增量生成 5 个新包块（rapidocr-onnxruntime/opencv-python/pyclipper/shapely/six）合并进 `requirements.lock`，并分别在 Windows venv 与 Linux 容器验证 `pip install --require-hashes`。
**验收标准**: - `requirements.lock` 含 5 个新包且 win/linux 安装通过 - 其余 112 包版本不变
**涉及文件**: - `test-platform-v2/backend/requirements.txt` — 新增依赖 - `test-platform-v2/backend/requirements.lock` — 合并新包块

### [ ] Task 2: 内置 rapidocr OCR CLI
**描述**: 新增 `app/services/lanhu_evidence/rapidocr_cli.py`：`--image` 参数读图 → RapidOCR 识别 → stdout 逐行输出 `{"text","confidence","bbox"}`（bbox 由 4 点框转 x1,y1,x2,y2），兼容现有 `parse_command_output`；异常输出 stderr 并非零退出。
**验收标准**: - `python -m app.services.lanhu_evidence.rapidocr_cli --image <png>` 输出逐行 JSON - 中文截图实测识别文本正确
**涉及文件**: - `backend/app/services/lanhu_evidence/rapidocr_cli.py` — 新增

### [ ] Task 3: 配置默认值与 .env.example
**描述**: `config.py` 中 `lanhu_ocr_command` 默认值改为内置 CLI 命令模板；新增 `lanhu_capture_device_scale_factor: float = 2.0`；`.env.example` 补充 OCR 与截图 DPR 配置说明。
**验收标准**: - 默认无环境变量时 OCR 走内置 CLI - 新配置项在 settings 可见且类型正确
**涉及文件**: - `backend/app/core/config.py` - `backend/.env.example`

### [ ] Task 4: 保留低置信度文本
**描述**: `local_ocr_provider.py` 移除 `min_conf` 过滤，保留全部识别块；置信度仅记录在块上。
**验收标准**: - 单测覆盖低置信度块不再被丢弃
**涉及文件**: - `backend/app/services/lanhu_evidence/local_ocr_provider.py`

### [ ] Task 5: 截图 2x DPR
**描述**: `screenshot_service.py` 在 `browser.new_page()` 传 `device_scale_factor=settings.lanhu_capture_device_scale_factor`。
**验收标准**: - 代码核对 + 现有 screenshot 单测通过
**涉及文件**: - `backend/app/services/lanhu_evidence/screenshot_service.py`

### [ ] Task 6: Dockerfile 系统库
**描述**: 在 apt 安装列表追加 opencv-python 所需系统库。
**验收标准**: - Linux 容器内 `import cv2` 成功
**涉及文件**: - `test-platform-v2/backend/Dockerfile`

### [ ] Task 7: 测试与文档
**描述**: 新增/更新单测（CLI 输出解析、低置信度保留、配置默认值）；前端 OCR 面板文案微调（「该页提取文字（OCR+DOM 合并）」）；更新部署/环境文档。
**验收标准**: - 受影响 pytest 全绿 - 前端 typecheck/build 通过
**涉及文件**: - `backend/tests/test_lanhu_ocr_merge.py` 等 - `frontend/src/pages/requirement/components/PrototypePreview.tsx`

## 质量要求
- [ ] 后端 `ruff check app --select F821`、受影响 pytest 全绿
- [ ] 前端 `npm run typecheck && npm run build` + 相关 vitest
- [ ] 无 console.log / print / debugger 调试遗留
- [ ] 锁文件双平台 `--require-hashes` 可安装
- [ ] OpenAPI 无变更（纯内部实现 + 配置）
