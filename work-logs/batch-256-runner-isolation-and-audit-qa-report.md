# Batch 256 — QA 报告
> **QA (🔍)** | Date: 2026-09-18 | Verdict: PASS（含 2 项环境限制记录，见 §6）

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 2（C246-1 / C243-1 S1+S2） | 2 | 0 | 0 |

## 可执行门禁（命令 / 退出码 / 日志摘要）

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:------:|------|
| 后端 F821 | `python -m ruff check app/ --select F821` | 0 | `All checks passed!` |
| 后端导入 | `python -c "import app.main"` | 0 | `APP_IMPORT_OK` |
| Alembic 单头 | `python -m alembic heads` | 0 | 1 个 head（`20260922_ai_agent_token`） |
| 受影响后端测试 | `pytest tests/test_deploy_compose_contract.py tests/aitde/v34 -q` | 0 | **79 passed** |
| 前端类型 | `npm run typecheck` | 0 | `tsc -b` 无输出 |
| 前端 lint | `npm run lint` | 0 | `eslint . --max-warnings=0` |
| 前端单测 | `npx vitest run --reporter=dot --pool=forks --maxWorkers=2` | 0 | **164 files / 710 tests passed**（112.85s） |
| 前端构建 | `npm run build` | 0 | `✓ built in 10.32s` |
| a11y 门禁（真实 LHCI） | `npm run lighthouse:a11y` | 0 | `Run #1...done.`；**accessibility = 1.0**；lighthouse 12.6.1 |
| lockfile ↔ CI npm 一致性 | `docker run --rm -v <fe>:/src -w /src node:22.22-alpine npm ci` | 0 | `added 828 packages`（npm 10.9.8，与 CI/镜像同版本） |
| 前端镜像构建 | `docker build --target build -f Dockerfile .` | 0 | `npm ci` 828 packages + `✓ built in 10.49s` |
| 完整审计 ratchet | `node scripts/ci/npm_audit_ratchet.mjs` | 0 | `baseline=0 current=0 new=0` → `NPM_AUDIT_RATCHET=PASS` |
| 生产依赖审计 | `npm audit --omit=dev --audit-level=high --registry=https://registry.npmjs.org` | 0 | `found 0 vulnerabilities` |
| 开发门禁 | `pwsh scripts/git/dev-gate.ps1` | 2 | `GATE_RESULT=PASS_WITH_WARN`（HARD=0；WARN=332 为既有基线，**无一条落在本批改动文件**；G1 全 exit=0；G2 路由守卫 4 passed） |

### compose 有效配置断言（`docker compose config --format json`）

| 服务 | user | cap_drop | read_only | tmpfs | no-new-privileges | volumes |
|------|------|----------|:---------:|-------|:-----------------:|---------|
| `runner`（base 与 overlay 均验） | `10001:10001` | `ALL` | `true` | `/tmp`、`/home/cameltv/.cache`、`/home/cameltv/.npm` | ✅ | data/artifacts/generated-specs/generated-jobs |
| `aitde-worker`（base 与 overlay+profile 均验） | `10001:10001` | `ALL` | `true` | 同上 | ✅ | 同上 |
| `backend`（对照组，本批不改） | — | `ALL` | 未设置 | — | 未设置（base 无） | 保持原样 |

## 逐条件验证

### C246-1：消除 dev-only npm audit（7 high / 1 moderate / 2 low）

