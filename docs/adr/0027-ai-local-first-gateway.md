---
title: "ADR-0027: 本地优先 AI Gateway 与精确响应缓存"
owner: "tech-lead"
last_reviewed: "2026-09-13"
status: "active"
expires: "2027-09-13"
tags: ["adr", "ai", "local-first", "cache", "gateway"]
related: ["0022-ai-chain-reality-gate.md", "0010-knowledge-vector-embedding-hybrid-retrieval.md"]
---

# ADR-0027: 本地优先 AI Gateway 与精确响应缓存

## 状态

已采纳。Phase 0 基线与 Phase 1 精确缓存已在 Batch 235 落地；Phase 2–4 由后续批次继续。

## 日期

2026-09-13

## 背景

平台已有共享 `ai_client`、项目级 Provider 配置、供应商 usage 遥测和 AITDE Prompt 缓存键，但没有应用层精确响应缓存，也没有把本地推理运行时、模型权重和应用镜像边界明确分开。直接“把所有 AI 能力搬到本地”会把模型权重、CUDA、Node/DSH 和 Playwright 都塞进 API 镜像，导致包体膨胀并降低发布缓存命中率。

## 决策

1. 采用**本地优先、AI Gateway 统一收口、持久缓存、云端兜底**的演进路线。
2. Phase 0 先采集 Provider、Embedding、镜像运行时和缓存基线。
3. Phase 1 在共享 `ai_client` 前增加 opt-in 精确响应缓存：
   - 默认关闭；
   - 只有调用方显式提供 `cache_namespace` 且配置开启时启用；
   - 缓存键包含 project、provider、model、namespace、system/input hash、JSON 模式、max_tokens、temperature；
   - 缓存写入和读取失败不得阻断主 AI 调用；
   - 截断响应不缓存；
   - 命中时当前调用 usage 置零，原始用量保存为 `cache_saved_usage`，避免把复用结果虚报为新 Token 消耗。
4. Phase 2–3 再接入独立本地运行时、Shadow Mode 和 local-first 路由；模型权重不进 API 镜像。
5. Phase 4 再拆 API / AI Worker / UI Runner 镜像。

## 后果

### 正面影响

- 重复精确请求可以跳过上游调用。
- 缓存命中率、条目、namespace 和清理操作可观测。
- 缓存默认关闭且按项目隔离，降低错误复用和越权风险。
- 为本地模型路由和镜像拆分保留统一接入点。

### 负面影响 / 权衡

- 新增 `ai_response_cache` 表和迁移。
- 缓存失效依赖 namespace、Prompt/Schema 版本治理。
- 当前只解决精确命中，不解决语义相似命中。
- Phase 1 本身不会减少模型权重或 Node/DSH 镜像体积。

## 弃选方案

| 方案 | 否决理由 |
|------|----------|
| 直接把模型权重打进 API 镜像 | 镜像膨胀数 GB，更新和缓存命中反而变差 |
| 只依赖云端 Prompt Cache | 输出仍重复生成，平台无法控制准确命中率 |
| 默认缓存所有 AI 调用 | 高风险任务、截断输出和陈旧 Prompt 可能被复用 |
| 语义缓存直接命中最终测试用例 | 误命中会污染测试资产，Phase 1 明确禁止 |

## 关联

- 实现：`test-platform-v2/backend/app/services/ai_gateway/`
- 表迁移：`test-platform-v2/backend/alembic/versions/20260916_b235_ai_gateway_cache.py`
- 基线脚本：`test-platform-v2/backend/scripts/collect_ai_local_baseline.py`
