# Batch 240 — AI/RAG Python 依赖分层 — PM Plan
> **PM (🟨)** | Date: 2026-09-14

## 开发任务
### [x] Task 1: 依赖输入与 lock
- `requirements.api.txt/lock`
- `requirements.ai.txt/lock`
- `requirements.runner.txt/lock`

### [x] Task 2: Docker builder/runtime base
- `builder-api` / `runtime-api-base`
- `builder-ai` / `runtime-ai-base`
- 保持 combined `runtime` 不变

### [x] Task 3: Target 继承修正
- api → runtime-api-base
- ai-gateway → runtime-ai-base
- runner → runtime-base

### [x] Task 4: 契约测试
- lock 包集断言
- stage 继承断言
- API clean venv import smoke

### [ ] Task 5: 真实镜像大小复采
- 留 C239-2/3，需要 Docker host。
