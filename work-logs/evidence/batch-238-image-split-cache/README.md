# Batch 238 Phase 4 镜像基线

## 当前采集

`image-baseline.json` 由 `scripts/deploy/collect-image-baseline.ps1` 生成。本轮桌面环境 Docker daemon 未启动，因此当前采集明确记录 `docker_available=false`，没有伪造实时镜像大小。

静态基线已确认：

- API/runner 分离目标存在：`api`、`runner`、combined `runtime`
- Backend Dockerfile BuildKit cache mount：3
- Frontend Dockerfile BuildKit cache mount：1
- `docker-compose.execution.yml` 存在

## 最近一次真实测量基线

来源：`work-logs/batch-production-capacity-guard-qa-report.md`

- API image reported size：980 MB
- Runner image reported size：5.35 GB
- Shared storage：972.9 MB
- API unique storage：6.963 MB
- API peak memory：约 207.48 MiB
- Runner peak memory：约 1269.35 MiB

这些数值是此前真实容器测量结果，不是本批新造数据。Batch 238 的 cache mount 需要在下一次 Docker host 可用时重新采集并与上述基线对比。
