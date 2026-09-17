# Batch 256 侦察与交接：C243-1（Runner 隔离）+ C246-1（依赖审计）

> Date: 2026-09-18 | 基线 main `96cd5b65` | 本文件只做**侦察与任务分解**，未改任何代码

## 1. C246-1 — dev-only npm audit（实测数据）

### 事实

1. **默认镜像源不能审计**：本机 `npm audit` 打的是 `registry.npmmirror.com`，该镜像未实现
   advisories 接口 → `[NOT_IMPLEMENTED] /-/npm/v1/security/*`。**审计/ratchet 必须显式指定
   `--registry=https://registry.npmjs.org`**（否则"没有漏洞"是假象）。
2. 实测（`npm audit --registry=https://registry.npmjs.org --json`）：

```
summary: {low: 2, moderate: 1, high: 7, critical: 0, total: 10}
high | @lhci/cli      | direct=True  | via: @lhci/utils, inquirer
high | @lhci/utils    | direct=False | via: lighthouse
high | lighthouse     | direct=False | via: puppeteer-core
high | puppeteer-core | direct=False | via: @puppeteer/browsers
high | @puppeteer/browsers | direct=False | via: extract-zip
high | extract-zip    | direct=False | via: 符号链接路径穿越 / 任意文件写
high | tmp            | direct=False | via: 符号链接任意写 / prefix-postfix 路径穿越
moderate | uuid       | direct=False | via: v3/v5/v6 buf 越界
```

3. **全部经 `@lhci/cli`（dev 依赖）传导**；npm 给出的唯一"fixAvailable"是
   `@lhci/cli@0.6.1`（semver-major 意义上的变更，实为降级到旧版），说明**不能靠 `npm audit fix` 解决**。

### 建议处置（三选一，按推荐顺序）

| 方案 | 做法 | 风险 |
|---|---|---|
| A（推荐） | 用 `package.json` 的 `overrides` 钉住传递依赖到已修复版本：`tmp`、`extract-zip`、`uuid`（必要时含 `puppeteer-core`） | 低：不改 LHCI 主版本；需跑一次 a11y job 验证 |
| B | 升级 `@lhci/cli` 到最新主版本（若其依赖已修复） | 中：LHCI CLI 参数/配置可能变化，需同步 `lighthouserc`/CI 步骤 |
| C | 把 LHCI 移出常规 dev 链（改为按需运行的工具镜像/独立 job） | 中：改变 a11y 门禁形态，需与 CI 策略一起评估 |

### 验收标准

- `npm audit --registry=https://registry.npmjs.org --json` → `high=0 critical=0`
- `npm-audit-baseline.json` ratchet 更新到新基线（且能阻止新增 advisory）
- 前端 `npm ci && npm run typecheck && npm run build` 全绿；a11y/LHCI 相关 CI 步骤仍可运行
- 文档/CI 中所有 `npm audit` 调用点补齐 `--registry`

## 2. C243-1 — 单任务 Runner 隔离 / 只读 rootfs / egress

### 现状（`test-platform-v2/deploy/docker-compose.yml` runner 段，实测行号 255+）

已有：`init: true`、`mem_limit`（默认 1536m）、`pids_limit: 256`、`security_opt: [no-new-privileges:true]`、
`stop_grace_period: 60s`、healthcheck。执行面 overlay（`docker-compose.execution.yml`）另加
`HEAVY_TASK_BUDGET_*`、`ORCHESTRATION_BUDGET_CAPACITY`、生成物卷。

### 缺口（与 C243-1 要求逐条对照）

| 要求 | 现状 | 待补 |
|---|---|---|
| 单任务 Runner 容器隔离 | 单 runner 服务 + 进程内预算（capacity=1），**非"每任务一个容器"** | 决定形态：容器级隔离（每任务 `docker run` 一次性容器）或用命名空间/子进程 + cgroup 限额；需评估改造面 |
| 只读 rootfs | 未设置 | `read_only: true` + 显式 `tmpfs:`（`/tmp`、`/ms-playwright` 可写点）+ 卷白名单（`/app/storage`、生成物卷） |
| 更严格 egress policy | 依赖默认 bridge，无出站限制 | 方案：专用 network + `internal: true` + 必要出口经代理/白名单；或主机层 iptables/nftables 规则 |
| 其它加固（顺带） | 无 `cap_drop` | `cap_drop: [ALL]`（配合 `no-new-privileges`），必要时 `user:` 非 root 运行 |

### 关键风险（必须先验证再上生产）

1. **只读 rootfs 与 Playwright/浏览器缓存的冲突**：`/ms-playwright`、`/tmp`、`PLAYWRIGHT_BROWSERS_PATH`
   需要可写点或预置只读缓存；错配会让 UI 任务全挂。
2. **aitde-worker** 同样跑 browser（共享准入），execution overlay 的 runner/aitde-worker 都必须同步改造，否则时间线任务会绕开隔离。
3. **egress 收紧会打断真实被测站点访问**（Test5 内网、目标业务域名）；需要白名单与"不可达时明确报错"的提示。
4. 验证成本：本地 compose 起栈 + 至少一次真实 UI 任务执行（或 CI 冒烟），不能只看 `docker compose config`。

### 建议切片（每片独立可验证）

| 切片 | 内容 | 验证 |
|---|---|---|
| S1 | `cap_drop: [ALL]` + 非 root 运行 + 保持现有卷/健康检查 | `docker compose config` + 起栈跑一个 UI 任务 |
| S2 | `read_only: true` + `tmpfs` 白名单（`/tmp`、浏览器缓存）+ 卷补齐 | 同上；重点验证 Playwright 能起浏览器 |
| S3 | egress 白名单（专用 network 或主机规则）+ 不可达时的可执行提示 | 真实站点可达 + 白名单外域名被拒 |
| S4 | 单任务容器隔离形态决策与 PoC（若采用每任务容器） | 并发=1 预算与取消/超时语义回归 |

> 建议 S1→S4 逐个合入，不要一次改完：S2/S3 出问题会直接影响所有 UI 与数据任务的执行能力。

## 3. 本批未做的事（明确交接）

- 未改任何代码/配置（侦察批次）。
- C246-1 的 registry 事实与依赖树已实测；C243-1 的缺口已逐条对照 compose 现状。
- 下一步建议：**先做 C246-1 方案 A**（改动最小、纯 dev 链、可用 audit+build 验证），
  再做 C243-1 的 S1→S2（改动集中在 compose，需一次真实执行验证）。
