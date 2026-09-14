# Batch 239 — 独立 AI Gateway 服务边界 — QA 报告
> **QA (🔍)** | Date: 2026-09-14 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 | 7 | 0 | 0 |

## 可执行门禁

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端全量 | `python -m pytest -q` | 0 | **2640 passed, 51 skipped, 1 xfailed**, 668.38s |
| 定向 AI/镜像契约 | `pytest tests/test_ai_gateway_service.py tests/test_image_split_cache_contract.py -q` | 0 | 11 passed |
| 后端 F821 | `ruff check app/ --select F821` | 0 | All checks passed |
| 前端类型 | `npm run typecheck` | 0 | PASS |
| 前端 lint | `npm run lint` | 0 | PASS |
| 前端构建 | `npm run build` | 0 | 3671 modules transformed；10.84s |
| Dev Gate | `pwsh scripts/git/dev-gate.ps1` | 2 | `PASS_WITH_WARN`：HARD=0，G1/G2 PASS |
| WARN 审计 | `run-warn-audit.ps1 -NoTrendAppend` | 2 | Batch 239 新增文件无告警；剩余为 main 既有漂移 |

## 逐条件验证

### C1: 独立 AI Gateway 进程
`app.ai_gateway_app:app` 可独立导入；`ai-gateway` Docker target 不包含 Node/DSH/Chromium。

### C2: 内部 chat/embed/health
`test_health_is_public_and_reports_role`、`test_chat_delegates_to_shared_client`、`test_embed_returns_vectors` PASS。

### C3: 内部 Token fail-closed
`test_chat_requires_internal_token` PASS；Token 未配置时服务返回 503。

### C4: API chat 远程委派
sync/async 远程分支测试 PASS；远程模式下不调用本地 `resolve_route`。

### C5: Embedding 远程委派
`test_embedding_service_uses_remote_gateway` PASS；远端向量归一化后保持现有 API。

### C6: 禁止递归委派
`test_remote_client_rejects_recursive_gateway_role` PASS；Gateway 角色不会再次转发。

### C7: Split overlay 集成
`test_opt_in_execution_overlay_uses_split_targets` PASS；新增 `ai-gateway` service，backend 等待其 health。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P2 | 内部服务返回 `R` 对象导致 FastAPI 响应校验失败 | 修复为 `model_dump()`；8 条服务测试通过 | ✅ 已修复 |
| 2 | P2 | API URL 已配置但 Token 缺失时曾静默回退 embedded | 改为 request-level fail-closed；测试通过 | ✅ 已修复 |

## 发布建议

状态: **READY（本地门禁）**  
必修复: 0  
建议修复: 0  

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 本会话完成 | 0/0/2/0 | 2 | 响应契约 + 配置失败策略 | 内部 API 先定 response contract；远程配置必须 fail-closed |

**技能使用**: `cameltv-agent-team` → 工件与门禁；`cameltv-bug-guard` → 进程边界、HTTP、配置与递归核查。
