# Batch 238 — 镜像拆分与包体缓存优化（Phase 4）— PM Plan
> **PM (🟨)** | Date: 2026-09-13

## 开发任务
### [x] Task 1: Docker target 拆分契约
**描述**: 验证已有 API/runner targets 和 opt-in execution overlay。
**验收**: API 段无 Node/Chromium；runner 段保留重型运行时。
**文件**: `tests/test_image_split_cache_contract.py`

### [x] Task 2: BuildKit 缓存
**描述**: backend pip/npm 与 frontend npm 增加 cache mount。
**验收**: Dockerfile 契约测试通过，镜像外缓存不进入 layer。
**文件**: `backend/Dockerfile`、`frontend/Dockerfile`

### [x] Task 3: 镜像基线采集
**描述**: 增加可重复采集脚本，记录 Docker 可用性、镜像大小、target/cache 状态。
**验收**: 本机 Docker 关闭时明确输出 unavailable，不伪造数据。
**文件**: `scripts/deploy/collect-image-baseline.ps1`

### [x] Task 4: 前端包体与缓存
**描述**: 拆分 charts/graph/mindmap vendor chunk；index.html no-store。
**验收**: build/typecheck/lint 通过；nginx 契约通过。
**文件**: `vite.config.ts`、`nginx.conf`

### [x] Task 5: 证据与回归
**描述**: 记录历史真实镜像基线并运行全量门禁。
**验收**: 后端/前端全量回归、F821、deploy contract 全绿。
**文件**: `work-logs/evidence/batch-238-image-split-cache/`

## 质量要求
- [x] 默认行为不变  - [x] 无模型权重进入 API 镜像  - [x] 缓存策略可验证
