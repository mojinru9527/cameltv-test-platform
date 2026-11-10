# Batch 285 — Dev Summary

| 文件 | 说明 |
|------|------|
| `aiqe/services/artifact_storage_minio.py` | MinIO 后端 + SigV4（httpx） |
| `aiqe/services/artifact_storage.py` | `get_storage_backend()` 工厂 |
| `aiqe/services/artifact_service.py` | 默认后端切换 + 按 URI 前缀读 |
| `app/core/config.py` | `ARTIFACT_STORAGE_BACKEND` / `MINIO_*` |
| `deploy/docker-compose.yml` | minio 服务 + `minio-data` volume + backend env |
| `tests/test_aiqe_artifact_minio.py` | 5 条 mock 测试 |

验证：`pytest -q` → 1434 passed / 43 skipped；ratchet PASS。

## 部署（待窗口）

```bash
# 1) 生产加载 minio 镜像（本地 pull → save → scp → load）
docker run -d --name cameltv-minio --restart unless-stopped \
  --network cameltv-tp-production_default \
  -v /opt/cameltv-tp/minio-data:/data \
  -e MINIO_ROOT_USER=... -e MINIO_ROOT_PASSWORD=... \
  minio/minio:latest server /data --console-address ":9001"

# 2) production.env 增加 MINIO_* 与 ARTIFACT_STORAGE_BACKEND=minio
# 3) server compose backend 环境补 MINIO_*，重启 backend
# 4) 容器内 ensure_bucket + put/read 冒烟
```
