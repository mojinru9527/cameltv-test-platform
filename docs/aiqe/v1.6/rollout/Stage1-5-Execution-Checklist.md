# Stage 1–5 执行清单（发布窗口用）

> 本清单用于真实发布执行；每阶段完成后把证据写入
> `docs/aiqe/v1.6/governance/production-evidence.json` 对应 stage，并置 `status=PASS`。
> 没有 artifact 的阶段不得标记 PASS。

## 通用前置（每个阶段都检查）

- [ ] main 最新 commit 已知，CI required checks 全绿
- [ ] 生产镜像 digest 与 release commit 对应
- [ ] `aiqe_ro` 只读 role 已硬化（见 `scripts/aiqe/sql/harden_pg_readonly_role.sql`）
- [ ] 回滚命令/值班人已确认
- [ ] 监控看板：错误率、P95、AIQE job 失败率、DB 连接数

## Stage 1 Shadow（2026-11-28 10:00–12:00）

```bash
# 只旁路，不对外生效
# 1) 记录生产 commit/镜像
git rev-parse HEAD
docker inspect aiqe-v16-backend --format '{{.Image}}'

# 2) 跑 shadow 对比任务，保存 Run/Job/Assertion artifact
# 3) 对比 shadow 与线上结果，记录差异
```

证据字段：`stage1_shadow.artifact`、`run_ids`、`diff_summary`、`operator`。

## Stage 2 Dogfood（2026-11-29 14:00–18:00）

- [ ] 内部账号执行核心链路（登录/查询/写入自建数据/清理）
- [ ] 缺陷记录链接
- [ ] 无 P0/P1 缺陷

证据字段：`stage2_dogfood.run_ids`、`defects`、`operator`。

## Stage 3 小流量 5%（2026-12-01 10:00–12:00）

- [ ] 流量比例 5%，观察 2 小时
- [ ] 错误率不高于基线 +0.5%
- [ ] 回滚演练一次并记录耗时

证据字段：`stage3_small_traffic.traffic_ratio`、`error_rate`、`rollback_drill`。

## Stage 4 扩量 50%（2026-12-03 10:00–16:00）

- [ ] 流量 50%，观察 6 小时
- [ ] P95、错误率、DB 连接数在阈值内
- [ ] 告警无未处理项

证据字段：`stage4_expand.traffic_ratio`、`metrics`、`alerts`。

## Stage 5 GA（2026-12-05 10:00）

- [ ] 100% 流量
- [ ] 发布公告
- [ ] 独立验收签署（Gate G）
- [ ] 生产 smoke PASS

证据字段：`stage5_ga.release_commit`、`image_digest`、`announcement`、`smoke`。
