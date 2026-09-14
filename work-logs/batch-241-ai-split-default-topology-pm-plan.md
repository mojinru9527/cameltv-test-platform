# Batch 241 — PM 任务计划
> **PM (🟨)** | Date: 2026-09-14 | Status: Approved

## 1. 范围

| ID | 任务 | 关联条件 | 交付物 |
|----|------|---------|--------|
| T1 | 修复三套 lock 的 linux 平台解析缺陷（P0 阻断） | 新增 C241-1 | `requirements.api.lock` / `.ai.lock` / `.runner.lock` |
| T2 | 默认 Compose 切换为 split 拓扑 | C239-2 | `docker-compose.yml` |
| T3 | 提供 combined 回滚 overlay | C239-3 | `docker-compose.combined.yml` |
| T4 | release-console 增加 ai-gateway 制品通道与 fail-closed | C239-3 | `capacity.py` / `release_artifacts.py` / `tencent_executor.py` / `app.py` |
| T5 | 真实 Docker host 全链路 smoke 脚本 | C239-2 | `scripts/ops/smoke_ai_split_topology.py` |
| T6 | 三镜像体积与共享层实测证据 | C240-1 | `scripts/deploy/collect-image-baseline.ps1` 输出 + QA 报告 |
| T7 | 契约测试补齐 | T2/T3/T4 | `test-platform-v2/backend/tests/test_deploy_compose_contract.py` 等 |

## 2. 依赖与顺序

```
T1 (lock 修复) ─┬─> T5 (smoke 需要可构建镜像) ──> T6 (体积证据)
                └─> T2/T3 (compose 拓扑) ──> T7 (契约)
T4 (发布 profile) ─────────────────────────> T7
```

- T1 是硬前置：修复前 `api` / `ai-gateway` target 无法构建，T5/T6 均不可执行。
- T2/T3 必须在同一提交内落地，避免出现「默认 split 但无回滚路径」的中间态。
- T4 与 T2/T3 相互独立，可并行。

## 3. 风险与缓解

| 风险 | 等级 | 缓解 |
|------|------|------|
| 默认拓扑切换影响生产发布路径 | 高 | 保留 combined `runtime` target 与回滚 overlay；发布 profile 双模式契约测试 |
| lock 重生成引发版本漂移 | 中 | 以现有 `requirements.lock` 作 `--constraint`，逐包 diff，仅接受缺失的 linux 依赖新增 |
| 本地 Docker 与生产 TLS/端口差异 | 中 | smoke 使用一次性 Compose project 与随机端口，不复用生产凭据 |
| 容器内写盘权限（Windows 挂载） | 低 | 生成物经 diff 校验后由宿主写入 |

## 4. 里程碑

| 里程碑 | 出口条件 |
|--------|---------|
| M1 lock 修复 | 三 target `docker build` 全部成功 |
| M2 拓扑切换 | `docker compose config` 默认即 split；combined overlay 可回滚 |
| M3 真实验收 | smoke 脚本在本地真实 Docker host 全绿，产出 JSON 证据 |
| M4 交付 | required checks 全绿 + 最终审计通过 + Leader APPROVED |

## 5. 明确不做

- 不改 Alembic、不动数据库。
- 不重构 `app/` 业务代码（本批仅部署/发布面）。
- 不执行腾讯云生产发布。
