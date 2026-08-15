# Batch 184 — Design Spec：DSH 沙箱安全加固

> 配套 PRD/PM：`batch-184-dsh-sandbox-hardening-{prd-summary,pm-plan}.md`

## 1. C172-2 凭据并发隔离（`dsh_runner._run_python_sdk`）

**问题**：SDK 从进程 `os.environ` 读凭据（无显式传参口），当前实现裸改 env → 多线程互踩。

**方案**：模块级 `_python_sdk_env_lock = threading.Lock()`，将「env 突变（写入 + 完成后恢复）」与 `DeepSeekHarness(...).run(...)` 整体纳入 `with _python_sdk_env_lock:`。

- 语义：python-sdk 任务在该进程内串行执行（凭据一致性强保证）；node 子进程路径天然隔离，不受锁影响。
- 恢复保证：`finally` 恢复 `previous_env`（已有），锁内保证恢复不与其他线程交错。

## 2. C172-1 沙箱加固（`dsh_runner` 全局）

### 2.1 任务级隔离工作区

`_workspace_for(workdir, session_root)` 改为**永远返回 `{base}/ws-{uuid}` 独立子目录**：

```
base = workdir（调用方显式）或 DSH_WORKSPACE 或 session_root/workspaces
isolated = base / ws-{uuid}   ← 每任务唯一，mkdir parents
```

- 调用方显式 workspace 也仅作隔离根（其下再建子层）——杜绝任务间文件互见/覆盖。
- 向后兼容：目录层级变化，根路径不变。

### 2.2 全局并发闸门

模块级 `_concurrency_gate = threading.BoundedSemaphore(max(1, DSH_MAX_CONCURRENT))`（默认 1），
`run_dsh_task` 在 `runtime_available` 与目录创建之后、执行之前 `with _concurrency_gate:` 包裹两个运行时分支。

- 语义：超出上限的任务**排队**（不拒绝、不丢任务）。
- 测试中重建闸门需显式 `runner_mod._concurrency_gate = BoundedSemaphore(n)`（模块 import 时按默认配置创建）。

### 2.3 任务文本配额

`run_dsh_task` 入口：`len(task) > DSH_MAX_TASK_CHARS`（默认 20000）→ 直接返回
`DshRunResult(exit_code=2, error="任务文本超长（N > M 字符上限…）")`。

### 2.4 配置项（`app/core/config.py` + `.env.example`）

| 配置 | 默认 | 说明 |
|------|------|------|
| `dsh_max_concurrent` | 1 | 全局并发上限（安全优先） |
| `dsh_max_task_chars` | 20000 | 单任务文本上限 |

## 3. 安全回归测试（`tests/test_dsh_sandbox.py`，8 例）

| 测试 | 断言 |
|------|------|
| test_shared_root_yields_per_task_subdirs | 共享根下两次任务目录互异、父目录=根、ws- 前缀、已创建 |
| test_explicit_workdir_used_as_root | 显式 workspace 作为隔离根 |
| test_default_root_is_session_workspaces | 无配置时根=session_root/workspaces |
| test_oversized_task_rejected | 超长任务 exit_code=2 + 「超长」 |
| test_normal_task_passes_length_check | 长度合法进入执行路径（不可用时 exit 1 非长度错误） |
| test_gate_caps_concurrent_executions | 4 任务线程并发、max_active==2（闸门生效） |
| test_concurrent_runs_see_own_credentials | 双任务各自捕获 key-a/model-a 与 key-b/model-b；结束后 env 不残留 |
| test_node_timeout_returns_timed_out | 超时语义回归（透传不吞异常） |

## 4. 文档

- `backend/CLAUDE.md`「DSH 沙箱约定」：隔离工作区/并发闸门/凭据锁/生产启用前置。
- `.env.example` 新增 DSH_MAX_CONCURRENT / DSH_MAX_TASK_CHARS 注释。
- 生产启用 checklist：加固合入 → test_dsh_sandbox 全绿 → 部署人工确认 → DSH_ENABLED=true。
