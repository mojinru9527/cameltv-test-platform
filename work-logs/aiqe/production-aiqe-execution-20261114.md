# 生产 AIQE 真实执行启用与验证（2026-11-14）

> **结论**：生产已启用 AIQE 进程内 http 执行器，真实 Run `PROD-AIQE-c8edbcba` 执行通过
> （Run COMPLETED/PASS、node PASSED、attempt PASSED），平台矩阵从 0 节点变为 `可用节点 1/1`。

## 1. 变更（生产服务器）

| 项 | 内容 |
|----|------|
| 文件 | `/opt/cameltv-tp/test-platform-v2/deploy/docker-compose.override.yml` |
| 变更 | `backend.environment.AIQE_INPROCESS_EXECUTOR_ENABLED: "true"` |
| 备份 | `/root/docker-compose.override.yml.bak-20261114` |
| 生效 | `docker compose ... up -d backend`（容器重建，health 200） |
| 范围 | 仅 http driver 在控制面内执行；UI/设备仍需外部 runner |

## 2. 能力注册

```json
{
  "node_id": "prod-aiqe-inprocess",
  "driver_key": "inprocess-http",
  "capabilities": ["aiqe:http", "aiqe:api"],
  "platforms": ["linux"],
  "max_parallel_sessions": 2,
  "evidence_ref": "prod://swiftbugs.cn/release-m15/health-run"
}
```

平台矩阵（生产 UI）：`平台 1 / 能力 2 / 可用节点 1/1`，`aiqe:api` 与 `aiqe:http` 各 1 节点。

## 3. 真实 Run 结果

节点：`GET https://swiftbugs.cn/api/v1/open/health`，expected_status=200。

```json
{
  "run_key": "PROD-AIQE-c8edbcba",
  "run_id": "ef0779eb-7ff7-4f69-a0a9-4b0f0768630d",
  "job_id": 3,
  "run_status": "COMPLETED",
  "outcome": "PASS",
  "node_status": "PASSED",
  "attempts": ["PASSED"],
  "job_status": "success"
}
```

生产 UI `/runs`：`共 1 条`，`PROD-AIQE-c8edbcba | manual | COMPLETED | PASS`。

## 4. 回滚

```bash
cd /opt/cameltv-tp/test-platform-v2/deploy
cp /root/docker-compose.override.yml.bak-20261114 docker-compose.override.yml
docker compose --env-file /root/production.env.bak-20261109-235015 \
  -f docker-compose.yml -f docker-compose.override.yml up -d backend
```

回滚后执行器恢复关闭；已产生的 Run/attempt 保留为审计记录。

## 5. 说明与风险

- **控制面执行**：http 节点在 backend 进程内执行（`AIQE_INPROCESS_EXECUTOR_ENABLED=true`），仅 http；UI/设备节点不会被认领（留给 runner）；
- 生产未暴露 AIQE Run 创建 API，Run 仍由受控运维脚本创建，风险面有限；
- 若后续部署覆盖 `docker-compose.override.yml`，需重新应用该环境变量（或纳入发布清单）；
- 建议后续把该开关纳入部署模板并做开关审计。