**变更文件**: `frontend/package.json`（overrides）、`frontend/package-lock.json`、`frontend/npm-audit-baseline.json`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 审计实测（改前） | ✅ 基线 | `high=7 moderate=1 low=2 total=10`；全部经 `@lhci/cli` 传导 |
| 审计实测（改后） | ✅ | `{"info":0,"low":0,"moderate":0,"high":0,"critical":0,"total":0}` |
| 无修复版 advisory 的处理 | ✅ | `extract-zip`（区间 `*`，无修复版）**从依赖树移除**：`overrides` 把 `puppeteer-core` → `^25.11.0`、`@puppeteer/browsers` → `^3.2.2`（3.x 用 `modern-tar` 取代 `extract-zip`）；`tmp`→`0.2.7`、`uuid`→`^11.1.1` |
| 可选 peer 收口（发现并修复的阻断缺陷） | ✅ | `@puppeteer/browsers@3.2.2` 声明可选 peer `proxy-agent >=8.0.1`：npm 11 增量解析不写该 peer，而 CI/npm 10 的 `npm ci` 会 EUSAGE（`Missing: proxy-agent@8.0.2 ...`）。修复=显式 override `proxy-agent: ^8.0.2`（持久有效；手工并回 lockfile 会被下一次 `npm install` 丢弃） |
| 该缺陷的证据 | ✅ | 修复前 `node:22.22-alpine npm ci` → `EUSAGE Missing: proxy-agent@8.0.2 / quickjs-wasi@2.2.0 ...`；修复后同一命令 → `added 828 packages` 退出码 0（见上表两行） |
| 不靠降级 | ✅ | 未使用 npm 建议的 `@lhci/cli@0.6.1`（降级）；`@lhci/cli` 保持 `^0.15.1`、`lighthouse` 保持 12.6.1 |
| a11y 门禁未回归 | ✅ | 真实 `npm run lighthouse:a11y` 退出码 0，accessibility=1.0，报告 lighthouseVersion=12.6.1（证明 override 的 puppeteer-core 25 / proxy-agent 8 与 LHCI 12.6.1 实际可协同；LHCI 自身依赖 proxy-agent，该 override 属高风险点，已用真实运行排除） |
| ratchet 收紧 | ✅ | baseline advisories 由 16 条降为 **0 条**；新增任何 advisory 会立即失败 |
| 审计调用点带 registry | ✅ | `.github/workflows/{main-quality-gate,main-merge-smoke,pr-check}.yml`、`scripts/ci/npm_audit_ratchet.mjs`、`scripts/git/dev-gate.ps1`、`frontend/README.md` 均已显式 `--registry=https://registry.npmjs.org` |
| 生产依赖仍为 0 | ✅ | `npm audit --omit=dev` → 0 |

**✅ PASS**

### C243-1（本批范围 S1+S2）：执行面容器隔离与只读 rootfs

**变更文件**: `deploy/docker-compose.yml`、`tests/test_deploy_compose_contract.py`、`tests/aitde/v34/test_managed_worker_deploy_contract.py`、`deploy/README.md`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 缺口实测（改前） | ✅ 基线 | `runner` 有 `cap_drop: ALL`/`no-new-privileges`（继承 backend）但**无 `read_only`/`tmpfs`**；`aitde-worker` 有 `cap_drop` 但**缺 `security_opt`** |
| 只读 rootfs | ✅ | base 与 overlay 渲染结果 `read_only: true` |
| 显式最小权限 | ✅ | 两个服务显式 `user: 10001:10001`、`cap_drop: [ALL]`、`security_opt: [no-new-privileges:true]`（不再只靠 `extends` 继承） |
| 可写白名单 | ✅ | tmpfs：`/tmp`（含 `WORKER_RUNTIME_DIR=/tmp/aitde-worker` 的 pid 文件）、`/home/cameltv/.cache`、`/home/cameltv/.npm`；卷：`/app/storage`、`/data`、生成 spec/job 两目录 |
| overlay 合并合法 | ✅ | `docker compose -f docker-compose.yml -f docker-compose.execution.yml --profile aitde-worker config` 退出码 0；新增回归测试禁止在 base/overlay 重复声明 `security_opt`/`cap_drop`/`tmpfs`（Batch 243 曾因重复 `security_opt` 失败） |
| TDD 红 | ✅ | 暂行 base compose 改动后：`test_managed_worker_carries_the_execution_plane_hardening` → `KeyError: 'read_only'`（1 failed） |
| TDD 绿 | ✅ | 恢复后 19 passed；合并 overlay 渲染断言通过 |
| 真实运行探针（只读 rootfs） | ✅ | 见下 |

**真实探针证据**（`work-logs/evidence/batch-256/read-only-runner-probe.log`）：

```
ROOTFS=overlay ro,relatime,...
APP_WRITE=blocked: /app/ro-probe.txt: Read-only file system
TMP_WRITE=ok / STORAGE_WRITE=ok / GENERATED_SPEC_WRITE=ok
PLAYWRIGHT_EXIT=0
PLAYWRIGHT_STATS=expected=1 unexpected=0 flaky=0 skipped=0
```

即：只读 rootfs + tmpfs 白名单 + `cap_drop ALL` + `no-new-privileges` + 非 root 下，
平台真实执行路径 `npx playwright test --project chromium` **成功启动浏览器并跑过用例**；
镜像路径写入被内核拒绝（EROFS）。

