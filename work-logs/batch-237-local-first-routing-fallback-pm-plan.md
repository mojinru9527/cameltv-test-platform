# Batch 237 — 本地优先路由与云端兜底（Phase 3）— PM Plan
> **PM (🟨)** | Date: 2026-09-13

## 开发任务
### [ ] Task 1: RoutePlan 与模式解析
**描述**: 实现 `cloud_only / shadow / local_preferred / local_only` 纯路由计划。
**验收标准**: 模式非法回退 cloud_only；local-only 无本地配置失败；local-preferred 有云端 fallback。
**涉及文件**: `app/services/ai_gateway/router.py`、`app/core/config.py`

### [ ] Task 2: 主链接入路由
**描述**: sync/async `ai_client` 都从 RoutePlan 取主配置与 fallback。
**验收标准**: 本地失败自动云端；`route_status` 与 `route_origin` 可观测；async 行为一致。
**涉及文件**: `app/services/ai_client.py`

### [ ] Task 3: Shadow 对端策略化
**描述**: Shadow 使用 RoutePlan 指定的 `shadow_config`，不再固定本地。
**验收标准**: shadow 模式对比 cloud→local；local-preferred 对比 local→cloud；cloud_only 不 shadow。
**涉及文件**: `app/services/ai_gateway/shadow.py`

### [ ] Task 4: Runtime 状态扩展
**描述**: 状态 API 返回 runtime_mode 与 fallback_to_cloud。
**验收标准**: 不泄漏 Key；dev-gate/typecheck 通过。
**涉及文件**: `app/services/ai_gateway/runtime.py`

### [ ] Task 5: 配置与测试
**描述**: 接入 env/compose，覆盖纯路由、sync/async fallback、shadow 策略。
**验收标准**: 相关 pytest 全绿；默认 cloud_only。
**涉及文件**: `tests/test_ai_runtime_routing.py`、`deploy/docker-compose.yml`、`.env.example`

## 质量要求
- [ ] 默认行为不变  - [ ] local-only 不暗回云  - [ ] fallback 有来源标签
- [ ] sync/async 双路径测试  - [ ] 无 Key 泄漏
