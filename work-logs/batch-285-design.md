# Batch 285 — Design

## 存储后端

```text
artifact_service.put_artifact()
  → get_storage_backend()   # fs | minio
  → MinioArtifactStorage.put(content, sha256)
      key = <sha[:2]>/<sha[2:4]>/<sha>
      PUT {endpoint}/{bucket}/{key}   (SigV4)
      → s3://<bucket>/<key>
```

读取按 URI 前缀路由，兼容 M1 已产生的 `file://` 数据。

## SigV4（无 SDK）

- canonical request：method / canonical URI / canonical query / host+`x-amz-content-sha256`+`x-amz-date`；
- scope：`<date>/us-east-1/s3/aws4_request`；
- 签名密钥链：`AWS4+secret → date → region → s3 → aws4_request`；
- 请求头带 `Authorization`、`x-amz-date`、`x-amz-content-sha256`。

## 配置

| 变量 | 默认 | 说明 |
|------|------|------|
| ARTIFACT_STORAGE_BACKEND | fs | fs / minio |
| MINIO_ENDPOINT | 空 | 如 `http://minio:9000` |
| MINIO_ACCESS_KEY / SECRET_KEY | 空 | MinIO root 凭据（生产放 production.env，600） |
| MINIO_BUCKET | cameltv-artifacts | 首次使用前 ensure_bucket |
| MINIO_REGION | us-east-1 | SigV4 region |

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-285-1 | 自实现 SigV4，不加 SDK | 避免 requirements lock 重生成 + 镜像膨胀 |
| D-285-2 | URI 前缀路由 | 存量 file:// 不迁移，零停机 |
| D-285-3 | `ensure_bucket` 显式调用 | 不在每次 PUT 前探测，失败信息更清晰 |
| D-285-4 | 单机 MinIO + 本地 volume | MVP；后续可换分布式/对象存储 |
