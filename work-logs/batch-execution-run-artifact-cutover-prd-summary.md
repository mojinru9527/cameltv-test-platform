# Batch PRD — Artifact cutover (PR-05)

mode: light
豁免理由：现有 EvidenceService 已实现 sanitize → object storage → metadata/hash；本批次只做验收守卫和迁移收口，不引入新行为。

## 验收
- EvidenceArtifact 表不得出现 raw bytes/blob 列。
- store_artifact 必须写 storage_uri/content_hash/content_type/size_bytes。
- 运行证据、数据证据继续通过 EvidenceService。
