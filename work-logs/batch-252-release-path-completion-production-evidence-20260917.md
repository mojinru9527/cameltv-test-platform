# Batch 252 — 端到端发布验收证据（release.ps1 -Publish）

> Date: 2026-09-17/18 | Git SHA: `6bbc9cf9d7427bb6a41967cda609328e8528c460`（Batch 252 合入后 main）
> 目的：验证 **C248-8 修复后，发布脚本不再需要手工组装镜像**

## Deployment

| 项 | 值 |
|----|----|
| Release | `release-20260917-0008` |
| Deployment id | `52d1288ca1b548978cb0f853877f1b62` |
| State | **PRODUCTION_VERIFIED** |
| 运行时 | split（api / runner / ai-gateway / frontend / aitde-worker） |
| 执行命令 | `pwsh scripts/ops/release.ps1 -Tag release-20260917-0008 -RuntimeMode split -ExecutionConfig test-platform-v2/deploy/docker-compose.execution.yml -Publish` |

## 与上一版的关键差异：四个镜像全部脚本本机构建

| Part | 来源 | 备注 |
|---|---|---|
| backend (api) | **脚本本机构建**（`--network=host`） | digest `sha256:2b6b75ff8a11…`（因 Dockerfile 变更而变化） |
| frontend | **脚本本机构建** | digest `sha256:47d2f3b79b98…` |
| runner | **脚本本机构建** ✅（此前三轮发布都失败/被迫复用） | 含 Node 22 供给修复 |
| ai-gateway | **脚本本机构建** | — |

发布链路按脚本原样走完：`构建 → digest → 提交登记(DRAFT) → 容量门禁通过 → 并行上传 → 校验 → 发布 → 确认上线`。
**没有任何手工 `docker tag` / `docker save` / `scp` 介入**。

## 事件与迁移证据

```
1 | DRAFT           | production deployment registered: release-20260917-0008
2 | VALIDATED       | manifest validated
3 | PROD_DEPLOYING  | publish started
4 | PROD_OBSERVING  | publish succeeded; migration target=20260922_ai_agent_token actual=20260922_ai_agent_token
5 | PRODUCTION_VERIFIED | （POST /verify → production verified (health ok)）
```

⇒ 迁移作业在停旧容器之前执行、校验值等于 manifest target（C249-4 + C250-1 修复在生产同时生效）。

## 生产验证

| # | 检查 | 结果 |
|---|------|------|
| 1 | 6 个容器 | 全部 `healthy`（backend / frontend / runner / ai-gateway / aitde-worker / postgres） |
| 2 | `GET /api/v1/open/health` | `{"code":0,…,"version":"2.3.0"}` |
| 3 | 回滚锚点 | `cameltv-tp-*:release-20260917-0007`、`-0008` 四件套镜像在位 |

## 验收中暴露的问题

### 🟡 P2（新登记 C252-1）`release.ps1 -Publish` 在网络中断时误报"发布失败"

- **现象**：publish 请求在客户端侧抛 `API 失败: An error occurred while sending the request.`，
  脚本 `throw "发布失败"`；但**服务端实际完整执行成功**（容器重建 healthy、事件走到 `PROD_OBSERVING`、
  随后 `/verify` 返回 `production verified`）。
- **诱因**：本机到 `release.swiftbugs.cn` 的 TLS/链路在该时段不稳定（TCP 443 通、握手失败；
  服务端自测公网 HTTPS 返回 200、证书有效期至 2026-11-21，且 localhost:8111 正常）→
  长时间 publish 请求被中断，客户端只看连接错误。
- **风险**：运维会以为发布失败，可能重复发布或误触发回滚（生产其实已经切到新版本）。
- **建议**：publish/rollback 失败路径增加**状态核对（reconcile）**：请求异常后按 deployment id 查
  `/api/deployments/{id}` 与 `/events`，若已到 `PROD_OBSERVING/PRODUCTION_VERIFIED` 则按成功报告并提示"服务端已完成"。

### ⚪ 运维观察：容量需要按发布节奏回收

- 本轮上传后磁盘一度到 **94%（2.7G 可用）**；按既有策略（保护最近两次发布 + 48h + 容器引用）
  清理旧 release 标签镜像与构建缓存后回到 **8.1G（79%）**，锚点 `-0007`/`-0008` 保留。
- 建议把"发布后回收上一版 tar / 定期回收历史 release 镜像"固化为发布 SOP 的一步（当前靠人工判断）。
