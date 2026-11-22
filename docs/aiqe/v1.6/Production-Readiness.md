# AIQE V1.6 生产就绪、灰度与回滚（V16-024）

> 结论先行：代码/配置门禁已落地；**真实 staging 灰度演练、HA/备份恢复演练、KMS 接入尚未在真实基础设施执行**，
> 因此 V16-024 标记为 IMPLEMENTED，发布报告不得声称 PRODUCTION_OBSERVED。

## 1. 部署拓扑（最小权限）

| 组件 | 身份/权限 | 网络 |
|---|---|---|
| API | 非 root、只读根文件系统 | 仅 ingress；出站经 egress proxy |
| Worker | 非 root、独立 ServiceAccount、最小 DB 权限 | 仅 DB/队列；禁止公网直连 |
| Browser Runner | 非 root、CPU/内存/PID/FD 限制、只读根 | **egress deny-by-default**，仅 proxy（3128）与 DNS（53） |
| Device Runner | 非 root、设备池独占、设备租约 | 仅 Appium/设备网段 |
| DB Query Runner | **独立只读账号 + 只读连接池** | 仅 DB 只读端点 |

容器 egress 事实源：`deploy/aiqe/egress-networkpolicy.yaml`（默认拒绝 + 仅 proxy + 元数据/私网 denylist），
由 `scripts/aiqe/check_container_egress.py` 校验。云元数据地址强制阻断（169.254.169.254、100.100.100.200、fd00:ec2::254）。

## 2. 必须监控/告警

见 `docs/aiqe/v1.6/observability/Monitoring-and-Alerts.md` 与 `aiqe-alerts.yaml`。
P0：Secret Canary、TargetPolicy 不可用、跨项目访问成功/尝试；P1：lease/fencing/无 Job/无断言/Agent 证据失败。
任意 P0 告警触发即停止扩大流量并回滚。

## 3. 灰度发布顺序与停止条件

| Stage | 内容 | 进入条件 | 退出条件 |
|---|---|---|---|
| 0 离线验证 | 单测/集成/安全/E2E 全绿，不接生产数据 | 本分支 CI 全绿 | 无 P0/P1 未解释失败 |
| 1 **Shadow** | 生产只读影子执行，不写业务数据，对比旧流程 | Stage 0 + 监控/告警启用 | 差异可解释、无 Secret/SSRF 漏拦 |
| 2 **Dogfood** | 内部 Project/Environment/Driver，人工审批外部副作用 | Stage 1 观察一个窗口 | 无 P0/P1，人工审批记录完整 |
| 3 **小流量** | 低风险项目/Workflow，限制并发/超时/域名/数据范围 | Dogfood 通过 | 错误率/延迟在 SLO 内 |
| 4 扩大范围 | 观察至少一个完整业务周期 | 小流量稳定 | 告警/误报/漏报/资源/恢复均达标 |
| 5 **GA** | 发布审批签字 | 全部 GA Gate 达标 | — |

**停止条件**（任一命中立即停止扩大并回滚/隔离）：
- Secret Canary 非零 / 持久化数据出现明文；
- SSRF 测试目标实际收到被拒绝请求；
- 跨 Project 资源访问成功；
- Run PASS 但无业务 Assertion 或 required Evidence；
- Noise/Regression 创建 Run 但无 Job，或终态无法收敛；
- Worker fencing 失效（迟到结果覆盖新结果）；
- 错误率/延迟超 SLO 且观察窗口内无法恢复。

回滚：应用回滚使用上一 release tag（`release/aiqe-v1-6` 之前的稳定 tag）；数据库采用 Expand→Migrate→Contract，
不可逆迁移必须 forward-fix 或恢复演练过的备份。

## 4. 备份与恢复

- 每日全量 + 持续 WAL/binlog；备份保留 ≥ 30 天；每月恢复演练一次。
- 演练步骤：择一备份 → 恢复至隔离实例 → `alembic upgrade head` → 行数/关键表校验 → 记录 RPO/RTO。
- 对象存储 Artifact 与 DB 元数据分开备份；恢复后执行 `verify_integrity` 抽样（Artifact checksum）。
- Secret/KMS 单独备份与轮换演练；禁止把明文密钥写入备份仓库。
- 恢复脚本/命令、负责人、RPO/RTO 目标写入发布报告；**未演练不得宣称可恢复**。

## 5. 生产回滚演练记录（待执行）

| 项 | 状态 | 证据 |
|---|---|---|
| staging 灰度（Shadow→Dogfood→小流量） | NOT_RUN | 需真实基础设施与业务只读副本 |
| DB 备份恢复演练（本地 SQLite） | **PASS（脚本+测试）** | `scripts/ops/aiqe_backup_restore_drill.py` + `test_aiqe_v16_024_backup_drill.py`（integrity/revision/SHA256） |
| DB 备份恢复演练（staging PostgreSQL） | NOT_RUN | 需生产同构数据库 |
| 容器 egress 策略实测（云元数据拒绝） | NOT_RUN（策略文件已校验） | 需 Runner 集群 |
| KMS/外部 Secret Manager | **PASS（测试）** | Vault Transit 容器 encrypt/decrypt + fail-closed 测试；dev 模式，生产持久化待办 |
| 监控告警联调（Prometheus→告警通道） | **PASS（合成自检）** | Prometheus/Alertmanager/webhook 已部署并收到告警；AIQE metrics 路由仍缺 |

以上 NOT_RUN/BLOCKED 不计入通过率，发布报告必须披露。

## 6. 2026-11-22 staging 实测

- Stage 1 Shadow / Stage 2 Dogfood / Stage 3 小流量共 5 个 Run 全部 PASS（详见 `Staging-V16-Run-Evidence.md`）。
- Prometheus target `aiqe-v16-backend` up，21 条 AIQE 规则已加载，自检告警已送达 webhook。
- Stage 4/Stage 5 仍未执行；Vault 仍为测试 dev 模式。
