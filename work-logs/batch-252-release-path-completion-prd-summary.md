# Batch 252 — 发布链路收口（C248-8 / C249-5 / C249-6 / C249-7）PRD

> **🟦 Product** | Date: 2026-09-17 | 分支：`feature/batch-252-release-path-completion`
> 批次模式：**完整批次**（触及 `test-platform-v2/backend/Dockerfile` = 构建配置变更）

## 1. 问题陈述（为什么用户/运维关心）

2026-09-17 一天内做了 3 次生产发布（-0005/-0006/-0007），每次都被同一批"发布链路自身"的问题拖住：

1. **runner 镜像本机根本构建不出来**：`--target runner` 连续三次失败，被迫"复用已验证镜像"绕过。
   根因不是网络，而是 Dockerfile 里 `curl -fsSL … | bash -` 的**管道吞掉了下载失败**（无 pipefail），
   于是静默退化成 Debian 的 nodejs——**有 node、没有 npm**，构建要到下一步才以 `npm: not found` 报 exit 127。
   更糟的是：这层一旦被缓存，后续构建"看起来"能跳过，掩盖问题（本次修复触发重建才暴露）。
2. **沿用旧镜像没有任何核对手段**：复用镜像/打补丁镜像时，若镜像里的转发面（`RUNNER_ENDPOINTS`）
   或 `alembic/versions` 与当前配置不一致，会出现"容器能起、任务全挂 / 迁移不可用"的隐形故障，
   发布日志里完全看不出来（Batch 248 事故的教训），只能靠人肉记忆。
3. **控制面 Dockerfile 显式列举 COPY**：Batch 249 新增 `migrations.py` 没被拷进镜像，
   直接部署会让"恢复平面"起不来（PR #464 救回）。同类事故只差一次新增模块。
4. **流程经验没有回写**：Batch 249 曾在已被 main 取代的分支上白做一轮（S1），
   但"接续旧分支前先比对 main"这条动作没有写进技能文件，后续批次随时可能重犯。

## 2. 成功指标

| # | 指标 | 判定 |
|---|------|------|
| M1 | runner target 本地可构建 | `docker buildx build --target runner` 成功，且构建日志出现 `node v22.x / npm x.y` |
| M2 | 装不上 Node 时**立刻失败**、不再静默降级 | 契约测试断言该层含 node 主版本与 npm 断言、且不使用 `\| bash -` 管道 |
| M3 | 沿用旧镜像前有一条命令可核对 | `verify-reused-image.ps1` 对生产 runner 镜像返回 OK(0)，对不合规镜像返回 BLOCK(1) |
| M4 | 控制面镜像不会漏拷模块 | 守卫测试按 import 图校验 COPY 覆盖；把 COPY 换回 Batch 249 的列表时必须报 `migrations.py` |
| M5 | 技能/部门文件含"接续旧分支先比对 main"动作 | SKILL.md + DEPARTMENTS.md 各有一处；CHANGELOG 同批追加 |

## 3. 非目标（本批不做）

- 不改发布流程的镜像构成/拓扑（split 仍是 runner + ai-gateway + api + frontend）。
- 不动 `RUNNER_ENDPOINTS` 契约本身（只做"镜像 vs 仓库"的一致性核对）。
- 不追 C-CONDITIONS 里其它历史 Open 条件（本次范围以用户确认的 4 条为准）。
- 不解决**本机 BuildKit 网络**偶发问题（apt 取包偶发失败）——本批只把"失败要吵"做进 Dockerfile。

## 4. 用户故事与验收标准

### US-1（发布负责人）runner 能在本机/CI 正常构建

- **Given** 我需要出一个 split 版本（含 runner 镜像）
- **When** 我执行 `docker buildx build --target runner …`
- **Then** 构建成功，且日志里能看到 `node v22.x / npm <ver>`
- **And** 若 NodeSource 下载或安装失败，构建**在那一层就失败**并打印明确原因（不再进入下一步才报 `npm: not found`）

### US-2（发布负责人）沿用旧镜像前有据可依

- **Given** 我打算复用某个已验证 runner/backend 镜像
- **When** 我执行 `pwsh scripts/ops/verify-reused-image.ps1 -Image <img> -Part runner -SshHost <prod>`
- **Then** 报告显示必需路径（`alembic`/`alembic/versions`/`alembic.ini`）与转发面覆盖情况
- **And** 任何缺失 → 退出码 1 并明确"不得沿用该镜像"

### US-3（运维）控制面不会因为"忘了 COPY"而自锁

- **Given** 有人在 `deploy/release-console/` 新增一个被 `app.py` 导入的模块
- **When** 我跑控制面测试
- **Then** 守卫测试会指出该模块没进镜像（Dockerfile 已是 `COPY *.py ./`，仍防回退成显式列表）

### US-4（后续 Agent）接续旧分支不白做

- **Given** 我要接续一个陌生/陈旧分支
- **When** 我按技能执行 `git diff --stat origin/main...HEAD` 并比对同名文件
- **Then** 若 main 已有同等或更完整实现，我会先请 Leader 确认再决定是否继续

## 5. 纳入本批的 C 条件

| ID | 内容 | 本批处理 |
|----|------|---------|
| C248-8 | `--target runner` 本地可构建性 | ✅ 修复（失败即中断 + node/npm 断言）+ 真实构建验收 |
| C249-5 | 沿用旧镜像前核对 `RUNNER_ENDPOINTS` / `alembic/versions` | ✅ 可执行核对 + 文档 + 生产双向验证 |
| C249-6 | SKILL.md/DEPARTMENTS.md 补"合并前先比对两侧同名文件规模" | ✅ 技能回写 + CHANGELOG |
| C249-7 | 控制面 Dockerfile 显式 COPY → 通配 + 守卫测试 | ✅ `COPY *.py ./` + import 图守卫 |

## 6. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| runner 构建涉及 apt/NodeSource/Playwright 下载，本机网络偶发失败 | 中 | 构建失败保留完整日志；不改用 `\|\| true` 类容错；网络问题单独记录，不掩盖 |
| 通配 `COPY *.py ./` 可能把不该进镜像的脚本带进去 | 低 | `release_cleanup.py` 等宿主维护脚本本就在同一目录，带进镜像无副作用（无入口执行）；守卫测试仍按 import 图判定"必需" |
| 核对脚本依赖镜像内有 python | 低 | runner/backend/api 镜像都基于 python 基础镜像；ai-gateway 不在必需路径表内（`required_paths('ai-gateway')` 为空） |
