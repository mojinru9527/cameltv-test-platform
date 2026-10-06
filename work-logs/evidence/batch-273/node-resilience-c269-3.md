---
title: "证据 — C269-3 执行节点韧性修复（Batch 273）"
owner: "qa-team"
last_reviewed: "2026-10-06"
status: "active"
expires: "2027-04-06"
tags: ["c269-3", "node", "resilience", "evidence", "batch-273"]
related: ["C-CONDITIONS.md", "work-logs/batch-273-p0-p3-remediation-report.md", "scripts/node/README.md"]
---

# C269-3 执行节点韧性修复 — 取证

> 分支 `fix/p0-p3-security-and-resilience-remediation`｜worktree `F:\CamelTv-worktrees\ds\DeepSeek_Harness-p0-p3-security-and-resilience-remediation`
> 改动面：`scripts/node/cameltv_node/cli.py`（+411/−89）、`scripts/node/README.md`、新增 `test-platform-v2/backend/tests/test_batch273_node_resilience.py`（25 例）

## 1. 根因（改动前，带行号）

| 位置 | 问题 |
|------|------|
| `cli.py:94-100`（旧） | `if resp.status_code >= 400 or payload.get("code") not in (None, 0): … raise SystemExit(2)` —— 平台 500/403 直接抛 `SystemExit`，而 `SystemExit` **不打印 traceback** |
| `cli.py:354-359`（旧） | 轮询循环 `_loop` **只捕获 `TransportDown`** → `SystemExit` 逃出循环，进程消失、已认领任务滞留 `pending` |
| `cli.py:88-89`（旧） | 只归一化 `httpx.TransportError`；stderr **从未落盘** |

> 同文件的 `_heartbeat_once` 反而写了 `except SystemExit: return False` —— 这佐证追踪器里「属遗漏」的判断。

## 2. 修复要点（改动后，带行号）

| 位置 | 内容 |
|------|------|
| `47-59` | 退出码 `EXIT_PLATFORM_ERROR=4`、`DEFAULT_MAX_CONSECUTIVE_FAILURES=10`、退避基数 5s / 上限 60s、默认日志 `~/.cameltv-node/logs/cameltv-node.log`（5MB × 5 轮转） |
| `61-137` | **文件日志**（stdlib logging + `RotatingFileHandler`，同时输出 stderr 与文件；不可写时安全降级为仅 stderr）+ `sys.excepthook`（未捕获异常也落盘） |
| `144-170` | `PlatformError`（携带 `status_code`/`code`，`.auth_problem` 识别 401/403）、`JobGone`、`RECOVERABLE_ERRORS=(TransportDown, PlatformError)` |
| `225-233` | `call()` 改为抛 `PlatformError` —— **根因修复点** |
| `237-248` | `_job_call()`：任务级端点返回 404 → `JobGone`（= 平台已把任务放回 pending），其他错误仍属可恢复 |
| `339-405` | `_fetch_payload`/`_heartbeat_once`/证据上传统一走 `_job_call`；不再需要 `SystemExit` 特判 |
| `444-500` | `_handle_job` 拆为 `_run_job`（取 payload → 执行 → 落 `results.json`）与 `_report_job`（传证据 → 上报）→ **重试不会重跑用例** |
| `503-565` | `_sleep`（测试接缝）、`_failure_budget`、`_backoff_seconds`（指数 + 等抖动 + 上限）、`_describe`（401/403 给出「检查 node token / X-Project-Id / execution:view」提示）、`_give_up`（退出 4 + 原因 + 明示「任务仍在租约内，平台会在租约过期后回收」）、`_retry_or_give_up` |
| `568-627` | `_process_job`：已认领任务**原地重试**（心跳维持租约）；仅平台 404（已被回收/改派）才放手，且**大声记日志**（任务此时已在 pending，不会被丢弃） |
| `630-672` | `_loop`：可恢复错误 → 记日志 + 指数退避 + 继续；连续失败计数在成功认领后归零；达上限退出 4 并给出可读原因。`--once` 语义保留（一轮，不退避空转） |
| `748-772` | 新增 `--log-file`、`--max-consecutive-failures`（env `CAMELTV_NODE_MAX_FAILURES`，0=不限）、`--backoff-base-seconds`、`--max-backoff-seconds`；README 补齐 |

