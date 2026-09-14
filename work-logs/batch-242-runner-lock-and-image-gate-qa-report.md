# Batch 242 — QA 报告
> **QA (🔍)** | Date: 2026-09-14 | Scope: backend Dockerfile / required CI gate / CI contract tests

## 1. 结论

**PASS**。runner 依赖锁完成收口且**零版本漂移**（真机镜像对比 +0.003%）；
required 后端 job 已具备 lock 平台解析校验与 `api` 镜像构建门禁；
一个长期未被执行、且断言已腐化的门禁契约测试被修复并接入 CI。

## 2. 变更范围

| 域 | 文件 |
|----|------|
| 镜像装配 | `backend/Dockerfile`（`builder` → `builder-runner`，改用 `requirements.runner.lock`） |
| CI 门禁 | `.github/workflows/main-quality-gate.yml`（+2 步，timeout 15→30） |
| CI 契约 | `scripts/ci/test_batch59_quality_contracts.py`（修正陈旧断言 + 新增 3 项）、`.github/workflows/ai-delivery-policy.yml`（接入执行） |
| 契约断言 | `backend/tests/test_deploy_compose_contract.py` |
| 文档/条件 | `docs/adr/0031-*.md`、`C-CONDITIONS.md` |

## 3. 门禁结果

| 检查 | 命令 | 结果 |
|------|------|------|
| Ruff F821 | `ruff check app/ --select F821` | ✅ All checks passed |
| Dev Gate G0–G2 | `scripts/git/dev-gate.ps1` | ✅ PASS_WITH_WARN（HARD=0） |
| 前端 typecheck / lint | G1 内置 | ✅ |
| 后端部署契约 | `pytest tests/test_deploy_compose_contract.py tests/test_image_split_cache_contract.py tests/test_split_default_topology_contract.py` | ✅ 29 passed |
| CI 门禁契约 | `pytest scripts/ci/test_batch59_quality_contracts.py scripts/ci/test_classify_ci_changes.py` | ✅ 20 passed, 34 subtests |
| 发布控制面 | `pytest deploy/release-console` | ✅ 37 passed, 2 subtests |
| 后端全量回归 | `pytest -q` | ✅ 2693 passed, 11 skipped, 1 xfailed, 0 failed |
| 真机 lock 安装 | 干净容器 `pip install --require-hashes -r requirements.runner.lock` | ✅ 119 包 + `import fastembed/onnxruntime/numpy/playwright` |
| 真机镜像构建 | `docker build --target runner` | ✅ 构建成功 |

## 4. C241-2 验收证据

### 4.1 收口前的事实核对

| 维度 | `requirements.lock` | `requirements.runner.lock` |
|------|--------------------|---------------------------|
| 包数量 | 119 | 119 |
| 版本 pin 差异 | — | **0** |
| 差异内容 | 头注释 + `# via` 注解 | 同左 |

### 4.2 改后真机验证

| 项 | 结果 |
|----|------|
| `docker build --target runner`（冷缓存，`builder-runner` 装 `requirements.runner.lock`） | ✅ 成功 |
| 镜像体积 | 改前 1,400,878,589 B → 改后 1,400,920,982 B（**+42,393 B = +0.003%**） |
| 关键模块 | `fastembed` / `onnxruntime` / `numpy` / `playwright` / `temporalio` / `fastapi` 全部存在 |
| 版本抽查 | `numpy 2.5.1`、`fastapi 0.140.13`，与改前一致 |

结论：**依赖零漂移**，变化仅是 Dockerfile 阶段命名与所读取的锁文件。

## 5. C241-3 验收证据

### 5.1 门禁并入既有 required job 的判定

`gh api repos/.../branches/main/protection` → **Branch not protected (404)**。
required 语义由 `scripts/git/audit-ai-pr.ps1` 按三个固定 context 名校验，
新增 job 不会自动成为门禁 → 两步并入 `backend-clean-checkout`。

### 5.2 新增门禁的实际拦截能力

| 步骤 | 命令 | 拦截缺陷类 |
|------|------|-----------|
| 依赖锁 Linux 解析校验 | `pip install --dry-run --require-hashes --ignore-installed -r <lock>` ×3 | 平台标记解析错误、传递依赖未 pin、hash 缺失 |
| API 镜像构建冒烟 | `docker build --target api ...`（context=仓库根） | Dockerfile 契约、COPY 路径、镜像可构建性 |

真机复核该命令对本批三个 lock 的实际行为：**三个 lock 全部解析通过**
（`ALL_LOCKS_RESOLVE_ON_LINUX`，约 50s）。

### 5.3 顺带修复：门禁契约测试原本是死的

- `scripts/ci/test_batch59_quality_contracts.py` 未被任何 workflow 引用。
- 其 `test_required_gate_runs_postgresql_concurrency_regressions` 断言 job 名
  `backend_tests`，而该 job 早已改名为 `backend-clean-checkout` → 该测试**必然失败**。
- 本批修正 job id，并把该文件接入 `ai-delivery-policy.yml`
  （`Validate required-gate workflow contracts`）。

## 6. 全量回归

```
cd test-platform-v2/backend && python -m pytest -q
```

### 6.1 结果

```
cd test-platform-v2/backend && python -m pytest -q
==== 2693 passed, 11 skipped, 1 xfailed, 62 warnings in 658.17s (0:10:58) ====
```

基线对比（Batch 241 合入 main 后同一套件）：

| 运行 | passed | skipped | xfailed | failed |
|------|--------|---------|---------|--------|
| Batch 241 基线 | 2693 | 11 | 1 | 0 |
| Batch 242 | 2693 | 11 | 1 | 0 |

**完全一致，无新增失败、无既有用例转失败。**（本批未新增后端用例，
新增断言落在 `scripts/ci/` 与既有契约文件中，已单独在 §3 记录。）

## 7. 调查记录：`hf-xet==1.5.2` 构建 hash 失败（非代码缺陷）

排查过程与结论：

| 观测 | 结论 |
|------|------|
| `docker build --target runner` 两次失败于 `hf-xet==1.5.2` hash 不匹配，报 `Got 8e7faa…` | 现象可复现 |
| 干净容器 `pip download hf-xet==1.5.2` 得到 `db78c39c…`，且该 hash **在锁内** | 锁本身正确 |
| 干净容器 `pip install --require-hashes -r requirements.runner.lock` | ✅ 119 包全部安装成功 |
| `docker buildx prune -a`（释放 37.76GB）后冷缓存重建 | ✅ 构建成功 |

**根因**：buildkit 共享 pip cache 中存在损坏的 `hf_xet-1.5.2…whl`
（Batch 241 主机页面文件耗尽时被强杀的构建遗留半包）。属**本机环境问题**，
与 lock 内容、Dockerfile 改动无关。

**教训**：`--mount=type=cache` 的缓存跨构建共享，被中断的构建可能污染它；
遇到「本地 hash 不匹配但干净环境可复现成功」时应先怀疑构建缓存。

## 8. 残余风险

| 风险 | 说明 | 处置 |
|------|------|------|
| CI 时长上升 | 原 job 约 14 分钟，新增 lock 解析（~1–2 min）与 api 构建（~2–4 min） | timeout 15→30；只构建最轻的 `api` target |
| 冷缓存下 api 构建更慢 | CI runner 无 layer cache | 可观测；超时留有余量 |
| 本地 buildkit cache 仍可能再次污染 | 环境问题 | 已记入上表；必要时 `docker buildx prune -a` |
