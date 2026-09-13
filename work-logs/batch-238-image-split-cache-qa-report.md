# Batch 238 — 镜像拆分与包体缓存优化（Phase 4）— QA 报告
> **QA (🔍)** | Date: 2026-09-13 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 | 7 | 0 | 0 |

## 可执行门禁

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端全量 | `python -m pytest -q` | 0 | **2672 passed, 11 skipped, 1 xfailed**, 691.47s（lanhu 子模块已初始化） |
| 后端 F821 | `ruff check app/ --select F821` | 0 | All checks passed |
| 镜像/部署契约 | `pytest tests/test_deploy_compose_contract.py tests/test_image_split_cache_contract.py -q` | 0 | 16 passed |
| 前端类型 | `npm run typecheck` | 0 | PASS |
| 前端 lint | `npm run lint` | 0 | PASS |
| 前端构建 | `npm run build` | 0 | 3671 modules transformed；11.17s |
| Dev Gate | `pwsh scripts/git/dev-gate.ps1` | 2 | `PASS_WITH_WARN`：HARD=0，G1/G2 PASS |
| WARN 审计 | `run-warn-audit.ps1 -NoTrendAppend` | 2 | Batch 238 新增文件无告警；剩余为 main 既有漂移 |

## 逐条件验证

### C1: API/runner target 分离
`test_backend_dockerfile_has_light_api_and_heavy_runtime_targets` PASS。API 段无 Node/Playwright；runner 段保留重型运行时。

### C2: Split Compose overlay
`test_opt_in_execution_overlay_uses_split_targets` PASS。backend/volume-permissions→api，runner/aitde-worker→runner。

### C3: BuildKit cache mount
`test_buildkit_cache_mounts_are_wired` PASS。backend pip/npm cache mount 3 处，frontend npm cache mount 1 处。

### C4: 镜像基线采集
`scripts/deploy/collect-image-baseline.ps1` 可执行；本机 Docker daemon 未启动时明确记录 `docker_available=false`，不伪造实时大小。历史真实基线已引用到 `work-logs/evidence/batch-238-image-split-cache/README.md`。

### C5: 前端重型 chunk
build 输出生成 `vendor-charts` 402.69 kB、`vendor-graph` 520.50 kB、`vendor-mindmap` 664.33 kB；避免依赖变化导致主 chunk 全量失效。

### C6: SPA HTTP 缓存
`test_frontend_heavy_chunks_and_spa_shell_cache_policy` PASS。`index.html` no-store；assets immutable。

### C7: 默认行为与回滚
Split 仅通过 opt-in `docker-compose.execution.yml` 启用；默认 combined `runtime` 保持不变。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| - | - | 无阻断缺陷 | 全量门禁通过 | - |

## 发布建议

状态: **READY（本地门禁）**  
必修复: 0  
建议修复: 0  

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 本会话完成 | 0/0/0/0 | 0 | - | Docker host 可用时复采实际镜像大小 |

**技能使用**: `cameltv-agent-team` → 工件与门禁；`cameltv-bug-guard` → Dockerfile/Compose/缓存边界核查。