**接口面核查（未杜撰端点）**：节点侧端点只有 `POST /execution-jobs/claim`、`GET /{id}/payload`、`POST /{id}/heartbeat`、`POST /{id}/evidence`、`POST /{id}/report`。**不存在节点侧 release/cancel 端点**（`/reclaim-stale` 需要 `execution:manage` 用户权限），因此「原地重试 + 维持租约 + 由租约过期回收」是唯一正确机制。

## 3. 验证

### 3.1 单元/回归测试

```
cd test-platform-v2/backend
python -m pytest tests/test_batch273_node_resilience.py \
  tests/test_batch258_node_cli.py \
  tests/test_batch266_executor_payload_and_isolation.py -q
→ 62 passed（25 新增 + 37 既有；改动前基线同为 37 passed，未回归）
```

覆盖：`call()` 对 500/403/业务码≠0 → `PlatformError`（非 `SystemExit`）；`ConnectError`/`ReadTimeout` → `TransportDown`；循环能扛过 500（继续轮询）、403+code≠0（带凭据提示）、连接重置/超时；连续 10 次失败 → 退出 4 且 stderr **与日志文件**都有原因；已认领任务原地重试（调用序列 `claim,payload,payload,payload,report`，**不重新 claim**）；上报失败仅重发上报、不重跑用例；平台 404 → 放手并继续轮询；`--once` 三种返回；日志文件带时间戳且跨重启追加；日志路径不可写 → 降级 stderr；退避上下界/抖动/预算/env。

### 3.2 真实 500 服务端实机探针（关键证据）

用一个**总是返回 500 的真实本地 HTTP 服务**跑真实节点子进程：

| 场景 | 结果 |
|------|------|
| `--max-consecutive-failures 0`（不限） | 进程 6 秒后**仍然存活**，共发出 **6 次**请求 —— **旧代码在第 1 次 500 就死了** |
| 上限 6 | **退出码 4**；stderr 显示 `重试 3/6…5/6` 后「连续失败 6 次 … 退出码 4」；日志文件 `node.log` 14 行含该原因 |

### 3.3 静态门禁

- `ruff check scripts/node/cameltv_node/cli.py --select F821` → All checks passed；`ruff check` 默认规则集（含新测试文件）→ All checks passed
- 仓库 `scan-common-bugs.ps1` → **HARD 0**
- 未新增第三方依赖（仅 stdlib `logging`/`logging.handlers`/`random`/`traceback`）

## 4. 未完成 / 未主张

- **未关闭 C269-3**：追踪器解除条件 ④ 要求「修复后做一次『平台重启 → 节点自动重连』实测」，需要**真实平台 + 已注册节点令牌**，本批无法在沙箱内完成。当前结论由**机制测试 + 真实 500 服务端实机探针**支撑，不等于实机演练。
- 除本文件外未新增 QA 报告（由批次报告统一承载）。

## 5. 行为变化与残余风险

1. **退出码变化**：平台故障现为 **4**（原 `SystemExit(2)`）。`--once` 在平台故障时返回 4，而旧代码会把任务中途的 `TransportDown` 吞掉后返回 0。`drill_b1_e2e.py` 只在成功路径断言 `==0`，平台健康时仍绿；但**平台抖动时演练会如实失败**（这正是本次想要的语义）。
2. **令牌失效（401/403）按可恢复处理**：节点会在约 6–7 分钟后（5s 基数 / 60s 上限 × 10 次）带凭据提示退出 4，而不是立刻退出。这与解除条件 ① 一致；若运维希望鉴权问题快速失败，需另加开关。
3. **持有任务时平台持续不可用**：节点退出 4，任务保持 running 直到租约过期被回收（日志会明确写出 job id）。**只有平台能把它放回 pending**——不存在节点侧释放端点。
4. 上报重试会**重复上传证据**，但为幂等（`execution_evidence_store.save_bundle` 按 (job, attempt) 覆盖并重写 `manifest.json`），已核对无重复证据包。
5. 本地（非平台）证据错误（如 `evidence.collect_files` 抛 `ValueError`）仍为致命 + traceback（既有行为；现在至少经 excepthook 落到日志文件）。
6. 默认日志路径在节点用户 home 下；演练把 `HOME`/`USERPROFILE` 指向临时目录，故演练日志落在该临时目录。
