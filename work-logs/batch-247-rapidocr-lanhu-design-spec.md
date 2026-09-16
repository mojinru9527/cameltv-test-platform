# Batch 247 — Design Spec

## Runtime flow

```text
LanhuEvidenceJob
  -> screenshot_service.capture_page_segments(device_scale_factor=2.0)
  -> LocalCommandOcrProvider
  -> {python} -m app.services.lanhu_evidence.rapidocr_cli --image "{image}"
  -> parse_command_output
  -> OCR blocks (不过滤低置信度)
  -> merge_page_text(DOM + OCR)
```

## Dependency boundary

- `requirements.api.lock`: canonical API 只读服务，不引入 RapidOCR。
- `requirements.ai.lock`: AI Gateway，不引入浏览器/OCR。
- `requirements.runner.lock`: 蓝湖证据 Worker 与 Playwright Runner，包含 RapidOCR。
- `requirements.lock`: 本地开发、pr-check 与完整回归基线，包含 RapidOCR。

## Failure handling

- CLI 图片不存在：stderr + exit 2。
- OCR 初始化/识别异常：stderr + exit 1。
- Provider 未配置命令：保持 `unavailable`，由现有质量门禁转为人工复核路径。
- 命令非零退出：保持既有 `failed` 语义，不伪造成功。
