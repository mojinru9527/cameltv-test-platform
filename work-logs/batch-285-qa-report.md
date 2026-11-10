# Batch 285 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | PUT/GET roundtrip + SigV4 | ✅ | `test_put_and_read_roundtrip` |
| A2 | 404 错误 | ✅ | `test_read_missing_raises` |
| A3 | ensure_bucket 409 | ✅ | `test_ensure_bucket_accepts_409` |
| A4 | 工厂选择 | ✅ | `test_factory_selects_backend` |
| A5 | service 走 MinIO | ✅ | `test_artifact_service_uses_minio` |
| A6 | compose minio 服务 | ✅ | 静态检查（image/volume/env） |
| A7 | 全量 + ratchet | ✅ | 1434 passed / 43 skipped；PASS |

## 缺口

- 真实 MinIO 端到端（需容器）→ 生产部署后跑 put/read 冒烟；
- 存量 `file://` 数据未迁移（按设计保留读取兼容）。

## 判定

代码侧通过；生产 MinIO 部署与冒烟待执行。
