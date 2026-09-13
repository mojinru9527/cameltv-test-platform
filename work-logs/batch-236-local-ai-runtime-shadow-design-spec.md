# Batch 236 — 本地 AI Runtime 与 Shadow Mode（Phase 2）— Design Spec
> **Design (🎨)** | Date: 2026-09-13 | Status: Ready

## 0. 技术体系确认

本批无 UI 变更。后端新增 runtime 配置、后台 shadow 执行与对比 API。

## 1. Runtime 配置

| 环境变量 | 默认 | 说明 |
|----------|------|------|
| `AI_LOCAL_RUNTIME_ENABLED` | false | 本地 runtime 总开关 |
| `AI_LOCAL_BASE_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible endpoint |
| `AI_LOCAL_API_KEY` | 空 | 本地服务可选 Key |
| `AI_LOCAL_MODEL` | 空 | 本地模型名 |
| `AI_SHADOW_ENABLED` | false | Shadow 总开关 |
| `AI_SHADOW_SAMPLE_RATE` | 0.0 | 0–1 采样率 |
| `AI_SHADOW_TIMEOUT_SECONDS` | 60 | 本地 shadow 超时 |
| `AI_SHADOW_MAX_OUTPUT_CHARS` | 200000 | 结果截断上限 |

## 2. API 契约

- `GET /api/v1/ai-config/runtime`：返回 enabled/base_url/model/available，不返回 Key。
- `POST /api/v1/ai-config/runtime/health-check`：探测本地 `/models`。
- `GET /api/v1/ai-config/shadow-runs?limit=50`：项目内最近 shadow 对比。

## 3. 四态设计

| 状态 | 行为 |
|------|------|
| disabled | 不提交本地任务 |
| queued/running | 后台线程执行，主链不等待 |
| succeeded | 记录 JSON 合法性、输出 hash、延迟、usage |
| failed | 只记录错误摘要；主链仍返回 primary 结果 |

## 4. 安全约束

- 不把 API Key 返回前端。
- 不保存完整 prompt；只保存 hash。
- 不保存完整本地输出；只保存 hash、长度、JSON 合法性、错误摘要。
- 不在请求线程内调用本地 runtime。
