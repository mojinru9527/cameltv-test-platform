# Batch 247 — PM Plan

## Tasks

| # | Task | Files | Acceptance |
|---|---|---|---|
| 1 | 新增内置 RapidOCR CLI | `backend/app/services/lanhu_evidence/rapidocr_cli.py` | 逐行 JSON 输出，兼容 `parse_command_output` |
| 2 | 默认配置与子进程协议 | `config.py`, `local_ocr_provider.py`, `.env.example` | `{python}`/`{image}` 替换、UTF-8 子进程、取消低置信度过滤 |
| 3 | 截图 2x DPR | `screenshot_service.py`, `config.py` | Playwright `device_scale_factor` 默认 2.0 |
| 4 | 依赖与镜像系统库 | `requirements*.txt`, `requirements*.lock`, `Dockerfile` | runner 锁包含 OCR 依赖；Linux 可导入 cv2/rapidocr |
| 5 | 回归与真实 OCR 证据 | tests, QA report | 单测/全量回归/Windows + Linux 锁校验/真实截图 OCR |

## Constraints

- 保留旧 `ocr_paddle.py` 作为可选外部引擎，不把它设为默认。
- 不改变 canonical ExecutionRun；本批只处理蓝湖证据 Worker 的 OCR 能力。
- 依赖版本受现有 `requirements.lock` 约束，避免无关版本漂移。
