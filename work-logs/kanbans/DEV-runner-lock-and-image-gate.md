# Batch 242 Dev Kanban — Runner 依赖锁收口与镜像构建门禁
> **Dev (💻)** | Date: 2026-09-14 | Status: In Review

## 切片

| # | 切片 | 文件 | 状态 |
|---|------|------|------|
| S1 | runner/combined 阶段改用 `requirements.runner.lock` | `backend/Dockerfile` | ✅ |
| S2 | 后端 required job 增加 lock Linux 解析校验 | `.github/workflows/main-quality-gate.yml` | ✅ |
| S3 | 后端 required job 增加 `api` 镜像构建冒烟 | 同上 | ✅ |
| S4 | 修复并接入门禁契约测试 | `scripts/ci/test_batch59_quality_contracts.py`、`.github/workflows/ai-delivery-policy.yml` | ✅ |
| S5 | 契约断言补齐 | `backend/tests/test_deploy_compose_contract.py`、`scripts/ci/test_batch59_quality_contracts.py` | ✅ |

## 关键实现记录

### S1 为什么是「收口」而不是「换锁」
`requirements.lock` 与 `requirements.runner.lock` 经比对：

| 维度 | 结果 |
|------|------|
| 包集合 | 完全相同（119 vs 119） |
| 版本 pin | 0 处差异 |
| 差异 | 仅头注释与 `# via` 注解 |

因此把 `builder` 改名为 `builder-runner` 并改用 `requirements.runner.lock`，
在依赖层面是**零漂移**；收益是消除「ADR 声明用 runner.lock，Dockerfile 实际用
requirements.lock」的双真相。

### S2/S3 为什么并入既有 job 而不是新增 job
`gh api .../branches/main/protection` 返回 **Branch not protected**（404）。
required 语义由 `scripts/git/audit-ai-pr.ps1` 按三个固定 context 名校验，
新增 job 只是多一个普通 check、**不会成为门禁**。所以两步必须并入
`backend-clean-checkout`。

`--dry-run` 特意**不加 `--no-deps`**：`--no-deps` 会跳过依赖解析，
恰好绕过 Batch 240 的失败模式（`keyring` 声明 `SecretStorage>=3.2` 未 pin）。

### S4 发现：门禁契约测试是死的
`scripts/ci/test_batch59_quality_contracts.py` 未被任何 workflow 引用，
且 `test_required_gate_runs_postgresql_concurrency_regressions` 断言
job 名 `backend_tests`（早已改名为 `backend-clean-checkout`）→ 本地必失败。
即：门禁契约测试本身已腐化，无法防护。本批修正 job id 并接入
`ai-delivery-policy.yml`。

## 阻塞与决策

| 项 | 决策 / 结论 |
|----|------------|
| `docker build --target runner` 两次在 `pip install -r requirements.runner.lock` 失败于 `hf-xet==1.5.2` hash 不匹配 | **非代码缺陷**。同一 lock 在干净容器 `pip install --require-hashes` 119 包全部通过、`import fastembed/onnxruntime/numpy/playwright` 正常；直接 `pip download` 得到的 wheel hash `db78c39c…` 也在锁内。判定为 **buildkit 共享 pip cache 中的损坏 wheel**（Batch 241 资源耗尽时被强杀的构建遗留）。处置：`docker buildx prune -a` 后冷缓存重建复验。 |
| 是否顺带把 `Dockerfile.local` 也切到 runner lock | **否**。`Dockerfile.local` 是本地全量开发镜像，继续用完整 `requirements.lock` 更直观；记入 ADR 说明避免再次被误判为漂移。 |
