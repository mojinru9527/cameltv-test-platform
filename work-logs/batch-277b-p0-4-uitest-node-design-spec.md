# Batch 277b-1 — P0-4 `/uitest` 节点化：Design Spec

> **部门**：🎨 Design
> **日期**：2026-11-09
> **对象**：`ui_job_dispatch`、`UiTestRun.execution_job_id`、节点 `run_spec_files`、`uitest_execution_mode`

---

## 1. 两条执行路径

```text
local（默认，现状不变）
  POST /ui-tests/{id}/trigger
    → _check_playwright_installed()
    → UiTestRun(pending) → ui_runner_queue（线程池）
    → playwright_executor（控制面 subprocess npx playwright test）
    → 写 artifact_dir / report.json / screenshots

node（batch-277b-1 新增，开关 UITEST_EXECUTION_MODE=node）
  POST /ui-tests/{id}/trigger
    → ui_job_dispatch.build_payload（读 spec + spec_guard + env）
    → UiTestRun(pending, execution_job_id=NULL→dispatch 回填)
    → ExecutionJob(kind="ui", payload)
    → cameltv-node claim → run_spec_files（npx playwright test）
    → evidence（sha256 manifest）+ report
    → execution_job_service.report()
        → ui_job_dispatch.sync_run_from_job()
            → UiTestRun(status/result/artifact_dir/finished_at)
            → UiTestJob.status/last_result
            → writeback_case_result()
```

**切换粒度**：整个平台级开关（`settings.uitest_execution_mode`），不做 per-job 混合，避免同一 job 两次触发落到不同执行器。

---

## 2. 载荷契约（`ExecutionJob.payload_json`）

```json
{
  "mode": "spec",
  "entry": "generated/abc.spec.ts",
  "files": [{"name": "generated/abc.spec.ts", "content": "<spec 源码>"}],
  "browser": "chromium",
  "base_url": "https://test.example",
  "env": {"CAMELTV_TARGET_ENV": "test"},
  "timeout_seconds": 900
}
```

约束：

| 约束 | 值 | 理由 |
|------|----|------|
| 单 job spec 大小 | ≤ 2 MB | 防止 DB/传输膨胀 |
| 文件名 | 相对路径、无 `..`、白名单字符 | 防节点路径穿越 |
| 安全拦截 | 控制面 `spec_guard.assert_spec_safe` | 与本地执行同一硬线 |
| env | 仅环境 slot 解析结果（不含平台 `SECRET_KEY` 等） | 与本地执行一致 |
| base_url | `test_runs` 同源环境 `base_url` | 可复现 |

---

## 3. 状态投影（`sync_run_from_job`）

| ExecutionJob | UiTestRun | UiTestJob |
|--------------|-----------|-----------|
| `completed` | `done` | `done` |
| `failed` | `fail` | `fail` |
| `cancelled` | `cancelled` | 保持原状态 |
| `result_json` | `result` | `last_result` |
| `error_message` | `error_message` | — |
| `finished_at` | `finished_at` | — |
| `evidence_store.bundle_dir(id, attempt)` | `artifact_dir` | — |

- 产物下载沿用现有 `/ui-tests/runs/{id}/artifacts[/{name}]`（读 `artifact_dir` 文件树）；
- 投影失败只记日志，不改变节点上报结果（避免"节点成功、平台 500"）；
- 幂等：重复上报只会写入同样的终态。

---

## 4. 节点执行器契约

```python
run_spec_files(files, *, entry, evidence_dir, base_url, browser, env,
               timeout_seconds, runner=None) -> dict
```

- `runner(cmd, cwd=, env=, timeout=)` 可注入（单测用 fake）；
- 优先使用仓库 `test-platform-v2/tests/playwright` 作为 cwd（已有配置与依赖）；否则落到证据目录内的 `spec/`；
- 命令：`npx playwright test <spec> --output <evidence>/test-results`；
- 环境：`BASE_URL` / `CAMELTV_BASE_URL` / `BROWSER` / `PLAYWRIGHT_JSON_OUTPUT_NAME`，并剔除 `SECRET/TOKEN/PASSWORD` 前缀变量；
- 报告：读取 `report.json`，拍平 `suites[].specs[].tests[].results[].status`；
- 失败诚实：无报告/超时/非法文件名 → `all_pass=false` + `error`，绝不伪造通过。

---

## 5. 失败模式

| 场景 | 行为 |
|------|------|
| spec 不存在/越权 | `trigger` 直接建 failed run，`error_message` 说明 |
| guard 命中 | 同上，返回"禁止使用的 API"明细 |
| 无在线节点 | `ExecutionJob` 停留 `pending`（租约/回收机制兜底），run 保持 `pending` |
| 节点执行超时 | job `failed`，run `fail`，error 含超时 |
| 证据上传失败 | 节点仍上报结论，`upload_error` 写入 result（现有节点行为） |

---

## 6. 为什么本批不切默认

1. 节点机器需具备 `npx playwright`（仓库依赖或全局），未验证；
2. 控制面还有 `xhr_capture_service`（`/ui-tests/capture`）与 playground 在本地起 Chromium，**Dockerfile 去 Chromium 需一并处理**；
3. P0-4 验收要"真实节点跑通 + 镜像无 Chromium"，不能靠单测替代。

**277b-2 清单**：

- [ ] 测试环境用真实节点跑通一次 `/uitest`（截图 + report.json + sha256 证据）
- [ ] `UITEST_EXECUTION_MODE=node` 设为部署默认
- [ ] 处理 `xhr_capture` / playground 的浏览器依赖（迁节点或明确降级）
- [ ] 控制面 Dockerfile 删除 `playwright install` 两行 → `docker image inspect` 无 Chromium
- [ ] 写 `work-logs/p0-evidence/P0-4-control-plane-no-browser.json`，守卫 P0-4 转绿
