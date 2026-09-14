# Batch 242 — Design 技术规范
> **Design (🎨)** | Date: 2026-09-14 | Status: Approved

## 1. 依赖装配目标态

```
requirements.txt ─────────────┐
                              ├─> requirements.lock        （完整基线 / 约束源）
requirements.api.txt ─────────┤      │
requirements.ai.txt  = api+AI ├──────┼─> requirements.api.lock     → builder-api    → api
requirements.runner.txt = ai+playwright ─> requirements.ai.lock     → builder-ai      → ai-gateway
                                     └─> requirements.runner.lock → builder-runner  → runner/runtime
```

- 三个 target 各自消费自己的 lock，**无交叉引用**。
- `requirements.lock` 仍作为 `--constraint` 源（生成三套锁）与
  `pr-check.yml` / `Dockerfile.local` / 文档基线，不再被 Docker target 安装。
- `requirements.runner.lock` 与 `requirements.lock` 当前版本集合一致，
  因此本批是**装配收口**而非依赖变更。

## 2. Dockerfile 变更

| 项 | 前 | 后 |
|----|----|----|
| 阶段名 | `builder` | `builder-runner` |
| COPY | `requirements.txt` + `requirements.lock` | `requirements.runner.txt` + `requirements.runner.lock` |
| 安装 | `-r requirements.lock` | `-r requirements.runner.lock` |
| 下游 | `COPY --from=builder` | `COPY --from=builder-runner` |

命名与 `builder-api` / `builder-ai` 对齐，使「阶段名 → 角色 → 锁」一一对应。

## 3. CI 门禁设计（`main-quality-gate.yml` 后端 required job）

required context 名固定为 `后端全新检出与全量回归`（分支未启用 GitHub
protection，required 语义由 `scripts/git/audit-ai-pr.ps1` 按三个固定 context 校验），
因此门禁**必须并入该 job**，不能新增 job。

新增两步，均不带 `continue-on-error`：

| 步骤 | 命令 | 拦截的缺陷类 |
|------|------|-------------|
| 依赖锁 Linux 解析校验 | `pip install --dry-run --require-hashes --ignore-installed -r <lock>`（×3） | 平台标记解析错误、hash 缺失/不匹配、传递依赖未 pin |
| API 镜像构建冒烟 | `docker build --target api -t cameltv-tp-api:ci-gate -f test-platform-v2/backend/Dockerfile .` | Dockerfile 契约、COPY 路径、镜像可构建性 |

选型理由：

- `--dry-run` **必须不带 `--no-deps`**：`--no-deps` 会跳过依赖解析，
  恰好漏掉 Batch 240 的失败模式（`keyring` 声明 `SecretStorage>=3.2` 但未 pin）。
- `--ignore-installed` 防止 runner 上已装的包让检查短路为「已满足」。
- 只构建 `api` target：最轻（112.6 MiB）、覆盖 api lock 端到端；
  ai/runner lock 由解析校验覆盖，避免每次 PR 下载 Playwright/Chromium。

job `timeout-minutes` 15 → 30（原 job 实测 ~14 分钟，新增约 5–6 分钟）。

## 4. 门禁契约测试

`scripts/ci/test_batch59_quality_contracts.py` 新增
`BackendImageGateContractTests`：断言后端 job 含上述两步、无 `continue-on-error`、
无 `|| true` 旁路，且 timeout ≥ 25。

并把该文件接入 `ai-delivery-policy.yml`（此前**未被任何 workflow 执行**），
同时修正其陈旧断言 `backend_tests` → `backend-clean-checkout`。

## 5. 回滚

- 代码回滚：revert 本批提交即可（纯配置/测试，无数据迁移）。
- 运行影响：无；两个 target 的依赖版本集合未变。
