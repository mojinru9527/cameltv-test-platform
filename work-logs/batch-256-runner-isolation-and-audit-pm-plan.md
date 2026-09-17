# Batch 256 — PM Plan
> **PM (🟨)** | Date: 2026-09-18

## 规格摘要
**原始需求**: C246-1（dev 依赖审计清零）+ C243-1 的 S1/S2（执行面容器加固与只读 rootfs），见 [PRD](batch-256-runner-isolation-and-audit-prd-summary.md) §1/§3。
**目标时间**: 1 个开发日（4 个切片）；不含 S3 egress 与 S4 每任务容器（已拆为 C256-1/C256-2）。

## 开发任务

### [ ] Slice 1: 依赖审计基线归零（C246-1）
**描述**: 在前端 `package.json` 增加 overrides（`tmp`、`uuid`、`puppeteer-core`、`@puppeteer/browsers`），重新生成 lockfile，令无修复版的 `extract-zip` 从依赖树消失；更新 `npm-audit-baseline.json`。
**验收标准**:
- `npm audit --registry=https://registry.npmjs.org --json` → `high=0, critical=0`
- `node scripts/ci/npm_audit_ratchet.mjs` → `NPM_AUDIT_RATCHET=PASS` 且 baseline 与实际一致
- `npm ci` 干净安装成功（无 ERESOLVE）
**涉及文件**:
- `test-platform-v2/frontend/package.json` — 增加 overrides
- `test-platform-v2/frontend/package-lock.json` — 由 npm 重新生成
- `test-platform-v2/frontend/npm-audit-baseline.json` — ratchet `--update`
**参考**: PRD §2/§5；侦察文档 §1

### [ ] Slice 2: 前端门禁回归（C246-1 验证）
**描述**: 证明依赖变更没有破坏前端硬门禁与 a11y 门禁。
**验收标准**:
- `npm run typecheck`、`npm run build`、`npm test`（Vitest）通过
- `npm run lighthouse:a11y` 真实跑通（含 build + preview）
**涉及文件**: 无（验证型切片，证据写入 QA 报告）
**参考**: PRD US-3

### [ ] Slice 3: 执行面容器加固（C243-1 S1+S2）
**描述**: 在 base compose 与 execution overlay 两处为 `runner`/`aitde-worker` 补齐 `read_only: true` + tmpfs 白名单、显式 `cap_drop: ALL`、`security_opt: no-new-privileges:true`、显式 `user: "10001:10001"`。
**验收标准**:
- `docker compose -f docker-compose.yml -f docker-compose.execution.yml config` 与加 `--profile aitde-worker` 均呈现预期加固字段
- `runner`/`aitde-worker` 的 `read_only == true`，`tmpfs` 覆盖 `/tmp` 等白名单
**涉及文件**:
- `test-platform-v2/deploy/docker-compose.yml` — runner/aitde-worker 安全段
- `test-platform-v2/deploy/docker-compose.execution.yml` — overlay 同名段
**参考**: PRD US-1；侦察文档 §2

### [ ] Slice 4: 契约测试 + 真实只读运行验证
**描述**: TDD 方式先写失败契约测试（断言 compose 加固字段），再补文档；用真实容器证明只读 rootfs 下浏览器仍可启动。
**验收标准**:
- 新增/扩展的后端契约测试在加固前失败、加固后通过
- 真实容器进只读 rootfs 运行：浏览器可启动；`/app` 写入被拒
**涉及文件**:
- `test-platform-v2/backend/tests/test_deploy_compose_contract.py` — 加固断言
- `test-platform-v2/backend/tests/aitde/v34/test_managed_worker_deploy_contract.py` — worker security_opt 断言
- `test-platform-v2/deploy/README.md` — 记录隔离模型与可写点
**参考**: PRD US-1/US-4

## 质量要求
- [x] 后端 `ruff check app --select F821`、app 导入检查
- [x] 前端 `npm ci && npm run typecheck && npm run build`
- [x] 相关测试：新增部署契约测试 + 受影响模块 pytest
- [ ] 响应式（Desktop + Tablet）——本批无 UI 改动，N/A
- [ ] OpenAPI 同步——无 API 变更，N/A
- [x] 无 console 报错/告警（前端构建与 LHCI 输出核查）
- [x] 文档保鲜：deploy README + C-CONDITIONS 更新
