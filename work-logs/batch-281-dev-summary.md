# Batch 281（M1 / TA-007）— Dev Summary

> **部门**：🟦 Dev · **日期**：2026-11-10

## 变更文件

| 文件 | 说明 |
|------|------|
| `app/aiqe/models/artifact.py` | RunArtifact |
| `app/aiqe/services/artifact_storage.py` | Protocol + LocalArtifactStorage（去重/防穿越） |
| `app/aiqe/services/artifact_service.py` | put/get/list/read/mark_redaction |
| `app/aiqe/models/__init__.py` | 导出 RunArtifact |
| `app/models/__init__.py` | 注册 artifact 模型 |
| `alembic/versions/20261113_ta007_run_artifacts.py` | 建表 + 索引（skip-if-provisioned） |
| `tests/test_aiqe_artifact_service.py` | 6 条单测 |

## 行为

- 同内容两次上传：两行 DB、同一 `storage_uri`、磁盘仅 1 个文件；
- `read_artifact` 对 `file:///etc/passwd` 这类越界 URI 抛 `ArtifactStorageError`；
- 跨项目 `get/list/read/mark_redaction` 全部 `ArtifactAccessDenied`；
- 脱敏 `sanitized → rejected` 被拒绝。

## 本地验证

```text
pytest tests/test_aiqe_artifact_service.py  → 6 passed
pytest -q                                   → 1392 passed / 43 skipped
alembic upgrade/downgrade/upgrade           → 0/0/0
quality_ratchet.py                          → PASS
```
