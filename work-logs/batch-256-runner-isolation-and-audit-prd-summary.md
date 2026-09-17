# Batch 256 — PRD Summary
> **Product (🟦)** | Date: 2026-09-18 | Status: Approved

**批次模式**: 完整批次（引入新配置行为：容器只读 rootfs / tmpfs / 安全选项；依赖树变更）

## 1. 问题陈述

本批次承接 [batch-256 侦察与交接](batch-256-recon-handoff.md) 的两个 P2 条件，它们是当前 Open 清单里生产风险面最大的两项：

1. **C246-1（dev-only 依赖漏洞）**：前端开发链（`@lhci/cli` → `lighthouse` → `puppeteer-core` → 解压工具）带来 7 high / 1 moderate / 2 low advisory。当前只靠 `npm-audit-baseline.json` ratchet 挡新增，没有任何一条被消除；且**默认镜像源 `registry.npmmirror.com` 未实现 advisories 接口**，不显式指定 `--registry=https://registry.npmjs.org` 时审计会返回"无漏洞"的假象（实测 `[NOT_IMPLEMENTED] /-/npm/v1/security/*`）。
2. **C243-1（执行面容器隔离）**：Batch 243 已完成代码级最小权限/env 白名单/资源限制，但**执行面容器的运行时隔离仍未收口**。实测 `docker compose config` 有效配置：`runner` 继承 `cap_drop: ALL` 与 `no-new-privileges`，但 **无 `read_only`、无 `tmpfs`**；`aitde-worker`（profile）虽有 `cap_drop: ALL`，但 **缺 `security_opt: no-new-privileges`**。容器内进程仍可写镜像文件系统（`/app`、`/ms-playwright`、`/home/cameltv`），一旦被测站点或用户 spec 触发任意写，落点就是容器可写层而非隔离点。

> 侦察文档中"runner 无 cap_drop"的结论与实测不符，已由本批更正并核实（`docker compose -f docker-compose.yml -f docker-compose.execution.yml config --format json`）。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| `npm audit --registry=https://registry.npmjs.org --json` high/critical | 7 / 0 | 0 / 0 | 本批 |
| 同上 total advisory | 10 | 0（若上游无修复版，需在 QA 报告中给出逐条不可达证明） | 本批 |
| 生产依赖审计 `npm audit --omit=dev --audit-level=high` | 0 | 保持 0 | 本批 |
| `npm run lighthouse:a11y` 真实跑通（build + preview + LHCI） | 可用 | 可用（overrides 后不得回归） | 本批 |
| 执行面 `read_only: true` 覆盖 | runner 0% / aitde-worker 0% | runner 100% / aitde-worker 100% | 本批 |
| 执行面 `no-new-privileges` + `cap_drop: ALL` 覆盖 | runner 100% / aitde-worker 50% | 100% / 100% | 本批 |
| 只读 rootfs 下真实跑一次浏览器任务 | 无证据 | 浏览器可启动、任务可执行 | 本批 |

## 3. 非目标（本次不做）

- **不做 S3 egress 白名单/专用 network**：需要生产网络拓扑与被测站点白名单，收错会直接打断真实业务域名访问（Test5 内网/目标业务域）。拆分为新条件 `C256-1`，解除条件写清。
- **不做 S4「每任务一次性容器」**：改动面覆盖调度、预算（`HEAVY_TASK_BUDGET_CAPACITY=1`）、取消/超时语义，需独立批次评估 PoC。拆分为 `C256-2`。
- **不改 a11y 门禁形态**：保留 LHCI + Lighthouse，不改为"仅 axe"，避免与 CI 策略同步变更混在同一批。
- **不给 `backend` / `ai-gateway` 加 `read_only`**：两者不执行用户代码（backend 已 `WORKER_EXECUTION_ENABLED=false`），本批只收执行面（runner / aitde-worker），避免扩大回归面。
- **不动 C-CONDITIONS 中与本次无关的其余 Open 条件**（外部依赖类）：与本批模块边界无交集，保持原状。

### C 条件处理

| 条件 | 本批处理 | 证据落点 |
|------|---------|---------|
| C246-1 | 纳入并争取关闭（overrides + 真实 LHCI 验证 + baseline 更新） | `frontend/package.json`、`npm-audit-baseline.json`、QA 报告 |
| C243-1 | 部分纳入：完成 S1（显式 cap_drop/no-new-privileges/user）+ S2（`read_only` + tmpfs 白名单）；S3/S4 拆为 C256-1/C256-2，C243-1 保留追踪收窄后的剩余项 | `deploy/docker-compose*.yml`、QA 报告、C-CONDITIONS.md |

## 4. 用户故事 + 验收标准