**✅ PASS（S1+S2）**；S3（egress 白名单）与 S4（每任务一次性容器）不在本批范围，已转为 C256-1 / C256-2。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| 1 | P3 | `/ms-playwright` 只读后，运行期 `playwright install` 新浏览器版本会失败（现有任务是构建期预置浏览器，不受影响） | `deploy/README.md` 白名单表；探针内浏览器来自镜像 | 已文档化（接受） |
| 2 | P3 | base 拓扑原先不共享生成 spec/job 目录（backend 写入、runner 不可见），本批统一为与 overlay 相同的命名卷 | `docker-compose.yml` volumes 对比改前渲染 | 已修复（本批） |
| 3 | P3 | 本机 `npm ci` 因 esbuild 平台包缺失失败（详见 §6），`npm install` 可替代 | 基线 main 同样失败 | 环境问题（非回归） |
| 4 | P1（已修复） | lockfile 与 CI 的 npm 10 不同步：`@puppeteer/browsers@3.2.2` 的可选 peer `proxy-agent>=8.0.1` 未被 npm 11 增量写入 lockfile，CI `npm ci` 会直接失败 | `node:22.22-alpine npm ci` 修复前 EUSAGE / 修复后 exit 0 | ✅ 已修复（显式 override `proxy-agent: ^8.0.2`），并写入 `docs/common-pitfalls.md` 7.12 |

**P0：0 ｜ P1：1（#4，已修复并以 npm 10 `npm ci` + 前端镜像构建复验）｜ P2：0 ｜ P3：3（记录/文档化）。**

## 发布建议

状态: **READY**（P1 缺陷已修复并复验；可进入一次总确认 → Draft PR → required checks）
必修复: 0 建议修复: 0（P3 已记录/文档化）

## CI 分层核对

本批变更范围：`test-platform-v2/frontend/**`、`test-platform-v2/deploy/**`、`test-platform-v2/backend/tests/**`、`docs/**`、`work-logs/**`。
按 `main-quality-gate.yml` 的分类契约：前端域（package.json/lock/baseline）→ 前端 required；`deploy/**` 属部署定义 → 由 `ai-delivery-policy.yml` 做 YAML 校验与 release-control 冒烟；backend `tests/**` → 后端 required；`docs/**`、`work-logs/**` → 文档类跳过重测试但 required contexts 仍返回结果。
本批**未**依赖 skipped job 推断质量：上述命令均已在本地真实执行并记录退出码。

## 复盘卡（Batch 75 起强制）

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 6h 计划 / 约 7h 实际 | 0/0/0/3 | 2（overlay 重复 `security_opt` 校验失败、宿主内存导致构建失败重试） | 工具链 + 外部依赖（宿主内存/WSL 页缓存） | 重工具型批次开工前先 `docker run --privileged --pid=host alpine sh -c "sync; echo 3 > /proc/sys/vm/drop_caches"` 释放 WSL 页缓存，再跑构建/构建型验证 |

## 技能使用

- `cameltv-bug-guard` → 用于 Dev 切片自检项（依赖/配置类避坑），结论已并入上表门禁。
- `cameltv-deploy` → 触发部署文档同步（`deploy/README.md` 增加只读 rootfs 白名单与探针）。
- 说明：技能仅作补充检查，不作为测试证据；上表所有结论均来自真实命令输出。

## 6. 环境限制记录（必须诚实披露，不掩盖）

1. **`npm ci` 在本机失败**：`npm error path .../node_modules/esbuild` + `@esbuild/win32-x64/esbuild.exe` 缺失。
   在**未改动的 main 工作树**上执行 `npm ci` 得到**完全相同**的失败（`BASELINE_NPM_CI_EXIT=1`，平台包同样缺失），
   故与本批 overrides 无关，属本机 npm/宿主环境问题。本批前端验证改用同 lockfile 的 `npm install`（828 packages）完成，
   CI 仍在干净 Linux runner 上执行 `npm ci`（本批 Docker 构建路径也使用 `npm ci`）。
2. **宿主内存不足**：本机 commit 逼近上限（23.9/24.4 GB），首次 `npm run build`、`docker build` 均报
   `fatal error: out of memory` / buildkit `cannot allocate memory`。释放 WSL 页缓存（VM 内 `buff/cache` 5.8 GB → 0.4 GB）后
   `npm run build` 与 LHCI 均一次通过；`vitest` 以 `--pool=forks --maxWorkers=2` 运行以避免 OOM。
   该限制与代码无关，但会导致"未经处理的构建失败"被误判为回归，故记录。
