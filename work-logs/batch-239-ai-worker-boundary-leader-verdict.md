# Batch 239 — 独立 AI Gateway 服务边界 — Leader Verdict
> **Leader (🎯)** | Date: 2026-09-14 | Decision: 有条件通过（待总确认 + required checks）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | A | AI 控制面已有独立 app、镜像 target 和 HTTP 契约 |
| 风险 | 中 | split overlay 新增关键依赖，真实容器 smoke 留后续 |
| 覆盖 | A- | 服务、Token、chat/embed、远程委派、递归防护均有测试 |

## 关键决策

1. AI Gateway 作为独立 Python 服务运行，不再要求 API 进程本地执行 AI。
2. API/runner/aitde-worker 通过内部 HTTP 访问 gateway。
3. Token 缺失 fail-closed，Gateway 角色禁止递归转发。
4. 默认 combined 拓扑不变；split overlay 仍为 opt-in。
5. FastEmbed/ONNX 依赖分层和默认 split 切换不在本批完成。

## 抽检通过

- ✅ `app/ai_gateway_app.py` — health/chat/embed 与 Token 鉴权
- ✅ `app/services/ai_gateway/remote.py` — API 远程客户端与 fail-closed
- ✅ `app/services/ai_client.py` — sync/async 远程委派
- ✅ `app/services/knowledge/embedding_service.py` — 远程嵌入与 Gateway 本地嵌入
- ✅ `Dockerfile` + execution overlay — `ai-gateway` target/service
- ✅ `pytest -q` — 2640 passed / 51 skipped / 1 xfailed

## 判决

有条件通过。条件：

1. 用户完成 Batch 239 一次总确认（推送 + Draft PR + required checks 通过后合入 main）。
2. Draft PR 创建后通过 `audit-ai-pr.ps1`，等待 required checks 全绿。
3. 最终审计通过后再更新为 APPROVED。

## 下一批次 Leader 条件

- C239-1: 拆分 Python AI/RAG 依赖与 lock，确保 FastEmbed/ONNX 不再进入 API image layer。
- C239-2: 在真实 Docker host 完成 API→AI Gateway→runtime 全链路 smoke，再切换默认 split 拓扑。
- C239-3: 发布 profile 必须同时支持 split 与 combined rollback，且 AI_GATEWAY_TOKEN/IMAGE 缺失时 fail-closed。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| API 进程仍承担 AI 控制面 | 新增独立 app、target 与 HTTP 契约 | `app/ai_gateway_app.py` + overlay |
| 远程配置缺 Token 可能静默回退 | remote_requested + token fail-closed | `ai_gateway/remote.py` |
| 响应类型契约易漂移 | 内部 API 明确 R 结构并测试 | `test_ai_gateway_service.py` |

**技能使用**: `cameltv-agent-team` → 判决与回写；`cameltv-bug-guard` → HTTP/进程/配置边界。
