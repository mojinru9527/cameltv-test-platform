# Batch 281（M1 / TA-007）— Design

> **部门**：🟪 Design · **日期**：2026-11-10

## 1. 表 `run_artifacts`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID string(36) | PK |
| run_id | FK test_runs CASCADE | 必填 |
| node_run_id / step_attempt_id | FK SET NULL | 可选 |
| artifact_type | varchar(24) | 12 类，服务层白名单 |
| storage_uri | text | `file://<root>/<sha[:2]>/<sha[2:4]>/<sha>`，不存二进制 |
| sha256 / size_bytes / mime_type | — | 完整性 |
| redaction_status | varchar(16) | pending / sanitized / rejected |
| metadata_json | JSON | 浏览器/viewport 等 |
| linked_evidence_type / id | varchar | `lanhu_evidence / defect / external_url` 成对 |
| created_at | timestamptz | 索引 `(run_id, created_at)` |

索引：`(run_id, created_at)`、`sha256`、`redaction_status`、`node_run_id`。

## 2. 存储抽象

```python
class ArtifactStorageBackend(Protocol):
    def put(self, content: bytes, sha256_hex: str) -> str: ...
    def read(self, uri: str) -> bytes: ...
```

`LocalArtifactStorage(root)`：
- `put` 先写 `.tmp` 再 `replace`（原子），已存在则复用；
- `read` 只接受 `file://` 且解析后必须在 root 内（防穿越）。

生产 COS/MinIO 后端只需实现同一 Protocol（TA-007 PoC 后接）。

## 3. 服务

- `put_artifact(project_id, run_id, content, artifact_type, …)`：
  校验 run 归属 → 类型/引用/大小 → sha256 → backend.put → 插行；
- `get/list/read/mark_redaction` 全部先按 `run.project_id` 鉴权；
- 跨项目抛 `ArtifactAccessDenied`（上层映射 403）；
- 同 hash 多行共享同一 `storage_uri`，文件只落一份。

## 4. 设计决策

| ID | 决策 | 理由 |
|----|------|------|
| D-281-1 | 文件名 = sha256 分片目录 | 内容寻址、天然去重、便于 GC |
| D-281-2 | `settings.storage_dir` 用 `getattr` 回退 `storage/` | 配置类未声明该字段（既有代码同样用 getattr） |
| D-281-3 | 脱敏只允许 pending → sanitized/rejected | 防止状态回退/二次改写 |
| D-281-4 | 生产后端不做进本批 | 接口已抽象，等 TA-007 PoC 选型 |
| D-281-5 | HTTP 端点推迟到 batch-282 | Console 与上传/下载一起联调 |
