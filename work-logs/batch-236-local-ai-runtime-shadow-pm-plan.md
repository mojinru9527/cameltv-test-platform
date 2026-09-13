# Batch 236 — 本地 AI Runtime 与 Shadow Mode（Phase 2）— PM Plan
> **PM (🟨)** | Date: 2026-09-13

## 规格摘要
**原始需求**: 实现 C235-1 的独立本地推理运行时与 Shadow Mode。  
**目标时间**: 本批完成，Phase 3 再切换主链路。

## 开发任务
### [ ] Task 1: Runtime 配置与状态
**描述**: 增加本地 OpenAI-compatible runtime 配置、脱敏状态与 health check。
**验收标准**: 不泄露 Key；默认 disabled；可在无本地服务时报告 unavailable。
**涉及文件**: `app/core/config.py`、`app/services/ai_gateway/runtime.py`、`app/api/v1/ai_config.py`

### [ ] Task 2: Shadow 数据模型与迁移
**描述**: 新增 `ai_shadow_run` 表和 Alembic 迁移。
**验收标准**: 记录 primary/shadow 模型、输入 hash、JSON 合法、延迟、usage、输出 hash、错误。
**涉及文件**: `app/models/ai_shadow_run.py`、`app/models/__init__.py`、`alembic/versions/*`

### [ ] Task 3: 后台 Shadow 执行与对比
**描述**: 复用共享 transport 调用本地 runtime，后台执行且不影响主链。
**验收标准**: 本地失败只写 failed 记录；主响应和缓存行为不变；线程使用独立 Session。
**涉及文件**: `app/services/ai_gateway/shadow.py`、`app/services/ai_client.py`

### [ ] Task 4: Shadow API
**描述**: 提供 runtime status、health check、shadow runs 查询接口。
**验收标准**: 权限沿用 `ai_config:view/manage`；项目隔离；不返回敏感内容。
**涉及文件**: `app/api/v1/ai_config.py`

### [ ] Task 5: 配置与部署
**描述**: 增加 Shadow/本地 runtime 环境变量并写入 compose/env 示例。
**验收标准**: 全部默认安全关闭。
**涉及文件**: `deploy/docker-compose.yml`、`.env.example`、`config/runtime/*.env.example`

### [ ] Task 6: 测试与证据
**描述**: 覆盖默认关闭、采样、成功对比、失败降级、API 契约。
**验收标准**: 相关 pytest、F821、Alembic、前端 typecheck/build 全绿。
**涉及文件**: `tests/test_ai_shadow_runtime.py`、`work-logs/evidence/batch-236-local-ai-runtime-shadow/`

## 质量要求
- [ ] 无调试遗留  - [ ] 无 Key 落地/泄露  - [ ] 后台线程异常隔离
- [ ] 迁移幂等单头  - [ ] 主链路 shadow 默认关闭
