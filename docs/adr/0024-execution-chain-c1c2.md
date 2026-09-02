# ADR-0024 — 执行链专门批次（C1/C2/C6b，Batch 209）

> Status: Accepted (2026-09-02) | Owner: qa-team | Tags: command-ir, execution, binding, gate

## 决策
- **C1 driver 分派**：Temporal `execute_commands` 按 `cmd.driver` 路由：
  `api`→HTTP（原逻辑不变）；`assertion`→跳过（oracle 阶段负责）；`browser`→注册的
  `browser_runner` 回调执行，无回调则持久化 BLOCKED(no_browser_runtime) 步骤——彻底杜绝
  browser 命令被静默当 HTTP 误请求。
- **C2 binding 自动物化**：`scenario.repository.materialize_bindings_for_plan`：plan 审批/激活时，
  把 plan 命令 observations 与 APPROVED oracle 按 oracle_key/命令 id 匹配，推导 binding_type
  （HTTP_STATUS→API_STATUS、HTTP_RESPONSE→API_JSONPATH、UI_*→同名、DB/EVENT/LOG→映射），
  幂等 upsert ACTIVE binding；未匹配保持未绑定并由 run fail-fast 兜底。
- **C6b 项目级门控**：agent 触发/类型列表在有 DB+project 时用 `ai_client.is_configured(db, project_id)`
  判定；无 DB 上下文回退 env（settings.ai_enabled 为全局 kill-switch）。

## 移交（后续）
- C1b：把真实 Playwright BrowserDriver 以 `register_browser_runner` 注入常驻 Temporal worker
  （需真实 UI 环境/凭据，单独批次）。
- 自动物化覆盖 DB 观测生成（执行器产出 DB step 后自动补 DB_COLUMN binding）可后续增强。

## 关联
- 工件: work-logs/batch-209-execution-chain-c1c2-*
