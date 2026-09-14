# Batch 240 — AI/RAG Python 依赖分层 — Leader Verdict
> **Leader (🎯)** | Date: 2026-09-14 | Decision: 有条件通过（待总确认 + required checks）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | A | 三套 hash lock 与独立 runtime base 完整 |
| 风险 | 中 | 尚未在 Docker host 实际构建新镜像 |
| 覆盖 | A | lock 包集、base 继承、API 导入冒烟均有测试 |

## 关键决策

1. API lock 不包含 FastEmbed、ONNX、NumPy、Playwright。
2. AI Gateway 保留本地 Embedding 依赖，但不携带浏览器包。
3. Runner 保留完整 AI/浏览器能力。
4. 三套 lock 受现有 `requirements.lock` 约束，避免版本漂移。
5. 默认 combined 不变；真实镜像构建与 split 切换仍留 C239-2/3。

## 抽检通过

- ✅ `requirements.api.lock` — 无 AI/RAG/浏览器重依赖
- ✅ `requirements.ai.lock` — 有 FastEmbed/ONNX，无 Playwright
- ✅ `requirements.runner.lock` — 完整运行时
- ✅ `Dockerfile` — builder/runtime base 分层
- ✅ API 干净 venv — 安装 API lock 后可导入 `app.main`
- ✅ 部署/镜像契约 — 21 passed
- ✅ 后端全量 — 2681 passed / 11 skipped / 1 xfailed

## 判决

有条件通过。条件：

1. 用户完成 Batch 240 一次总确认（推送 + Draft PR + required checks 通过后合入 main）。
2. Draft PR 创建后通过 `audit-ai-pr.ps1`，等待 required checks 全绿。
3. 最终审计通过后再更新为 APPROVED。

## 下一批次 Leader 条件

- C239-2: 真实 Docker host 完成 API→AI Gateway→runner 全链路 smoke 后切默认 split。
- C239-3: 发布 profile 支持 split/combined rollback，AI_GATEWAY_TOKEN/IMAGE 缺失时 fail-closed。
- C240-1: 记录新 API/AI Gateway/Runner 实际镜像大小和共享层，验证 API image 体积下降。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| API 与 Runner 共享同一完整 Python venv | 新增 API/AI/Runner 三套 lock 与 base | Dockerfile + requirements.* |
| 直接取最新依赖会造成版本漂移 | 使用现有 requirements.lock 约束三套 lock | build inputs |

**技能使用**: `cameltv-agent-team` → 判决与回写；`cameltv-bug-guard` → Docker、lock、导入边界。
