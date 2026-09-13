# Batch 235 — AI Local-First 基础（Phase 0 + Phase 1）— Design Spec
> **Design (🎨)** | Date: 2026-09-13 | Status: Ready

## 0. 技术体系确认

本批无前端视觉变更。设计对象是后端缓存契约、配置语义和运维可观测性。

## 1. 组件规格表

| 组件 | 规格 | 默认值 | 失败行为 |
|------|------|--------|----------|
| Exact Cache | `ai_response_cache` 持久表 | 禁用 | 读写异常不阻断 AI |
| Cache Key | SHA-256 规范化键 | 按请求生成 | 键不完整则 bypass |
| TTL | 秒级过期 | 86400 | 过期即 miss |
| Stats | 项目级聚合 | 空结果零值 | 查询失败返回可读错误 |
| Cleanup | 按 project + namespace | project 必填 | 删除结果计数 |

## 2. API 契约

### GET `/api/v1/ai-config/cache-stats`
返回：

```json
{
  "enabled": false,
  "project_id": 1,
  "entries": 0,
  "active_entries": 0,
  "expired_entries": 0,
  "hit_count": 0,
  "namespaces": []
}
```

### DELETE `/api/v1/ai-config/cache?namespace=aitde-cache-v1`
返回：

```json
{"deleted": 12, "namespace": "aitde-cache-v1"}
```

## 3. 缓存键与失效

```text
sha256(
  project_id | provider_id | model |
  cache_namespace | system_prompt_hash | user_message_hash |
  json_mode | max_tokens | temperature
)
```

失效条件：

- 手动清理 namespace
- TTL 到期
- Prompt/Schema 版本升级时调用方切换 namespace
- Provider 或模型变化自动产生不同键

## 4. 状态设计核对

| 状态 | 行为 |
|------|------|
| disabled | `cache_status=disabled`，调用上游 |
| miss | 调用上游，成功后写入 |
| hit | 不调用上游，更新 hit_count |
| bypass | 截断响应、无 DB、键不完整 |
| error | 记录日志，按 miss 继续主调用 |

## 5. 设计签核

结论：通过。无 UI；Admin 视角只通过统计/清理 API 观测。

## 6. 设计 QA 走查发现

无前端变更，本批不做 UI 走查。
