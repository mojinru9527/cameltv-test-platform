# Batch 235 — AI Local-First 基础（Phase 0 + Phase 1）— PM Plan
> **PM (🟨)** | Date: 2026-09-13

## 规格摘要
**原始需求**: 落地 AI 本地优先优化的 Phase 0 基线与 Phase 1 AI Gateway 精确缓存。  
**目标时间**: 本批完成，Phase 2–4 拆后续批次。

## 开发任务
### [ ] Task 1: Phase 0 基线与采集器
**描述**: 新增基线采集脚本，输出 Provider、Embedding、缓存开关、镜像运行时依赖和当前缓存统计。
**验收标准**:
- 脚本可独立运行并输出 JSON。
- 不读取或打印任何 API Key / Secret。
- 结果覆盖 Phase 2–4 需要的当前状态。
**涉及文件**:
- `test-platform-v2/backend/scripts/collect_ai_local_baseline.py`
- `work-logs/evidence/batch-235-ai-local-first/baseline.json`

### [ ] Task 2: 持久化精确缓存模型与迁移
**描述**: 新增 `ai_response_cache` 表和 Alembic 迁移。
**验收标准**:
- project_id、namespace、cache_key 唯一、provider/model/prompt/input、response、usage、TTL、hit_count 落库。
- migration 幂等、单头、可 downgrade。
- Base.metadata 可发现模型。
**涉及文件**:
- `test-platform-v2/backend/app/models/ai_gateway_cache.py`
- `test-platform-v2/backend/app/models/__init__.py`
- `test-platform-v2/backend/alembic/versions/20260916_b235_ai_gateway_cache.py`

### [ ] Task 3: AI Gateway 精确缓存读写
**描述**: 在共享 `ai_client` 中接入 opt-in 精确缓存；命中不调上游，写入不阻断主调用，截断响应不缓存。
**验收标准**:
- 两次相同请求只调用上游一次。
- 不同项目不命中。
- TTL 过期后 miss。
- cache_status 返回 miss/hit/write/bypass。
**涉及文件**:
- `test-platform-v2/backend/app/services/ai_gateway/cache.py`
- `test-platform-v2/backend/app/services/ai_gateway/keys.py`
- `test-platform-v2/backend/app/services/ai_client.py`
- `test-platform-v2/backend/app/core/config.py`

### [ ] Task 4: 缓存统计与清理 API
**描述**: 提供项目级缓存统计和 namespace 清理 API。
**验收标准**:
- `GET /api/v1/ai-config/cache-stats` 返回命中/条目/命名空间数据。
- `DELETE /api/v1/ai-config/cache` 按项目清理，支持 namespace。
- 权限沿用 `ai_config:view` / `ai_config:manage`。
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/ai_config.py`
- `test-platform-v2/backend/app/services/ai_gateway/stats.py`

### [ ] Task 5: 配置与部署接入
**描述**: 增加缓存开关、TTL，并在 compose 中显式传入环境变量，默认关闭。
**验收标准**:
- 未开启时行为与现状一致。
- `AI_EXACT_CACHE_ENABLED=true` 时才启用。
**涉及文件**:
- `test-platform-v2/backend/app/core/config.py`
- `test-platform-v2/deploy/docker-compose.yml`

### [ ] Task 6: 测试与证据
**描述**: 增加模型、缓存、API、迁移契约测试，执行相关回归并记录证据。
**验收标准**:
- 相关 pytest 全绿。
- 导入/F821/Alembic 单头通过。
- 证据写明命令、退出码、结果。
**涉及文件**:
- `test-platform-v2/backend/tests/test_ai_gateway_cache.py`
- `test-platform-v2/backend/tests/test_ai_client.py`
- `work-logs/batch-235-ai-local-first-pipeline-qa-report.md`

## 质量要求
- [ ] 无调试遗留  - [ ] 无硬编码密钥  - [ ] OpenAPI 同步（若生成契约受影响）
- [ ] 迁移安全  - [ ] 缓存失败不阻断主链  - [ ] 项目隔离
