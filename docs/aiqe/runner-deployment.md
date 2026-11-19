# AIQE Runner 部署配置（Test / Prod）

> 适用：把外部 Runner（浏览器/真机/小程序）接入 AIQE 平台。平台只做登记、调度、证据；
> Runner 在本地执行并回传结果（ADR-0026）。

## 1. 一次性准备

### 1.1 注册节点令牌（每个环境、每个项目独立）

用有 `apitest:execute` 权限的账号：

```bash
curl -X POST "https://<平台地址>/api/v1/ai/agents/register" \
  -H "Authorization: Bearer <用户token>" \
  -H "X-Project-Id: <项目ID>" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"aiqe-runner-prod-01","capabilities":["api","aiqe:http","aiqe:playwright","aiqe:appium","aiqe:external_e2e"]}'
```

返回的 `token` 只出现一次，保存到 Runner 密钥文件；换机/泄露用
`POST /api/v1/ai/agents/tokens/revoke` 吊销。

### 1.2 登记能力清单（平台主机，运维脚本）

Runner token 只证明身份；Preflight 依赖 `node_capability_manifests`：

```python
from app.core.db import SessionLocal
from app.aiqe.services.capability_registry import register_manifest, mark_verified

db = SessionLocal()
register_manifest(
    db,
    node_id="aiqe-runner-prod-01",
    driver_key="playwright",
    driver_version="1.5x",
    runner_version="aiqe-runner-1.0.0",
    capabilities=["aiqe:playwright", "aiqe:appium"],
    platforms=["web_desktop", "android"],
    max_parallel_sessions=2,
    artifact_types=["SCREENSHOT", "PLAYWRIGHT_TRACE", "HAR", "RUNNER_LOG"],
    evidence_ref="<真实验收 Artifact ID>",
)
mark_verified(
    db, "aiqe-runner-prod-01",
    platforms=["web_desktop", "android"],
    evidence_ref="<真实验收 Artifact ID>",
)
db.commit()
```

`driver_version` / `runner_version` 变化会自动使 VERIFIED 失效（SOFTWARE_UPDATED_REVERIFY_REQUIRED）。

## 2. Runner 启动

```bash
export AIQE_AGENT_TOKEN="agt_..."
export AIQE_SECRETS_JSON='{"ADMIN_PASSWORD":"..."}'
python scripts/qa/aiqe_local_runner.py \
  --base-url https://<平台地址> \
  --project-id <项目ID> \
  --node-id aiqe-runner-prod-01 \
  --agent-token "$AIQE_AGENT_TOKEN" \
  --capability-heartbeat-interval 15 \
  --interval 3
```

依赖：

- Python 3.12 + `pip install -r requirements.txt`
- Playwright：`pip install playwright && playwright install chromium`
- Android：`adb` + Appium + UiAutomator2 driver
- 小程序（后续）：微信开发者工具 + minium
- NTP 时间同步、日志目录、专用系统账号

## 3. 能力心跳（关键）

平台 Preflight 的 manifest 心跳 TTL 是 **30 秒**；Runner 会每
`--capability-heartbeat-interval`（默认 15s）调用：

```http
POST /api/v1/aiqe/nodes/{node_id}/heartbeat
X-AI-Agent-Token: agt_...
```

返回 `capability_status` / `effective_status` / `next_heartbeat_seconds`。
行为：

- 心跳过期 → `UNAVAILABLE`；收到心跳后恢复 `AVAILABLE`（有 evidence）或 `VERIFIED`；
- `DEGRADED` 保持降级；`REVOKED` 返回 409，不允许靠心跳复活；
- manifest 缺失返回 404，Runner 只在日志里提示，不会退出（需运维先登记 manifest）。

## 4. Test / Prod 配置差异

| 项 | Test | Prod |
|---|---|---|
| `--base-url` | `https://<test-platform>` | `https://<prod-platform>` |
| project / node_id | 测试项目 / `aiqe-runner-test-01` | 生产项目 / `aiqe-runner-prod-01` |
| 节点 token | 独立 | 独立，定期轮换 |
| 出站 allowlist | 平台 + Test Camel（`192.168.50.170:443`）+ DNS | 平台 + Prod Camel + 对象存储 + DNS |
| `AIQE_INPROCESS_EXECUTOR_ENABLED` | `true`（http 进程内） | 全量 Runner 时 `false`；只跑 UI/真机时 `true` |
| `UITEST_EXECUTION_MODE` | `node` | `node` |
| `AIQE_RECONCILER_ENABLED` | `true` | `true` |
| 证据存储 | 本地目录 | 持久盘/对象存储 + 保留期 |
| 运行方式 | 手动/计划任务 | systemd/NSSM，`Restart=always`，日志轮转 |

## 5. 守护进程示例（Linux）

```ini
[Unit]
Description=AIQE Runner
After=network-online.target

[Service]
User=aiqe
WorkingDirectory=/opt/cameltv
EnvironmentFile=/etc/aiqe-runner.env
ExecStart=/opt/cameltv/.venv/bin/python scripts/qa/aiqe_local_runner.py \
  --base-url https://<platform> --project-id <id> \
  --node-id aiqe-runner-prod-01 --agent-token ${AIQE_AGENT_TOKEN} \
  --capability-heartbeat-interval 15
Restart=always
RestartSec=5
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

Windows 可用 NSSM 注册为服务，工作目录仓库根，日志重定向到 `~/.cameltv-node/logs/`。

## 6. 上线验收

1. `POST /execution-jobs/claim` 能认领任务，`node-status` 在线；
2. `POST /aiqe/nodes/{node_id}/heartbeat` 返回 `AVAILABLE`/`VERIFIED`；
3. 平台 Preflight 对目标节点为 `READY`；
4. 跑一条 UI/Android Workflow，Artifact sha256 对账通过；
5. 杀掉 Runner → 租约过期任务回 `pending`，重启后继续；
6. 版本变更后 VERIFIED 失效，重新验收后才能恢复。

## 7. 出口防火墙

Runner 出站只放行平台、被测环境、对象存储与 DNS；策略与云安全组映射见
[`runner-egress.md`](evidence/runner-egress.md) 与
[`policy.json`](evidence/runner-egress/policy.json)。
