# V1.6 生产就绪状态（2026-11-24 审计后修订）

**STATUS: NOT_PROVEN**
**唯一事实源：`governance/production-evidence.json`（机器判定见 `release-verdict.json` Gate F）**

旧版本（2026-11-22/23）在本文件内同时写“未在真实基础设施执行”和“staging/PG/Vault PASS”，
结论自相矛盾。本版本只保留可校验状态：

## 1. 生产阶段状态（来自 production-evidence.json）

| 阶段 | 状态 | 说明 |
|---|---|---|
| Shadow / Dogfood / 小流量 | NOT_PROVEN | 文档记录 Run PASS，但未归档 Run/Job/Assertion/Artifact 机器产物 |
| Stage 4 扩大 / Stage 5 GA | NOT_PROVEN | `Staging-V16-Run-Evidence.md` 与 `Production-Readiness` 记录未执行；旧 GA 报告却写已完成 |
| PostgreSQL 备份恢复 | NOT_PROVEN | 仅有“178 表一致”文本，无 pg_dump/restore 原始日志；`Platform-Residual-Resolution.md` 另记 staging 恢复 NOT_RUN |
| Vault 生产模式 | NOT_PROVEN | `Vault-Transit-Deployment.md` 明确为 dev 模式（重启丢数据） |
| 监控告警联调 | NOT_PROVEN | 仅有规则加载与自测投递记录，无 Alertmanager 触发证据 |
| 容器 egress 集群实测 | NOT_PROVEN | 旧 GA 报告勾选项自身写着“集群实测 NOT_RUN” |
| 镜像自包含 | NOT_PROVEN | 仓库侧已把 sqlglot 固化进 API/Runner lock；仍需重建镜像并记录 digest |
| 生产 smoke | NOT_PROVEN | health 200 仅为部署记录，无 digest / commit 一致性校验 |

## 2. 镜像可重建性（本批次已修）

- 背景：`app/aiqe/security/sql_policy.py` 在 API 进程内 `import sqlglot`，而
  `Dockerfile` 使用 `requirements.api.lock` / `requirements.runner.lock`；
  这两个 lock 之前**不含** sqlglot，生产只能靠 `/opt/aiqe-v16-deps` 运行时挂载规避。
- 现状：`sqlglot==30.33.0` 已加入 `requirements.api.txt`，并写入
  `requirements.api.lock` / `requirements.runner.lock`（含 sha256 hash）；
  `tests/test_aiqe_v16_024_image_dependencies.py` 锁定该约束。
- 仍缺：从 release commit 干净重建镜像、记录 digest/SBOM、部署到干净节点并跑
  Read-only / 安全负向 / Regression 各一个真实 Run。

## 3. Vault 说明

`Vault-Transit-Deployment.md` 与 2026-11-22 GA 决策记录的“生产 TLS/Shamir/持久化”
没有配套配置导出或重启验证日志，因此**不得**作为生产 KMS 已就绪的证据。
需要：脱敏后的 `vault status`/`vault operator init` 记录、持久化存储配置、
重启后 unseal 与 Transit 加解密验证日志。

## 4. 关闭 Gate F 的最小动作

1. 重建镜像并记录 digest：`deploy/release-console/image_contract.py` 校验镜像包含
   `alembic/versions` / `alembic.ini`；
2. 干净节点部署并执行 migration upgrade/downgrade/upgrade；
3. 跑三类真实 Run（Read-only / 安全负向 / Regression）并归档产物；
4. PG 备份恢复原始日志、Vault 生产配置脱敏记录、Alertmanager 触发证据；
5. 把以上 artifact 路径写入 `governance/production-evidence.json` 对应 stage，
   再运行 `python scripts/aiqe/release_verdict.py --write` 重算 Gate F。

## 5. 停止条件与回滚

灰度各阶段必须预置停止条件，触发即停并回滚，不得以“继续观察”豁免：

| 阶段 | 停止条件（任一触发） | 回滚动作 |
|---|---|---|
| Shadow | Run 失败率 > 5% 或出现 P0 断言回归 | 关闭影子流量并保留证据 |
| Dogfood | 出现 Secret 明文 / 越权访问 / 目标策略绕过 | 立即停止，按安全事件处理并回滚镜像 |
| 小流量 | 5xx > 1%、延迟 P95 翻倍、告警风暴 | 回滚上一镜像 digest，恢复上一版本 |
| 扩大 | 数据污染 / 并发串行失效 / 备份失败 | 停止扩量，执行备份恢复演练 |
| GA | Gate A–G 任一 NOT_PROVEN/FAIL | 不签署 GA，版本锁保持上一个 release |

回滚流程与数据库恢复步骤见 `V1.6-Rollback-and-Recovery.md`；
备份恢复必须保留原始日志（pg_dump/restore、校验和），仅“178 表一致”的文本记录不算证据。

