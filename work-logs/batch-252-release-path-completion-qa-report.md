# Batch 252 — QA Report（发布链路收口）

> **🔍 QA** | Date: 2026-09-17 | 立场：默认「需要改进」
> 分支：`feature/batch-252-release-path-completion`（base `c37c03a7`）
> 变更范围：`test-platform-v2/backend/Dockerfile`、`test-platform-v2/backend/tests/`、`deploy/release-console/`、`scripts/ops/`、`.claude/skills/`、`work-logs/`

## 1. 结论

**PASS**。四条 Open 条件全部修复并有可复核证据：runner 镜像**本地真实构建成功**、
沿用镜像核对脚本在生产双向验证、控制面 COPY 有 import 图守卫、技能文件含"接续旧分支先比对 main"。

| 指标 | 状态 |
|------|------|
| M1 runner target 本地可构建 | ✅ 真实构建成功（`node v22.23.2 / npm 10.9.8`） |
| M2 装不上 Node 就立刻失败 | ✅ 契约测试 + 修复前后日志对比 |
| M3 沿用镜像前一条命令核对 | ✅ 本机新镜像 OK(0) / 生产 runner OK(0) / 负向对照 BLOCK(1) |
| M4 控制面不漏拷模块 | ✅ 守卫测试（含负向用例） |
| M5 技能回写 | ✅ SKILL.md + DEPARTMENTS.md + CHANGELOG |

## 2. 硬门禁证据

| 门禁 | 命令 | 结果 |
|---|---|---|
| **runner 真实构建（C248-8 核心）** | `docker buildx build --network=host -f test-platform-v2/backend/Dockerfile --target runner -t cameltv-tp-runner:c248-8-probe .` | **成功**；日志 `#15 … node v22.23.2 / npm 10.9.8`；`#25 naming to … cameltv-tp-runner:c248-8-probe` |
| 新镜像内容核验 | `docker run --rm cameltv-tp-runner:c248-8-probe sh -c "node --version; npm --version; ls /app/alembic/versions \| wc -l; …"` | `v22.23.2`、`10.9.8`、`112` 个迁移、`playwright_ok`、chromium-1228 |
| 后端图形契约测试 | `pytest tests/test_image_split_cache_contract.py -q` | **6 passed**（含新增 Node 供给契约） |
| 控制面全量测试 | `cd deploy/release-console && pytest tests -q` | **66 passed, 2 subtests passed**（Batch 251 基线 54 → +12） |
| 控制面 lint | `ruff check .` | All checks passed |
| 沿用镜像核对（本机镜像） | `verify-reused-image.ps1 -Image cameltv-tp-runner:c248-8-probe -Part runner` | OK（7 个模块，exit 0） |
| 沿用镜像核对（生产镜像） | `… -Image cameltv-tp-runner:release-20260917-0007 -SshHost …` | OK（exit 0） |
| 沿用镜像核对（负向对照） | `… -Image cameltv-tp-ai-gateway:release-20260917-0007 -Part runner` | **BLOCK**（缺 `alembic` 三件套，exit 1） |
| `release.ps1` 语法 + `-DryRun` 回归 | Parser + `-DryRun` | 语法 OK；仍"未构建、未登记、未上传、未发布" |
| `verify-reused-image.ps1` 语法 | Parser | OK |

## 3. 缺陷与根因（本批修复的都是既有条件）

### 🟠 C248-8（P1）`--target runner` 本地不可构建 —— 根因：管道吞失败导致静默降级

- **修复前证据**：`#17 … /bin/sh: 1: npm: not found`（exit 127），且装 Node 的 `#12 [runner 1/10]` 显示 **CACHED**——
  缓存里那一层**只装了 node、没有 npm**。
- **根因**：`curl -fsSL https://deb.nodesource.com/setup_22.x | bash -` 无 `pipefail`，
  curl 失败时管道退出码取 `bash -`（0），随后 `apt-get install nodejs` 命中 Debian 仓库的 nodejs
  （Debian 把 npm 拆成独立包）→ **有 node、无 npm**。
- **修复**：setup 脚本先落盘（`curl -fsSL --retry 3 -o /tmp/nodesource_setup.sh`）再 `bash` 执行；
  同一 RUN 内断言 `process.versions.node` 必须是 `22.x` 且 `npm --version` 可执行。
- **验收**：真实构建成功；契约测试锁定该层不得再用 `| bash -` 管道。
- **附带发现**：本机 BuildKit **默认网络**取 `deb.debian.org` 的个别 `.deb` 会稳定失败
  （两次复现 `Unable to connect to deb.debian.org:http`），而 `docker run` 内 apt 正常 →
  `release.ps1` 的 buildx 固定 `--network=host`，使 4 个镜像能在本机完整构建。

### 🟠 C249-5（P1）沿用旧镜像无核对手段

- **修复**：`deploy/release-console/image_contract.py`（AST 解析 `RUNNER_ENDPOINTS` + 必需路径 + 差异比对）
  + `scripts/ops/verify-reused-image.ps1`（容器内探测，退出码 0/1）+ README 核对清单。
- **验收**：生产 runner 镜像 OK；把 ai-gateway 镜像当 runner 用时 BLOCK 并列出缺失路径（正是 Batch 248 类隐形故障的判定）。

### 🟡 C249-7（P1）控制面 Dockerfile 显式 COPY

- **修复**：`COPY *.py ./`（新增模块自动进镜像）+ `tests/test_dockerfile_copy_guard.py`
  （从 `app.py` 按 import 图求可达模块，校验 COPY 覆盖；负向用例把 COPY 换回 Batch 249 的列表必须报 `migrations.py`）。

### ⚪ C249-6（P2）流程经验未回写

- **修复**：SKILL.md 新增「动手前先判断分支是否已被 main 取代」（含 `git diff --stat origin/main...HEAD` 与同名文件比对口径）、
  多窗口 Red Flag 补一条；DEPARTMENTS.md Leader 节第 6 条同步；CHANGELOG 追加一条（日期/批次/摘要/动因）。

## 4. 遗留与观察

- 本机 BuildKit 网络偶发失败已用 `--network=host` 固化；若 CI 环境有代理策略差异，需在 CI 侧确认（未登记为新条件）。
- 本轮**未**再跑一次完整 `release.ps1 -Publish`（当前生产 `release-20260917-0007` 已验证、镜像与配置未变）；
  若需要"发布脚本端到端不再需要手工组装"的闭环证据，可另起一次发布窗口（预期 20–30 分钟）。

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际约 2.5h | 0/0/0/0（本批为修复既有条件） | 2（apt 取包偶发失败重跑；契约测试被自己注释里的反模式字面量误伤后改为只看指令行） | 工具链 + 技术债 | ①shell 管道 `|` 装东西必须显式处理失败（`pipefail`/落盘再执行）；②契约测试解析 Dockerfile 时先剔除注释行 |
