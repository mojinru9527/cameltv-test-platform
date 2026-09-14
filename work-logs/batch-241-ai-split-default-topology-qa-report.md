# Batch 241 — QA 报告
> **QA (🔍)** | Date: 2026-09-14 | Scope: test-platform-v2/deploy + backend deps + release-console

## 1. 结论

**PASS**。默认 split 拓扑在真实 Docker host 跑通 API→AI Gateway→runner 全链路，
fail-closed 与 combined 回滚均经验证；并发现并修复了 Batch 240 遗留的 **P0 构建阻断**。

## 2. 变更范围

| 域 | 文件 |
|----|------|
| 依赖锁 | `backend/requirements.{api,ai,runner}.lock` |
| AI Gateway | `backend/app/ai_gateway_app.py` |
| Compose | `deploy/docker-compose.yml`、`deploy/docker-compose.combined.yml`（新） |
| 发布控制面 | `deploy/release-console/{app,capacity,release_artifacts,tencent_executor}.py` + tests |
| 运维脚本 | `scripts/ops/smoke_ai_split_topology.py`（新） |
| 契约测试 | `backend/tests/test_split_default_topology_contract.py`（新） |

## 3. 门禁结果

| 检查 | 命令 | 结果 |
|------|------|------|
| Ruff F821 | `ruff check app/ --select F821` | ✅ All checks passed |
| Dev Gate G0–G2 | `scripts/git/dev-gate.ps1` | ✅ PASS_WITH_WARN（HARD=0） |
| 前端 typecheck | `npm run typecheck` | ✅ exit=0 |
| 前端 lint | `npm run lint` | ✅ exit=0 |
| 路由层守卫 | G2 内置 | ✅ 4 passed |
| 新增拓扑契约 | `pytest tests/test_split_default_topology_contract.py` | ✅ 12 passed |
| 发布控制面 | `pytest deploy/release-console -q` | ✅ 37 passed, 2 subtests passed |
| 后端全量回归 | `pytest -q`（子模块已初始化） | ✅ 2693 passed, 11 skipped, 1 xfailed, 0 failed |
| 真机 Docker smoke | `python scripts/ops/smoke_ai_split_topology.py` | ✅ result=passed |

## 4. 真机验收证据（C239-2 / C240-1）

原始 JSON：`work-logs/evidence/batch-241-ai-split-smoke.json`

```json
{"result": "passed",
 "images": {"api": 118112389, "ai-gateway": 179363765, "runner": 1400878589},
 "chain": {"api_health": true, "gateway_health": true, "runner_health": true,
           "api_to_gateway_anonymous_rejected": 401},
 "fail_closed": {"missing_token_blocks_split_rendering": true,
                 "gateway_unhealthy_without_token": true},
 "image_boundaries": {"api_excludes": ["fastembed","onnxruntime","numpy","playwright"],
                      "gateway_includes": ["fastembed","onnxruntime","numpy"],
                      "gateway_excludes": ["playwright"]},
 "combined_rollback": {"backend_target": "runtime"}}
```

### 4.1 C240-1 镜像体积

| 镜像 | 压缩体积 | 磁盘占用 | rootfs 层 |
|------|---------|---------|-----------|
| `api` | **112.6 MiB** | 533 MB | 12 |
| `ai-gateway` | 171.1 MiB | 787 MB | 8 |
| `runner`（= combined `runtime` 基线） | 1336.0 MiB | 5.37 GB | 18 |

- **API 镜像体积下降 91.6%**（1336.0 → 112.6 MiB）。
- 共享层：api∩gateway = 4 层，api∩runner = 4 层，gateway∩runner = 5 层。
- `runtime` 是 `runner` 的空别名 stage（Dockerfile 末尾 `FROM runner AS runtime` 后无指令），
  故以 runner 作为 combined 基线是等价的。

### 4.2 镜像边界直测（容器内 import 探测）

| 断言 | 结果 |
|------|------|
| api 不含 fastembed / onnxruntime / numpy / playwright | ✅ |
| ai-gateway 含 fastembed / onnxruntime / numpy | ✅ |
| ai-gateway 不含 playwright | ✅ |

### 4.3 全链路

