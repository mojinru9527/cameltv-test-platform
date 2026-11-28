# 生产发布阶段证据归一化说明（FIX-010）

**状态：** 归一化完成，Gate F 仍为 `NOT_PROVEN`（禁止宣称 GA / 生产发布完成）
**依据：** `CamelTv_AIQE_V1.6.2_整改开发落地实施手册.md` §0.3、§11、§19
**原始事实来源：** `docs/aiqe/v1.6/evidence/production-stage-canary-eb20.json`（2026-11-27T14:06:31Z 采集）
**修正文件：** `docs/aiqe/v1.6/governance/production-evidence.json`
**扫描基线 SHA：** `2d2f508d5d1fd452972e7af49d9b4f3bde2e7b01`

## 1. 为什么要归一化

手工验收发现 `production-evidence.json` 的 §11 灰度阶段全部写成 `PASS`，而原始部署记录
`production-stage-canary-eb20.json` 只能证明：

- canary 容器 `eb20` 启动后、切流前 `/health=200`；
- 100% 切流后公网 `/health=200`、`/openapi.json=200`，canary 访问日志收到一条 `GET /health`；
- 5%/50% 渐进流量被用户授权跳过，直接 100% 切换；
- 记录了回滚命令、nginx 备份路径和旧后端容器名，但没有回滚演练结果。

按手册 §0.3「严禁状态折算」，健康检查通过、配置校验通过、100% 切流、回滚命令存在都
不能单独折算为 `PASS`。因此 Gate F 不能依据这份文件 PASS。

## 2. 修正前后对照

| 阶段 | 修正前 | 修正后 | 原始事实 | 依据 |
|---|---|---|---|---|
| `stage1_shadow` | PASS | **NOT_PROVEN** | 只有 canary `/health=200` | §11.4：Shadow 必须有影子流量/双跑差异，不可用 `/health=200` 代替 |
| `stage2_dogfood` | PASS | **NOT_PROVEN** | 只有公网 `/health=200`、`/openapi.json=200`、canary 日志一条 `/health` | §11.4：Canary 需按产品关键业务流程 Dogfood 并保存业务指标/错误率 |
| `stage3_small_traffic` | PASS | **NOT_RUN** | 5% 阶段被用户授权跳过，未执行 | §11.2/§11.4：未执行记 NOT_RUN；只有正式豁免字段才可 WAIVED |
| `stage4_expand` | PASS | **NOT_RUN** | 50% 阶段被折叠为一次 100% 切换，未执行 | 同上 |
| `stage5_ga` | PASS | **NOT_PROVEN** | 100% 切流 + 公网 health/openapi 200 | §11.4/§11.5：GA 依赖前序 mandatory 阶段，切流完成不等于 GA 验收 |
| `rollback_drill` | （缺失，未记录） | **NOT_RUN** | 只有回滚命令、nginx 备份、旧容器名 | §11.4：只有命令/配置不算演练；新增该阶段记录并附 blocked_by/owner/unblock_action |
| `independent_verification` | `reviewed_by=MoojinR`（视为已签） | `reviewed_by=MoojinR`，`review_id`/`reviewed_commit_sha` 留空，`status=PENDING` | 原始文件没有 review id / 签署 SHA | §11.5、FIX-014：不得编造 Reviewer 身份与提交 |

### 为什么没有写 WAIVED

原始文件只有一句话的用户授权（“100% 切换、无需观察窗口”）。手册 §11.3 要求 `WAIVED`
必须具备 `approved_by`、`approved_at`、`reason`、`risk`、`compensating_controls`、
`expires_at`，并且按发布策略默认不计入 Gate F PASS。当前没有正式的豁免字段与到期时间，
因此 stage3/stage4 记 `NOT_RUN`，不写 `WAIVED`，更不写 `PASS`。

## 3. 已补录的原始事实字段

每个 §11 阶段尽量补齐了 `target_release_sha`、`deployed_image_digest`、`environment`、
`checks`、`artifact_refs`：

- `target_release_sha = eb20b98095e10444bf5cb43f3c8a5de4c1d6cf69`（原始 `release_commit`）
- `deployed_image_digest = sha256:dfebc617d093ef97e87890c0063cedfd66c1e01b5dd1da2bec057b4c62d22a0f`（原始 `release_image_id`）
- `environment = production`（原始 `network=cameltv-tp-production_default`）

仍为空并已注明原因的字段：

| 字段 | 为空原因 |
|---|---|
| `region` | 原始文件只有 docker network/容器 IP，没有云区域/集群信息 |
| `operator_identity` | 原始文件只记录“回滚负责人=用户”“生产验收签字人=MoojinR”，没有执行操作者账号 |
| `stage1_shadow.started_at/finished_at` | 原始文件没有阶段起止时间，只有 `switch.switched_at` 与 `captured_at` |
| `rollback_drill.rollback_target_sha` | 原始文件只有旧容器名 `cameltv-tp-production-backend-v16`，没有镜像 digest/SHA |
| `independent_verification.review_id/reviewed_commit_sha` | 原始文件没有 Reviewer Review ID 与签署提交 |

## 4. Gate F 现状

`python scripts/aiqe/release_verdict.py` 计算 Gate F 为 `NOT_PROVEN`，原因包括：

- `stage1_shadow` / `stage2_dogfood` 状态 `NOT_PROVEN`，不是可接受的生产阶段状态；
- `stage3_small_traffic` / `stage4_expand` / `rollback_drill` 为 `NOT_RUN`；
- 独立验收缺少 `review_id` / `reviewed_commit_sha`。

`python scripts/aiqe/release_verdict.py --require-ga` 因此退出码 1。手册 §11.5 要求：
若产品负责人坚持 100% 直接切换，Release Verdict 必须显示“受控发布 + 明确豁免”，不能显示
“完整灰度流程全部通过”；是否允许 GA 由发布策略单独决定，默认不把豁免计入强制 Gate PASS。

## 5. 仍需 owner 完成的动作

| 动作 | owner | 解除条件 |
|---|---|---|
| 真实回滚演练 | 发布负责人（用户） | 在隔离环境或受控窗口实际回滚，记录起止时间、目标 SHA/digest、恢复耗时、恢复后 health 与业务断言，产出 artifact |
| 5%/50% 灰度或正式豁免 | 发布负责人（用户） | 要么记录真实流量比例、观察窗口、错误率/延迟/业务指标阈值与停止条件；要么按发布策略补 `approved_by/approved_at/reason/risk/compensating_controls/expires_at`，且 Gate F 仍不把 WAIVED 计入 PASS |
| Shadow / Dogfood 证据 | 发布负责人 + QA | 影子流量或等效双跑差异结果；产品关键业务流程 Dogfood 记录与业务指标 |
| 独立验收签署 | MoojinR | 在 GitHub 上对目标 SHA 提交 Review，回填真实 `review_id`、`reviewed_commit_sha`、`reviewed_at`（FIX-014） |
| 阶段操作者身份 | 发布负责人 | 原始发布记录补充执行账号/流水线 Run ID，或由发布平台导出 operator 字段 |

## 6. 未纳入本次归一化的项

`production-evidence.json` 中的 `postgres_backup_restore`、`vault_production_mode`、
`monitoring_alerts`、`container_egress`、`image_self_contained`、`production_smoke`
不属于手册 §11 的灰度阶段，本次未重新执行，保留原记录并标注为 readiness 项；最终发布
复核时仍需 owner 重新确认。
