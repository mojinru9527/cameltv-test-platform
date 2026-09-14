# Batch 246 — PM Plan

> **PM (🟨)** | Date: 2026-09-15 | Batch mode: full

## 规格摘要

**原始需求**: 完成 Phase 4 工程治理：完整 Ruff/mypy、axe/Lighthouse、依赖审计进入 required checks，禁止 echo 假成功；处理 Dashboard 线性查询。
**目标时间**: 1 个完整批次。

## 开发任务

### [ ] Task 1: 建立质量 ratchet 与审计门禁
**描述**: 新增完整 Ruff/mypy exact-count ratchet、锁定质量工具版本，把 ratchet/pip-audit 加入 required backend job。
**验收标准**:
- 新增 Ruff/mypy occurrence 时 `quality_ratchet.py` 退出 1。
- 历史 baseline 可追踪，删除 finding 时可显示减少量。
- `pip-audit -r requirements.txt` 为 0 known vulnerabilities。
**涉及文件**:
- `scripts/ci/quality_ratchet.py`
- `test-platform-v2/backend/quality-ratchet-baseline.json`
- `test-platform-v2/backend/requirements-quality.txt`
- `.github/workflows/main-quality-gate.yml`
**参考**: PRD US-1/US-2

### [ ] Task 2: 前端 axe/Lighthouse/依赖审计
**描述**: 引入 `@lhci/cli`，配置自动 preview server；修复 Lighthouse 脚本吞错；升级 Vitest/coverage 与安全 override；required frontend job 增加 axe、Lighthouse 和生产依赖审计。
**验收标准**:
- `npm run lighthouse:a11y` exit 0，accessibility >= 0.9。
- `npm audit --omit=dev --audit-level=high` exit 0。
- 完整 `node scripts/ci/npm_audit_ratchet.mjs` 无新增 advisory。
- `package.json` 中不再存在 `|| echo`。
**涉及文件**:
- `test-platform-v2/frontend/package.json`
- `test-platform-v2/frontend/package-lock.json`
- `test-platform-v2/frontend/.lighthouserc.json`
- `.github/workflows/main-quality-gate.yml`
**参考**: PRD US-1/US-3

### [ ] Task 3: 消除 Dashboard 项目级线性查询
**描述**: 新增批量项目统计函数，用 group-by 聚合替代每项目 `get_dashboard_stats` 和执行过滤循环；更新查询预算测试。
**验收标准**:
- 批量统计固定 5 个查询。
- 2/20 项目查询预算不增长。
- cross-project 返回结构与现有前端兼容。
**涉及文件**:
- `test-platform-v2/backend/app/services/statistics_service.py`
- `test-platform-v2/backend/app/services/dashboard_service.py`
- `test-platform-v2/backend/tests/test_batch244_query_budget.py`
**参考**: PRD US-4、C244-1

### [ ] Task 4: CI 契约与文档回写
**描述**: 新增 Phase 4 CI contract 测试，更新开发门禁/前后端 README，关闭 C243-3，记录 C243-4/C244-1 证据。
**验收标准**:
- `test_batch59_quality_contracts.py` 覆盖 required steps 且无 echo。
- 文档列出本地/CI 命令和 ratchet 更新规则。
**涉及文件**:
- `scripts/ci/test_batch59_quality_contracts.py`
- `docs/code-development-gate.md`
- `AGENTS.md`
- `test-platform-v2/{frontend,backend}/README.md`
- `C-CONDITIONS.md`
**参考**: PRD §2、§6

## 质量要求
- [x] 后端全量 pytest
- [x] 前端全量 Vitest/typecheck/lint/build
- [x] axe/Lighthouse
- [x] pip/npm production audit
- [x] 查询预算与 CI 契约测试

## 风险与缓解
- **历史 Ruff/mypy 债务大**：精确 ratchet，只阻止新增，不伪造清零。
- **LHCI 开发依赖有公告**：required 门禁限制在生产依赖；开发工具漏洞记录在报告，避免盲目 major override。
- **Lighthouse 本机 Chrome 差异**：配置 `--no-sandbox --headless=new`，CI 使用标准 Chromium。
