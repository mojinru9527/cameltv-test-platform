# Batch 256 — Leader Verdict
> **Leader (🎯)** | Date: 2026-09-18 | Decision: 有条件通过（待用户一次总确认 + required checks）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 4/5 | 依赖用 overrides 让**无修复版**的 `extract-zip` 退出依赖树（而非绕过告警）；执行面隔离显式化，不再依赖 `extends` 继承 |
| 风险控制 | 4/5 | 只读 rootfs 的可写点逐条列举并用真实浏览器探针验证；S3/S4 未做且明确拆分，不假装完成 |
| 覆盖 | 4/5 | 后端 79 passed + 前端 typecheck/lint/710 单测/build/真实 LHCI；两处环境限制已用基线对照证明非本批引入 |
| 流程 | 4/5 | 六部门工件、看板、3 个切片提交、C 条件回写齐全；一次总确认前的门禁遵守到位 |

## 关键决策（已批准）

1. **C246-1 用 overrides 而非降级**：npm 给出的唯一 `fixAvailable` 是 `@lhci/cli@0.6.1`（实为降级）。本批改为把 `puppeteer-core` → `^25.11.0`、`@puppeteer/browsers` → `^3.2.2`（3.x 已用 `modern-tar` 取代 `extract-zip`），使区间为 `*` 的无修复 advisory **从树中消失**；`tmp`→`0.2.7`、`uuid`→`^11.1.1` 一并收口。`@lhci/cli` 与 `lighthouse` 主版本不变。
2. **a11y 门禁不得以"消除告警"为代价**：验收必须包含真实 `npm run lighthouse:a11y`，实测退出码 0、accessibility=1.0、报告 lighthouseVersion=12.6.1 → 证明 override 后的 puppeteer 栈与 LHCI 实际可协同。
3. **执行面加固只在 base 声明**：Batch 243 曾因 overlay 与 base 重复 `security_opt` 导致 compose 校验失败；本轮加固统一写在 base，overlay 继承，并新增回归测试禁止"单例列表重复声明"。
4. **base 与 overlay 语义对齐**：base 拓扑原先不共享生成 spec/job 目录，只读 rootfs 下会成为执行面死角；本批把两个命名卷提升到 base（含 `volume-permissions` 初始化），使两种拓扑隔离语义一致。
5. **`/ms-playwright` 保持只读**：tmpfs 会遮蔽镜像内预置浏览器；运行期 `playwright install` 属预期收紧，写入文档（P3）。
6. **不扩大回归面**：`backend`/`ai-gateway` 不加 `read_only`（不执行用户代码）。
7. **S3 egress / S4 每任务容器不做**：需生产网络拓扑与被测站点白名单，且会改动调度/预算/取消语义；拆为 C256-1 / C256-2，写明解除条件。
8. **可选 peer 必须显式 override**：`@puppeteer/browsers@3.2.2` 声明可选 peer `proxy-agent >=8.0.1`。npm 11 在已有 lockfile 上增量解析**不会**写入该 peer，而 CI/npm 10 的 `npm ci` 会因此 EUSAGE 直接失败（QA 在合入前用 `node:22.22-alpine` 复现）。修复为显式 `overrides.proxy-agent = ^8.0.2`；**手工把缺失闭包并回 lockfile 的做法被判为不可接受**（下一次 `npm install` 会被重写），故要求以"显式 override + 与 CI 同版本 npm 的 `npm ci` 验证"作为唯一放行方式。
9. **风险 override 必须有真实运行证据**：`proxy-agent` 同时是 LHCI 自身的依赖，跨主版本（6→8）存在运行期风险；本轮以真实 `npm run lighthouse:a11y`（accessibility=1.0）排除，而不是只跑 `npm audit`。

## 抽检通过

- ✅ `test-platform-v2/frontend/package.json` — overrides 仅新增 4 项，未动 `@lhci/cli`/`lighthouse` 主版本
- ✅ `test-platform-v2/frontend/npm-audit-baseline.json` — advisories 16 → **0**；`NPM_AUDIT_RATCHET=PASS`
- ✅ `test-platform-v2/deploy/docker-compose.yml` — runner/aitde-worker 显式 `user`/`cap_drop`/`security_opt`/`read_only`/`tmpfs`；`docker compose config` 在 base 与 overlay+profile 两种拓扑下均渲染出预期值（见 QA 报告表）
- ✅ `test-platform-v2/backend/tests/test_deploy_compose_contract.py` — 新增只读白名单断言 + overlay 单例列表回归；`test_existing_volumes_receive_the_runtime_uid_before_backend_starts` 按新设计更新（**这是有意的设计变更，已在 PRD §3/Design §2 记录**）
- ✅ `work-logs/evidence/batch-256/read-only-runner-probe.log` — 只读容器内 `APP_WRITE=blocked: Read-only file system`、`PLAYWRIGHT_STATS=expected=1 unexpected=0`
- ✅ lockfile ↔ CI 一致性 — `node:22.22-alpine npm ci` 退出码 0（`added 828 packages`）；`docker build --target build` 退出码 0（`npm ci` + `✓ built in 10.49s`）
- ✅ 硬门禁 — `ruff F821` 通过、`import app.main` OK、Alembic 单头、`pytest tests/test_deploy_compose_contract.py tests/aitde/v34 -q` 79 passed、`vitest 164 files/710 tests`、`npm run build ✓ built in 10.32s`、`dev-gate GATE_RESULT=PASS_WITH_WARN`（HARD=0，WARN 为既有基线且无一落在本批文件）
- ✅ `audit-cconditions.ps1` — hard errors 0 / warnings 0 / closed rows missing evidence 0
- ⏳ PR required checks — 尚未运行（需先取得用户一次总确认后 push + 建 Draft PR）

