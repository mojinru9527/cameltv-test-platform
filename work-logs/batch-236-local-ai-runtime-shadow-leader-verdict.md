# Batch 236 — 本地 AI Runtime 与 Shadow Mode（Phase 2）— Leader Verdict
> **Leader (🎯)** | Date: 2026-09-13 | Decision: 有条件通过（待总确认 + required checks）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | A | Runtime 与应用镜像解耦，Shadow 失败隔离 |
| 风险 | 低 | 默认关闭；主链不依赖本地模型 |
| 覆盖 | A | 配置、采样、对比、失败、health、API 均有测试 |

## 关键决策

1. C235-1 的 runtime 与 Shadow 部分在本批实现；不把模型权重打进 API 镜像。
2. Shadow 使用后台线程 + 独立 Session，主响应不受影响。
3. 只保存结构化对比事实，不保存完整 Prompt/输出/Key。
4. local-first routing 与云端兜底留到 Phase 3。

## 抽检通过

- ✅ `app/services/ai_gateway/runtime.py` — 独立配置、health、Key 脱敏
- ✅ `app/services/ai_gateway/shadow.py` — 采样、后台执行、失败隔离、结构化对比
- ✅ `app/services/ai_client.py` — sync/async 主链与 configured transport 统一
- ✅ `app/models/ai_shadow_run.py` + migration — 持久化字段完整
- ✅ `pytest -q` — 2619 passed / 51 skipped / 1 xfailed
- ✅ 前端 typecheck / lint / build — 全部通过

## 判决

有条件通过。条件：

1. 用户完成 Batch 236 一次总确认（推送 + Draft PR + required checks 通过后合入 main）。
2. Draft PR 创建后通过 `audit-ai-pr.ps1`，等待 required checks 全绿。
3. 最终审计通过后再更新为 APPROVED；当前不得宣称已合入或已发布。

## 下一批次 Leader 条件

- C236-1: Phase 3 必须实现 local-first routing、shadow 证据到策略的转换，以及云端失败兜底。
- C236-2: Phase 4 拆分 API/AI Worker/UI Runner 镜像前，必须先记录镜像体积与构建缓存基线。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| sync/async transport 容易产生签名漂移 | 本批共享 `_call_configured_full`，主链与 shadow 复用 | `app/services/ai_client.py` |
| Shadow 可能持有请求 Session | 改为后台线程 + `SessionLocal`，只传结构化参数 | `app/services/ai_gateway/shadow.py` |
| 模型权重若进镜像会破坏 Phase 2 目标 | 设为显式非目标并写入 ADR/C 条件 | ADR-0028 + C236-2 |

**技能使用**: `cameltv-agent-team` → 判决与流程回写；`cameltv-bug-guard` → 异步/线程/迁移边界。
