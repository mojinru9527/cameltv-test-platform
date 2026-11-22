# V1.6 staging 灰度 / 监控证据（2026-11-22）

环境：测试机 `aiqe-test-net`，独立 DB `aiqe_v16_test`，API 镜像 `cameltv-tp-backend:v16-api`（711 MB）。

## 部署

- 容器 `aiqe-v16-backend`，端口 `127.0.0.1:18001`，健康检查 `/api/v1/open/health` 200；
- 原生 `/api/v1/aiqe/metrics` 200，暴露 21 个 `aiqe_*` 指标；
- Prometheus job `aiqe-v16-backend`：**up**；
- 真实查询：
  `aiqe_run_queued_age_seconds{job="aiqe-v16-backend"} 0`；
- AIQE 告警规则：3 组 / 21 条已加载；
- AIQE 自检告警经 Prometheus → Alertmanager → webhook 送达（测试后已移除自检规则）。

## 灰度阶段

Environment ID `1`，TargetPolicy `17d19114-ac99-4d6e-be26-f247c87aded3` version 1：

| 阶段 | Run ID | 结果 |
|---|---|---|
| Shadow | `9fb84240-8906-4a17-9338-b368718e38c4` | COMPLETED / PASS |
| Dogfood | `9804b240-524c-44de-99b8-e8f8f6581853` | COMPLETED / PASS |
| 小流量 #1 | `be4e64cb-6f2a-40a7-bf65-e27fd3ab018f` | COMPLETED / PASS |
| 小流量 #2 | `e5ef2ebf-3579-43fa-b5f1-698c68b86f38` | COMPLETED / PASS |
| 小流量 #3 | `4bc9b025-b8e9-4e7f-a339-720ad8b42912` | COMPLETED / PASS |

Shadow 的 Policy decision = ALLOW，目标 `http://aiqe-test-nginx:80/api/v1/open/health`，policy_version=1。

## 未完成

- Stage 4「扩大范围」观察完整业务周期；
- Stage 5「GA」发布审批；
- Vault 生产持久化/自动解封/TLS（当前测试为 dev 模式）；
- 迁移链修复：AUD-007 boolean 修复、policy_status 表名修复、v1.6 catalog/AUD merge revision、V1.6 API 镜像重建。

因此 V16-024-R3 仍为 **PARTIAL**。

