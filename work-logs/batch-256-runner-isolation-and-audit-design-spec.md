# Batch 256 — Design Spec
> **Design (🎨)** | Date: 2026-09-18 | Status: 就绪

> 本批为「运行时隔离 + 依赖供应链」类改动，无 UI 组件/视觉改动（PRD §3 已声明非目标）。
> 设计部门输出的是**运行时安全边界规格**与**配置契约规格**，用于 Dev 落地、QA 断言。

## 0. 技术体系确认

- 编排：Docker Compose（base `docker-compose.yml` + 可选执行面 overlay `docker-compose.execution.yml`）。
- 执行面服务：`runner`（浏览器/UI 任务、生成 job）与 `aitde-worker`（Temporal 队列、BROWSER 能力）。
- 运行时用户：镜像已 `USER cameltv:cameltv`（UID/GID 10001），`HOME=/home/cameltv`，`XDG_CACHE_HOME=/home/cameltv/.cache`，`PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`。

## 1. 安全边界规格表（执行面容器）

| 维度 | 目标值 | 现状（实测） | 落点 |
|------|--------|-------------|------|
| `read_only` | `true` | 未设置 | base + overlay 的 `runner`/`aitde-worker` |
| `tmpfs` | `/tmp`、`/home/cameltv/.cache`、`/home/cameltv/.npm` | 未设置 | 同上 |
| `cap_drop` | `ALL` | runner 继承 ✅ / aitde-worker 继承 ✅ | 显式写出，避免继承链被改动时静默失效 |
| `security_opt` | `no-new-privileges:true` | runner ✅ / **aitde-worker ❌** | base + overlay 的 `aitde-worker` |
| `user` | `10001:10001` | 镜像 USER 已非 root（compose 未显式声明） | 显式声明，防基础镜像改动 |
| `init` | `true` | ✅ | 保持 |
| 资源限制 | `pids_limit` / `mem_limit` | ✅ | 保持 |

## 2. 可写路径白名单（只读 rootfs 的前提）

| 路径 | 写入者 | 处置 | 依据 |
|------|--------|------|------|
| `/tmp` | Playwright / Node / Python 临时文件；`WORKER_RUNTIME_DIR=/tmp/aitde-worker`（heartbeat.pid、gateway.pid） | tmpfs | `deploy/aitde-runtime/scripts/start-worker.sh` |
| `/home/cameltv/.cache` | `XDG_CACHE_HOME`（pip/npm/Playwright 缓存） | tmpfs | `backend/Dockerfile` ENV |
| `/home/cameltv/.npm` | node/npm 运行期缓存 | tmpfs | 同上 |
| `/app/storage` | 生成物、蓝湖证据、`HEAVY_TASK_BUDGET_DIR=/app/storage/resource-budget` | 卷 `tp-artifacts` | compose volumes |
| `/data` | 数据库/模型缓存（`EMBEDDING_CACHE_DIR=/data/models/fastembed`） | 卷 `tp-data` | compose volumes |
| `/app/tests/playwright/specs/generated`、`/app/tests/playwright/generated` | 生成 spec/job | 执行面 overlay 卷；base compose 无卷时用 tmpfs 兜底 | `docker-compose.execution.yml` |
| `/ms-playwright` | 镜像内预置浏览器（构建期安装） | **保持只读**（运行期不再 `playwright install`） | `backend/Dockerfile:143-144` |

> 设计决策：`/ms-playwright` 不做 tmpfs —— tmpfs 会**遮蔽**镜像内已安装的浏览器；运行期安装新浏览器版本属 PRD §5 已接受的风险 3。

## 3. 状态设计核对（四态）

| 场景 | 期望表现 | 验证方式 |
|------|---------|---------|
| 正常执行（只读 rootfs + 浏览器） | 浏览器启动、任务产出证据 | 真实容器跑一次 UI 任务 |
| 运行期写镜像路径 | 明确 `Read-only file system` 报错，不污染容器层 | 真实容器内向 `/app` 写入断言失败 |
| 缺少 `API_TOKEN` 的 worker | 启动即退出码 2 并给出可执行提示（既有行为不变） | `start-worker.sh` 现有逻辑 |
| 依赖树变更后审计 | 真 0 而不是镜像源假 0 | 显式 `--registry` 的审计命令 |

## 4. 设计 QA 走查发现

### 🟠 P1-1 侦察文档与实测不一致（cap_drop 继承）
`work-logs/batch-256-recon-handoff.md:52` 记「runner 无 cap_drop」。实测有效配置为 `cap_drop: ALL`（继承自 `backend`）。
**建议**：PRD/QA 以 `docker compose config` 有效配置为准，并把加固重点放在**继承链的反例**（aitde-worker 缺失 `security_opt`）上。

### 🟡 P2-1 隐式继承是脆弱契约
`runner` 的安全性依赖 `extends: backend` 的继承；有人改动 base 段即可静默削弱执行面。
**建议**：在执行面两个服务上**显式**声明 `cap_drop`/`security_opt`/`user`，并由契约测试断言（US-4）。

### 🟡 P2-2 审计命令的 registry 默认值陷阱
`npm audit` 在本机默认打 `registry.npmmirror.com`，返回 `NOT_IMPLEMENTED` 却可能被读成"无漏洞"。
**建议**：审计调用点与文档示例显式带 `--registry=https://registry.npmjs.org`，并把该事实写入常见坑位文档。

## 5. 设计签核

结论：**通过**（无 P0 阻断项；P1-1 已在本批纠正，P2 项纳入 Slice 3/4 实现与测试）。
