# Batch 281（M1 / TA-007）— Artifact Manager：PRD

> **部门**：🟦 Product · **日期**：2026-11-10 · **批次模式**：完整
> **分支**：feature/batch-281-m1-artifact · **基线**：origin/main `cf5dcfb5e`

## 1. 问题

Run 的事件流有了，但截图 / trace / HAR / 日志等执行证据没有统一落点：现有
`ui_test_run`/runner 各自存目录，无法按 Run 聚合、无法校验完整性、无法控制跨项目访问。

## 2. 目标

1. `run_artifacts` 表（13 号 §4.12）+ 本地 FS 存储后端（`ArtifactStorageBackend` 抽象）；
2. `put_artifact()`：sha256 计算、同 hash 文件去重、大小上限、类型/跨源引用校验；
3. 读写按 `run.project_id` 鉴权，跨项目 403；
4. `redaction_status` pending → sanitized / rejected 单向；
5. 迁移 up/down/up 可重跑。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 上传/下载 roundtrip，sha256/大小/mime 正确 | `test_put_and_read_roundtrip` |
| A2 | 同内容只落一份文件（多行共享 URI） | `test_same_content_dedupes_file` |
| A3 | 跨项目读写/列表/脱敏全部 403 | `test_cross_project_access_denied` |
| A4 | 非法类型/不成对引用/未知 run 拒绝 | `test_invalid_inputs` |
| A5 | 脱敏单向迁移 | `test_redaction_transitions` |
| A6 | 路径穿越拒绝 | `test_read_rejects_path_escape` |
| A7 | 迁移 + 全量回归 | QA 记录 |

## 4. 非目标

- COS/MinIO 生产后端（TA-007 PoC 后定，接口已抽象）；
- 留存清理策略（TA-007 后续/运维批次）；
- HTTP 上传/下载端点（batch-282 Console 一起接）。
