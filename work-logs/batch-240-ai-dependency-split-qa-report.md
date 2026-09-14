# Batch 240 — AI/RAG Python 依赖分层 — QA 报告
> **QA (🔍)** | Date: 2026-09-14 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 | 7 | 0 | 0 |

## 可执行门禁

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端全量 | `python -m pytest -q` | 0 | **2681 passed, 11 skipped, 1 xfailed**, 653.26s |
| 部署/镜像契约 | `pytest tests/test_deploy_compose_contract.py tests/test_image_split_cache_contract.py tests/aitde/v34/test_managed_worker_deploy_contract.py -q` | 0 | 21 passed |
| API 干净 venv | 仅安装 `requirements.api.lock` 后 `import app.main` | 0 | `api-lock-clean-ok` |
| 依赖完整性 | `pip check`（API venv） | 0 | No broken requirements |
| 后端 F821 | `ruff check app/ --select F821` | 0 | All checks passed |
| 前端 | `npm run typecheck && npm run lint && npm run build` | 0 | PASS |
| Dev Gate | `pwsh scripts/git/dev-gate.ps1` | 2 | `PASS_WITH_WARN`：HARD=0，G1/G2 PASS |
| WARN 审计 | `run-warn-audit.ps1 -NoTrendAppend` | 2 | Batch 240 新增文件无告警；剩余为 main 既有漂移 |

## 逐条件验证

### C1: API lock 去除 AI/RAG 重依赖
`test_python_dependency_layers_are_split_by_runtime_role` + 干净 venv 断言 PASS：`fastembed/onnxruntime/numpy/playwright` 均不存在。

### C2: AI Gateway lock
`requirements.ai.lock` 含 `fastembed/onnxruntime/numpy`，不含 `playwright`。

### C3: Runner lock
`requirements.runner.lock` 含 FastEmbed/ONNX/NumPy/Playwright 完整运行时。

### C4: 版本一致性
三套 lock 使用现有 `requirements.lock` 作为 constraint 生成；核心版本与主 lock 对齐。

### C5: Docker base 分层
新增 `builder-api`、`builder-ai`、`runtime-api-base`、`runtime-ai-base`；API/Gateway/Runner 分别继承正确 base。

### C6: API 导入冒烟
仅安装 API lock 的干净 venv 可导入 `app.main`，且无 AI 浏览器依赖。

### C7: combined 兼容
combined `runtime` 仍由 runner 构建；默认 Compose 行为未改变。

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
| 本会话完成 | 0/0/0/0 | 0 | - | Docker host 可用时补测实际 API 镜像层大小 |

**技能使用**: `cameltv-agent-team` → 工件与门禁；`cameltv-bug-guard` → Docker base、lock 和导入边界核查。
