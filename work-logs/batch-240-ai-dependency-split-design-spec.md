# Batch 240 — AI/RAG Python 依赖分层 — Design Spec
> **Design (🎨)** | Date: 2026-09-14 | Status: Ready

## 依赖边界

| Runtime | lock | FastEmbed/ONNX | Playwright | Node/Chromium |
|---------|------|----------------|------------|---------------|
| API | `requirements.api.lock` | 否 | 否 | 否 |
| AI Gateway | `requirements.ai.lock` | 是 | 否 | 否 |
| Runner | `requirements.runner.lock` | 是 | 是 | 是 |

## Docker stages

```text
builder-api -> runtime-api-base -> api
builder-ai  -> runtime-ai-base  -> ai-gateway
builder     -> runtime-base     -> runner -> runtime
```

三套 lock 均以现有 `requirements.lock` 为 version constraint，避免子环境版本漂移。
