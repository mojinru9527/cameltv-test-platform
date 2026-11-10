# Batch 285（M1 遗留 / TA-007）— MinIO 自托管 Artifact 存储：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-285-artifact-minio · **基线**：origin/main `79cbbbc11`

## 1. 背景

M1 的 Artifact 只支持本地 FS；用户决定生产采用 **MinIO 自托管**（数据不出站、成本可控）。
要求不引入带哈希锁的新依赖（避免 lock 重生成风险）。

## 2. 目标

1. `MinioArtifactStorage`：S3 兼容 PUT/GET，`s3://<bucket>/<key>`，key 与 FS 同构（内容寻址）；
2. 自实现 AWS SigV4（httpx，无 boto3/minio SDK）；
3. 配置开关 `ARTIFACT_STORAGE_BACKEND=fs|minio` + `MINIO_*`；
4. `artifact_service` 按 URI 前缀读取（`s3://` → MinIO，`file://` → FS），兼容存量数据；
5. compose 增加 minio 服务 + `minio-data` volume + backend env。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | PUT/GET roundtrip + URI/签名 | `test_put_and_read_roundtrip` |
| A2 | 404 → ArtifactStorageError | `test_read_missing_raises` |
| A3 | ensure_bucket 200/409 | `test_ensure_bucket_accepts_409` |
| A4 | fs/minio 工厂切换 | `test_factory_selects_backend` |
| A5 | service 走 MinIO 写入/读取 | `test_artifact_service_uses_minio` |
| A6 | compose/minio 服务 | 静态检查 |
| A7 | 全量回归 + ratchet | CI |

## 4. 非目标

- MinIO 生产容器部署（随后窗口执行）；
- 生命周期/配额（留存策略单独批次）；
- 多副本/分布式 MinIO（单机 MVP）。
