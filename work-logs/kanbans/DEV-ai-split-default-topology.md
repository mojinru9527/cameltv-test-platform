# Batch 241 Dev Kanban — AI split 默认拓扑与容器级验收
> **Dev (💻)** | Date: 2026-09-14 | Status: In Review

## 切片

| # | 切片 | 文件 | 状态 |
|---|------|------|------|
| S1 | 修复三套 lock 的 linux 平台解析缺陷（P0 阻断） | `requirements.api.lock` / `.ai.lock` / `.runner.lock` | ✅ |
| S2 | AI Gateway health 部署级 fail-closed | `app/ai_gateway_app.py` | ✅ |
| S3 | 默认 Compose 切 split 拓扑 | `deploy/docker-compose.yml` | ✅ |
| S4 | combined 回滚 overlay | `deploy/docker-compose.combined.yml`（新） | ✅ |
| S5 | 发布 profile ai-gateway 制品通道 + fail-closed | `deploy/release-console/*.py` | ✅ |
| S6 | 真机 split 全链路 smoke 脚本 | `scripts/ops/smoke_ai_split_topology.py`（新） | ✅ |
| S7 | 静态契约测试 | `tests/test_split_default_topology_contract.py`（新）+ 既有契约更新 | ✅ |

## 关键实现记录

### S1 根因
三套新 lock 在 **Windows** 上用 `pip-compile` 生成，平台标记按 win32 解析，导致
`secretstorage` / `jeepney` / `uvloop` 三个 linux-only 传递依赖缺失。
Linux 容器内 `pip install --require-hashes -r requirements.api.lock` 直接失败，
`api` 与 `ai-gateway` target **完全无法构建**（Batch 240 遗留 P0）。

修法：以上三包从 Linux 解析结果补齐，保持既有最小标记风格，三文件各 **+66 行 / -0 行**。
基准 `requirements.lock` 本身是通用锁（同时含 uvloop 与 pywin32），补齐后与之一致。

### S2
`/internal/ai/v1/health` 在 `ai_gateway_token` 为空时返回 **503**。
此前返回 200，导致 compose `--wait` 会把「无 token 的网关」判为健康，
把应用层 fail-closed 降级为首次调用才暴露。

### S3/S4
- base `docker-compose.yml`：`backend`/`volume-permissions` → `api` target；
  新增 `ai-gateway`（`ai-gateway` target）与 `runner`（`runner` target）服务。
- `extends: service: backend` 会**合并** `depends_on`，若 base backend 声明
  `depends_on: ai-gateway` 会产生 `ai-gateway -> ai-gateway` 自依赖；
  因此 ordering 交给 `up --wait` 统一门禁，base backend 不声明 split 依赖。
- `docker-compose.combined.yml` 用 `!reset` 覆写 `depends_on`，并把
  `ai-gateway`/`runner` 置入 `combined-disabled` profile 以在回滚时排除。

### S5
`release_parts(mode)` 统一 part 列表；`image_target()` 解决 `ai-gateway` →
`image_ai_gateway` 的属性名映射问题（`getattr(config, 'image_ai-gateway')` 不可用）。
`_compose` 的 combined 分支补 `-f docker-compose.combined.yml`，因为仓库默认已变 split。

## 阻塞与决策

| 项 | 决策 |
|----|------|
| 主机页面文件耗尽导致 docker CLI 崩溃 | 清理 12.38GB 可回收 build cache；smoke 改用 `up --no-build` 复用已构建镜像 |
| `requirements.runner.lock` 未被 Dockerfile 引用 | 保留并同步修复（runner target 实际用 `requirements.lock`），记入 C241-2 |
