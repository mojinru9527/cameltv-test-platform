# Batch 238 — 镜像拆分与包体缓存优化（Phase 4）— Leader Verdict
> **Leader (🎯)** | Date: 2026-09-13 | Decision: 有条件通过（待总确认 + required checks）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | A | 复用已有双 target，补齐缓存与契约，不冒险切默认 |
| 风险 | 低 | Split overlay opt-in；combined 回滚保留 |
| 覆盖 | A | Docker/Compose、前端 chunk、缓存策略、基线脚本均有测试 |

## 关键决策

1. 保留 combined `runtime` 为默认，split 只走显式 overlay。
2. API target 禁止 Node/DSH/Chromium；runner target 保留重型运行时。
3. Pip/npm 使用 BuildKit cache mount，缓存不进入镜像 layer。
4. 模型/浏览器缓存继续外挂卷，不进入源码 layer。
5. Docker daemon 不可用时只记录 unavailable，不用估算代替真实测量。

## 抽检通过

- ✅ `Dockerfile` — `api` / `runner` / `runtime` targets 与 cache mount
- ✅ `docker-compose.execution.yml` — split target 映射
- ✅ `scripts/deploy/collect-image-baseline.ps1` — 基线采集
- ✅ `vite.config.ts` / `nginx.conf` — 前端缓存分块与 SPA shell 策略
- ✅ `pytest -q` — 2672 passed / 11 skipped / 1 xfailed
- ✅ 前端 typecheck / lint / build — 全部通过

## 判决

有条件通过。条件：

1. 用户完成 Batch 238 一次总确认（推送 + Draft PR + required checks 通过后合入 main）。
2. Draft PR 创建后通过 `audit-ai-pr.ps1`，等待 required checks 全绿。
3. 最终审计通过后再更新为 APPROVED。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 已有 split target 缺少自动化契约 | 新增 image split contract tests | `tests/test_image_split_cache_contract.py` |
| pip 原 `--no-cache-dir` 使 cache mount 无意义 | 改为 BuildKit cache mount，保留 hash 锁定 | `backend/Dockerfile` |
| 前端重库可能导致 chunk 失效联动 | 独立 charts/graph/mindmap vendor chunks | `vite.config.ts` |

**技能使用**: `cameltv-agent-team` → 判决与回写；`cameltv-bug-guard` → Docker/Compose/缓存边界。