## 判决

**有条件通过。** 代码、工件与本地硬门禁已达合入前标准；以下为放行条件，未完成前不得 squash 合入 main：

1. 用户一次总确认：确认推送 `feature/batch-256-runner-isolation-and-audit`、创建 Draft PR，并在 required checks 通过后合并到 `main`；
2. `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex` 基础审计通过；
3. required checks 全绿后 `audit-ai-pr.ps1 ... -RequireSuccessfulChecks` 通过，Leader 才最终 APPROVED、转 Ready 并 squash 合入。

打回项：无。

## 下一批次 Leader 条件

- `C256-1`（P2）：执行面 egress 白名单（专用 network + `internal: true` 或主机层 nftables/iptables），含被测站点/蓝湖/Test5 内网白名单与不可达时的明确报错；解除条件=白名单内可达 + 白名单外被拒的双向证据。
- `C256-2`（P2）：单任务一次性容器隔离形态决策与 PoC，含并发=1 预算与取消/超时语义回归。
- 保留 `C243-1`（P2，In-Progress）：仅剩 S3/S4 两项，已由 C256-1/C256-2 承接，两者关闭后同步关闭。

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| 侦察文档把 runner 的 `cap_drop` 判为缺失，实测是继承自 base `backend`；真正的缺口是 aitde-worker 缺 `security_opt` | 以 `docker compose config` 有效配置为准复核；把该教训写成设计走查 P1-1 | `work-logs/batch-256-runner-isolation-and-audit-design-spec.md:4.x` |
| overlay 与 base 同值声明单例列表（security_opt/cap_drop/tmpfs）会让 compose 直接校验失败（Batch 243 已踩一次） | 新增回归测试 + 坑位文档条目 | `test_deploy_compose_contract.py::test_execution_overlay_never_redeclares_singleton_list_fields`、`docs/common-pitfalls.md` 7.10 |
| 本机 `npm audit` 默认打 npmmirror，返回"无漏洞"假象 | 写入坑位文档并要求所有调用点显式 `--registry` | `docs/common-pitfalls.md` 7.9 |
| 只读 rootfs 的可写点清单此前只存在于个人经验 | 固化到部署文档并新增运行探针脚本 | `deploy/README.md`「执行面只读 rootfs 与可写白名单」、`work-logs/evidence/batch-256/read-only-runner-probe.sh`、`docs/common-pitfalls.md` 7.11 |
| 宿主内存/WSL 页缓存会导致构建与 buildkit 随机 OOM，容易被误读为代码回归 | 写入 QA 报告 §6，并给出释放 WSL 页缓存的可执行命令 | `work-logs/batch-256-runner-isolation-and-audit-qa-report.md` §6 |
| 本机 `npm ci` 因 esbuild 平台可选包缺失而失败（基线同样失败） | 记录为环境问题，验证改用同 lockfile 的 `npm install`，并在 CI 由干净 Linux runner 跑 `npm ci` | 同上 §6.1 |

> 本批未修改 `SKILL.md`/`DEPARTMENTS.md`，故不触发 `CHANGELOG.md` 更新。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 6h 计划 / 约 8h 实际 | 0/1/0/3 | 3 | 工具链 + 外部依赖（宿主内存/WSL 页缓存；本机 npm ci 可选包缺失；npm 11 与 npm 10 的可选 peer 解析差异） | 依赖类批次在改 lockfile 后**先跑与 CI 同版本 npm 的 `npm ci`**（`node:22.22-alpine` 容器）再进入前端门禁，避免把"本机能装"当作"CI 能装" |

**技能使用**: `cameltv-agent-team`（流水线）、`cameltv-bug-guard`（Dev 自检）、`cameltv-deploy`（文档同步）→ 结论均已落入工件与门禁记录（非测试证据）。