| 环节 | 结果 |
|------|------|
| api `/health` | 200 |
| ai-gateway `/internal/ai/v1/health`（带 token） | 200 |
| runner `/health` | 200 |
| api→ai-gateway 匿名调用 `/internal/ai/v1/embed` | **401**（鉴权生效） |

### 4.4 Fail-closed（C239-3）

| 场景 | 期望 | 实测 |
|------|------|------|
| 缺 `AI_GATEWAY_TOKEN` 渲染 split 发布 overlay | 失败 | ✅ 非零退出 |
| 缺 `AI_GATEWAY_TOKEN` 渲染 combined 回滚 overlay | 成功 | ✅ 通过 |
| 网关无 token 时 `/internal/ai/v1/health` | 503 | ✅ 503 |

## 5. 发现与修复

### P0 — Batch 240 遗留：三套 lock 无法在 Linux 安装

- **现象**：`docker build --target api` 在 `builder-api` 阶段失败：
  `ERROR: In --require-hashes mode, all requirements must have their versions pinned with ==.
  These do not: SecretStorage>=3.2 (from keyring==25.7.0)`。
- **根因**：三套 lock 在 **Windows** 上用 `pip-compile` 生成，平台标记按 win32 解析，
  丢失 `secretstorage` / `jeepney`（linux）与 `uvloop`（非 win32）。
  基准 `requirements.lock` 是通用锁（同时含 uvloop 与 pywin32），三套新 lock 不具备该性质。
- **影响**：`api` 与 `ai-gateway` target **完全无法构建**，C239-2 的「默认切 split」
  在此之前不可能达成。CI 未拦截是因为 required 后端 job 只跑 pytest，不构建镜像。
- **修复**：从 Linux 解析结果补齐 3 个包块，三文件各 +66/-0 行；已由真机构建验证。
- **追踪**：C241-1（新增）。

### P1 — 网关健康检查在无 token 时仍返回 200

- **现象**：`ai_gateway_token` 为空时 `/internal/ai/v1/health` 返回 200，
  compose `--wait` 会把无 token 的网关判为健康。
- **修复**：health 在 token 缺失时返回 503，容器级 fail-closed 成立。
- **追踪**：C239-3 关闭依据之一。

### P2 — `requirements.runner.lock` 未被 Dockerfile 引用

- `runtime-base` 复制 `builder`（`requirements.lock`）的 venv；`runner` target 继承之，
  `requirements.runner.lock` 目前是**死文件**。本批已同步修复其 linux 依赖，但
  是否改为真正引用需单独决策。
- **追踪**：C241-2（新增）。

## 6. 全量回归

```
cd test-platform-v2/backend && python -m pytest -q
```
（结果见 §6.1；与基线对比确认无新增失败）

### 6.1 结果

```
cd test-platform-v2/backend && python -m pytest -q
==== 2693 passed, 11 skipped, 1 xfailed, 62 warnings in 656.00s (0:10:56) ====
```

基线对比：

| 运行 | passed | skipped | xfailed | failed |
|------|--------|---------|---------|--------|
| Batch 240 基线（合并 main） | 2681 | 11 | 1 | 0 |
| Batch 241（含新增 12 项拓扑契约） | 2693 | 11 | 1 | 0 |

2693 − 2681 = 12，恰为本批新增的 `test_split_default_topology_contract.py` 用例数，
**无新增失败、无既有用例转失败**。

补充：首次本地全量运行时 `lanhu-mcp` 子模块未初始化，51 项被 skip（含
`test_deploy_compose_contract.py` 的模块级 skipif）。执行
`git submodule update --init --depth 1 lanhu-mcp` 后重跑，最终如上；
期间修正了该文件一处旧契约断言（`backend.build` 现含 `target: api`）。

## 7. 残余风险

| 风险 | 说明 | 处置 |
|------|------|------|
| 默认拓扑切换未经生产验证 | 本批验收在本地真实 Docker host（Windows Docker Desktop / linux 容器）完成，非腾讯云生产 | 发布走 release 火车；回滚 = 叠加 `docker-compose.combined.yml` |
| `docker compose` 组合语义依赖 `!reset` | 需 Compose v2.24+ | CI 与发布主机均为 v2.4x；契约测试覆盖 |
| 主机资源 | 本机 16GB/固定 8GB 页面文件，构建期曾触发 CLI OOM | smoke 已改为 `--no-build` 复用镜像；CI runner 内存更充裕 |
