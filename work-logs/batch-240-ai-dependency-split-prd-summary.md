# Batch 240 — AI/RAG Python 依赖分层
> **Product (🟦)** | Date: 2026-09-14 | Status: Approved

## 1. 问题陈述

Batch 239 已提供独立 AI Gateway 服务，但 API image 仍继承完整 Python 依赖，包含 FastEmbed、ONNX Runtime、NumPy 和 Playwright。控制面虽已拆出，包体边界仍未闭合。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| API lock 含 AI/RAG 重依赖 | 是 | 否 |
| AI Gateway lock | 无 | 含 FastEmbed/ONNX/NumPy，不含 Playwright |
| Runner lock | 无 | 含 AI + Playwright 完整运行时 |
| API 干净 venv 导入 | 未验证 | 仅安装 API lock 可 `import app.main` |
| 版本一致性 | 无 | 三套 lock 受现有 requirements.lock 约束 |

## 3. 非目标

- 不切换默认 Compose 为 split（C239-2）。
- 不替代真实 Docker 全链路 smoke（C239-3）。
- 不改变业务 API/前端。
- 不把浏览器包放入 AI Gateway。

## 4. 验收标准

- `requirements.api.lock` 不含 `fastembed/onnxruntime/numpy/playwright`。
- `requirements.ai.lock` 含 AI/RAG，不含 Playwright。
- `requirements.runner.lock` 含完整运行时。
- Dockerfile 新增 `builder-api`、`builder-ai`、`runtime-api-base`、`runtime-ai-base`。
- API target 继承 `runtime-api-base`；AI Gateway 继承 `runtime-ai-base`。
- 仅安装 API lock 的干净 venv 可导入 `app.main`。
