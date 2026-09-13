---
title: "ADR-0030: AI 镜像拆分与 BuildKit 缓存"
owner: "tech-lead"
last_reviewed: "2026-09-13"
status: "active"
expires: "2027-09-13"
tags: ["adr", "docker", "buildkit", "image-split", "cache"]
related: ["0026-production-execution-resource-ownership.md", "0027-ai-local-first-gateway.md"]
---

# ADR-0030: AI 镜像拆分与 BuildKit 缓存

## 状态

已采纳。Batch 238 验证 split 契约并补齐构建缓存与镜像基线采集。

## 决策

1. 保留 `api` / `runner` / combined `runtime` 三个 Docker target。
2. API target 禁止包含 Node、DSH、Chromium、ffmpeg 等重运行时。
3. Split 部署继续通过显式 `docker-compose.execution.yml` overlay 启用，默认 combined 行为不变。
4. Pip/npm 使用 BuildKit cache mount；缓存不写入最终镜像 layer。
5. 模型权重和浏览器文件不进入应用源码 layer。
6. 镜像基线由 `collect-image-baseline.ps1` 采集；Docker 不可用时必须明确记录，不允许用估算值冒充测量值。
7. 前端重型图表/图谱/思维导图库独立 vendor chunk，SPA shell 不缓存，hashed assets 长缓存。

## 后果

- API 发布镜像可明显小于 runner。
- 依赖下载和前端构建的重复成本下降。
- 缓存与镜像大小可通过脚本持续观测。
- split 与 combined 仍并存，回滚成本较低。