**US-1｜平台运维：执行面容器不可写**
- As a 平台运维, I want 执行面容器（runner / aitde-worker）的根文件系统只读且只暴露白名单可写点, so that 被测站点/用户 spec 触发的任意写不会落到容器可写层或镜像内路径。
- 验收：Given 已启用执行面 overlay / When 渲染有效 compose 配置 / Then `runner` 与 `aitde-worker` 均 `read_only: true`、含显式 `tmpfs` 白名单、`cap_drop: ALL`、`security_opt: no-new-privileges:true`
- 验收：Given 只读 rootfs 的 runner 容器 / When 启动 Chromium 并跑一个真实 UI 任务 / Then 浏览器正常启动、任务有成功证据，且向 `/app` 写入被拒（`Read-only file system`）

**US-2｜QA/安全：审计不能有"假 0"**
- As a QA, I want 依赖审计在无漏洞时是真 0、在有漏洞时能报出来, so that 供应链门禁不被镜像源差异欺骗。
- 验收：Given 仓库脚本与文档中的审计调用 / When 检查全部调用点 / Then 均显式带 `--registry=https://registry.npmjs.org`（或等价显式 registry）
- 验收：Given overrides 后的前端依赖树 / When 执行 `npm audit --registry=https://registry.npmjs.org --json` / Then `high=0 && critical=0`；且 `npm ci && npm run typecheck && npm run build` 全绿

**US-3｜流水线维护者：a11y 门禁在依赖收口后仍可用**
- As a 流水线维护者, I want overrides 之后 LHCI 仍能真实产出 a11y 结果, so that 消除 advisory 不以牺牲门禁为代价。
- 验收：Given 干净 `npm ci` / When `npm run build && npm run lighthouse:a11y` / Then LHCI 跑完并返回结果（accessibility 断言按 `.lighthouserc.json` 生效），日志中无依赖加载错误

**US-4｜Dev：门禁被测试钉住，不靠人肉检查**
- As a Dev, I want 容器隔离配置由契约测试断言, so that 后续批次误删 `read_only`/`tmpfs`/`security_opt` 会被 CI 拦住。
- 验收：Given `read_only`/`tmpfs`/`security_opt` 被移除 / When 运行后端部署契约测试 / Then 测试失败（红）

## 5. 技术考量

- **依赖事实（实测）**：`tmp` 漏洞区间 `<=0.2.5`，已发布修复版 `0.2.7`；`uuid <11.1.1`；`@puppeteer/browsers <=2.13.2`；`puppeteer-core 19.8.4–24.43.1`；`extract-zip` 区间 `*`（无修复版，2.0.1 为最新）。
- **解锁点**：`@lhci/cli@0.15.1` 硬依赖 `lighthouse@12.6.1`；`lighthouse@13.4.1` 改用 `puppeteer-core@^25`，而 `@puppeteer/browsers@3.2.2` 已用 `modern-tar` 取代 `extract-zip`。因此用 `overrides` 把 `puppeteer-core`/`@puppeteer/browsers` 抬到已修复主版本，可让无修复版的 `extract-zip` **从依赖树消失**，而不是"绕过告警"。
- **风险 1**：overrides 跨主版本（`puppeteer-core` 24→25）可能破坏 LHCI 运行；必须以真实 `npm run lighthouse:a11y` 作为验收，不以 `npm audit` 单点结论。
- **风险 2**：`read_only` + 白名单错配会让所有 UI/浏览器任务挂掉。可写路径清单（依据 Dockerfile 与启动脚本）：`/tmp`（Playwright/Node/Python 临时文件、`WORKER_RUNTIME_DIR=/tmp/aitde-worker`）、`XDG_CACHE_HOME=/home/cameltv/.cache`、`/home/cameltv/.npm`、卷 `tp-artifacts:/app/storage`、`tp-data:/data`，执行面 overlay 另有 `tp-generated-specs`、`tp-generated-jobs`。
- **风险 3**：`/ms-playwright` 为镜像内预置浏览器，运行期若需要 `playwright install` 新版本会失败——属预期收紧，需在文档写明，并在 QA 中确认现有 UI 任务路径不依赖运行期安装。
- **待解决**：`npm ci` 在 overrides 下可能出现 ERESOLVE；a11y job 为每日观察项（非阻断 required），本批仍要求本地真实跑通。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合并到 main | 主干 | required checks 全绿 + 本批 QA 硬门禁证据 |
| test 环境部署 | QA/研发 | `docker compose up` 后执行面容器带只读 rootfs 起来，健康检查通过 |
| 生产发布（release 火车） | 生产 | 执行面 UI 任务抽检成功；回滚方式：还原 compose 两个文件的 `read_only`/`tmpfs` 段 |

## 7. 技能使用

- `cameltv-bug-guard`：编码前避坑清单（依赖/配置类改动）→ 用于 Dev 切片自检项。
- `cameltv-deploy`：部署面改动需同步部署文档 → 结论：同步 `deploy/README.md`。
- 非测试证据：以上技能只用于补充检查，不替代 QA 章节的可执行门禁。
