# cameltv-node —— 本地执行节点

平台的**控制面只做登记 · 调度 · 证据 · 知识**：它不跑浏览器、不跑模型、不存被测系统凭据
（ADR-0026 / `docs/platform-refactor/09-platform-landing-plan.md` §3.1）。
接口与 Web 用例的真实执行发生在**你本机的这个节点**里，按需启动、用完即退。

## 一条命令开工

```bash
cameltv-node up --node-id my-pc --capabilities api web
```

Windows 用仓库里的 `cameltv-node.cmd`；也可以直接 `python scripts/node/cameltv_node/cli.py up ...`。

首次运行需要平台登录态来签发节点令牌（令牌只返回一次，存在 `~/.cameltv-node.json`）：

```bash
cameltv-node login --username <你的平台账号> --project-id <项目ID>
cameltv-node up --node-id my-pc          # 自动注册并开始认领
```

`up` 做的四件事：注册/复用节点身份 → 执行中每 30s 心跳续租 → 认领任务并真实执行 →
上传证据（sha256 对账）并上报结果。

## 断线不丢任务

租约默认 300 秒（平台 `EXECUTION_JOB_LEASE_SECONDS`）。节点断网或崩溃时不再续租，
平台把任务回收为 `pending`（`attempt + 1`）——**不会丢**。节点恢复后重新 `up` 即可继续认领：

```bash
cameltv-node up --node-id my-pc          # 重启后接着干
```

按 Ctrl+C 停止是安全的：心跳立即停止，任务由租约超时回收，而不是被误判为失败。

## 平台故障自愈（C269-3）

平台**可达但报错**（HTTP 4xx/5xx、业务码 != 0）与断网一样按**可恢复**处理：节点留日志、退避、继续跑，
不再退出进程（Batch 269 的 `call()` 对 `status>=400 或 code!=0` 抛 `SystemExit(2)`，而轮询循环只捕
`TransportDown` → 一次 500/403 就让节点无声消失、任务滞留 `pending`）。

- **退避**：指数 + 抖动；`--backoff-base-seconds`（默认 5s）起，`--max-backoff-seconds`（默认 60s）封顶；
- **连续失败上限**：`--max-consecutive-failures`（默认 10，`0` = 不限；也可用 `CAMELTV_NODE_MAX_FAILURES`），
  达到即退出码 `4` 并把原因写进 stderr 与日志，交 supervisor 重启——不会静默空转；
- **已认领的任务只重试不丢弃**：执行中途遇到平台错误会重试**同一任务**（心跳持续续租）；上报失败只重发结论、
  不重跑用例；平台回 404（租约已回收/改派）才放手，此时任务已被平台放回 `pending`；
- **`--once` 语义不变**：仍然只跑一轮；该轮平台失败返回 `4`，而任务结论为失败仍返回 `0`（CI/自检看退出码）。

退出码：`0` 正常 / `1` 任务结论失败 / `2` 用法或配置错误 / `3` 执行器依赖缺失 / `4` 平台侧失败。

## 日志落盘

节点诊断输出**同时写 stderr 与日志文件**（默认 `~/.cameltv-node/logs/cameltv-node.log`，
可用 `--log-file` 或 `CAMELTV_NODE_LOG_FILE` 覆盖；5 MB × 5 轮转，追加写入）。
Batch 269 的退出事故无法逐帧回看，就是因为当时该节点的 stderr 没有落盘；日志目录不可写时自动降级为仅 stderr，
不影响节点干活。

## 子命令

| 命令 | 用途 |
|------|------|
| `login` | 登录平台，保存会话（注册节点用） |
| `register` | 注册/复用节点并签发节点令牌 |
| `doctor` | 自检：平台连通性、凭据、本项目节点与队列状态 |
| `up` | 注册 + 心跳 + 认领循环（`--once` 只跑一轮；平台故障退避重试，见下两节） |
| `run-api` | 本地执行接口用例：`--job <id>` 或 `--job-file payload.json` |
| `run-web` | 本地执行 Web 用例（Playwright） |
| `upload` | 上传证据目录：`--job <id> --dir ./evidence` |
| `show` | 查看任务详情 |

## 用例载荷格式

平台登记任务时把**载荷**一并写入（`payload.cases`），节点按 `kind` 选择执行器。

接口用例（`kind=api`，httpx 直发）：

```json
{
  "base_url": "https://example.com",
  "cases": [{
    "id": "home-1",
    "name": "首页列表",
    "request": {"method": "GET", "url": "/api/home", "headers": {"Accept": "application/json"}},
    "assertions": [
      {"type": "status", "expected": 200},
      {"type": "json_path", "path": "$.data.today", "expected": "20260918"},
      {"type": "not_empty", "path": "$.data.list"}
    ]
  }]
}
```

Web 用例（`kind=web`，Playwright）：

```json
{
  "base_url": "https://example.com",
  "cases": [{
    "id": "home-ui-1",
    "name": "首页轮播可见",
    "steps": [
      {"action": "goto", "url": "/"},
      {"action": "wait_visible", "selector": ".banner"},
      {"action": "expect_visible", "selector": ".banner"},
      {"action": "expect_text", "selector": "h1", "expected": "赛事"}
    ]
  }]
}
```

支持的动作：`goto` / `click` / `fill` / `press` / `wait_visible` / `expect_visible` /
`expect_text` / `wait`。每条用例都会留下截图（`<case>.png`）与控制台错误（`<case>.console.json`）。

## 证据

每次尝试写入独立目录，并生成 `manifest.json`（逐文件 sha256）：

```
cameltv-node-evidence/job-12-attempt-1/
├── home-1.request.json      ← 失败可回放的请求
├── home-1.response.json     ← 响应
├── home-ui-1.png            ← 截图
├── home-ui-1.console.json   ← 控制台错误
├── results.json
└── manifest.json
```

上传时会拿平台返回的 manifest 与本地 sha256 对账，不一致直接报错，避免"传了但截断"。
完整性与篡改显红由后续 B4-1 的证据包定型接管。

## 诚实原则

依赖缺失、断言失败、上传失败都会**如实**记为失败/告警，绝不伪造成通过：

- 未安装 Playwright → `run-web` 报 `failed` 并提示 `pip install playwright && playwright install chromium`；
- 上传对账不一致 → 任务上报里带 `upload_error`，不静默吞掉；
- 断网 / 平台 4xx/5xx → 不算失败，退避重试（已认领任务继续持有，或交给租约回收）。
