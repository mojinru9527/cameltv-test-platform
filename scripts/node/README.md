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

## 子命令

| 命令 | 用途 |
|------|------|
| `login` | 登录平台，保存会话（注册节点用） |
| `register` | 注册/复用节点并签发节点令牌 |
| `doctor` | 自检：平台连通性、凭据、本项目节点与队列状态 |
| `up` | 注册 + 心跳 + 认领循环（`--once` 只跑一轮） |
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
- 断网 → 不算失败，交给租约回收。
