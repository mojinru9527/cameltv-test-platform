# Batch 237 — 本地优先路由与云端兜底（Phase 3）— Design Spec
> **Design (🎨)** | Date: 2026-09-13 | Status: Ready

## 0. 技术体系确认

本批无 UI 变更；设计对象为路由状态机和安全回退契约。

## 1. 路由状态机

| 模式 | 主调用 | Shadow | Fallback |
|------|--------|--------|----------|
| cloud_only | cloud | 无 | 无 |
| shadow | cloud | local | 无 |
| local_preferred | local | cloud（可选） | cloud（可选） |
| local_only | local | 无 | 禁止 |

## 2. 配置语义

- `AI_RUNTIME_MODE=cloud_only`：Batch 237 默认，行为与现状一致。
- `AI_LOCAL_FALLBACK_TO_CLOUD=true`：仅 local_preferred 生效。
- `AI_SHADOW_ENABLED`：shadow/local_preferred 下决定是否记录对比。

## 3. 主链响应元数据

追加但不替代原字段：

```json
{
  "route_status": "primary|fallback",
  "route_origin": "cloud|local",
  "route_fallback_from": "local"
}
```

## 4. 安全约束

- 默认不切换主链。
- local-only 无本地配置时抛错，不暗中回云。
- fallback 不写入本地 provider 的 exact cache；避免标签错配。
- Shadow 失败仍不影响主响应。
