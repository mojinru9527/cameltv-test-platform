---
title: "Batch 63 QA Report — 汇总问题遗留解决版本"
owner: "qa-team"
created: "2026-08-02"
status: "local-pass-with-conditions"
batch: "63"
tags: ["qa", "batch-63", "legacy-debt", "regression-closure"]
related:
  - "batch-63-regression-57-62-summary.md"
  - "batch-63-legacy-issue-closure-prd-summary.md"
  - "batch-63-legacy-issue-closure-pm-plan.md"
  - "../../../tests/test-cases/batch-63-function-point-matrix.md"
  - "../../../C-CONDITIONS.md"
---

# Batch 63 — QA 报告

> **QA (🔍)** | Date: 2026-08-02 | Verdict: LOCAL PASS WITH CONDITIONS

## 1. 判决

本地可控的 Batch 63 范围（供应链 FAIL、项目隔离矩阵、生产保护五入口矩阵、
菜单/命令面板对账、知识中心布局、遗留 C 条件对账）已通过全部本地门禁；
B61-P1-001（backend ecdsa 高危）已关闭。真实业务环境、Test5、AI/OCR、
真机、旧库快照、云注册与 DevOps 基础设施仍为外部阻塞，不计入通过。

## 2. 固定基线

| 项 | 值 |
|---|---|
| workflow / executor | agent-team / codex |
| 分支 | `feature/batch-63-legacy-issue-closure` |
| 基线 | `origin/main@9c6263f` |
| worktree | `F:\CamelTv-worktrees\codex-batch-63-legacy-issue-closure` |
| 前端 / 后端端口 | 5200 / 8030 |
| 子模块 | lanhu-mcp@c9f4a43124c1e10c442a487c54c456b1ad32d65e |

## 3. 自检结果

| 门禁 | 命令摘要 | 结果 |
|---|---|---|
| 后端 F821 | `ruff check app/ --select F821` | PASS，0 项 |
| 后端全量 | `pytest tests -q` | PASS，996 passed / 3 skipped / 0 failed |
| 后端供应链 | `pip-audit -r requirements.lock` | PASS，No known vulnerabilities（ecdsa/python-jose 已移除） |
| Alembic | `alembic heads` | PASS，单一 head |
| release-control | `pytest deploy/release-control/tests -q` | PASS，22 passed |
| 前端 typecheck | `npm run typecheck` | PASS |
| 前端全量 | `npm test -- --run` | PASS，81 files / 315 passed |
| 前端构建 | `npm run build` | PASS，Vite 生产构建成功 |
| 差异卫生 | `git diff --check` | PASS |

后端全量 3 个 skip 均来自 `test_batch48_postgresql_concurrency.py`（PG 集成专用，
与 Batch 62 基线一致，非新增失败）。本次新增测试：后端 +16（JWT 6、菜单 4、生产保护矩阵 6）、
前端 +22（隔离矩阵 10、请求头 2、命令面板 3、CategoryManagerDialog 7）。

## 4. 遗留问题处置

| ID | 级别 | 本批处置 | 证据 |
|---|---|---|---|
| B61-P1-001 | P1 | **CLOSED** | `security.py` 切换 PyJWT；lock 移除 python-jose/ecdsa；`test_security_jwt.py` 6/6；pip-audit 0 漏洞；认证回归 65/65 |
| B60-P0-003 | P0 | **CLOSED** | `projectIsolationMatrix.test.tsx` 10 项 + `projectHeader.test.ts` 2 项 + 后端隔离套件 75/75 |
| B60-P0-004 / B60-P1-019 | P0/P1 | **CLOSED（五入口）** | `test_batch63_production_guard_matrix.py` 6/6（quick/asset/single/task）+ parity + `apiExecutionRequest.test.ts`；ui/bundle/integration 入口 guard 由既有 `test_production_operation_guard.py` 等覆盖 |
| B60-P1-002 | P1 | **CLOSED** | `seed.py` 补 notify/environment 菜单；`test_batch63_menu_catalog.py` 4/4；`CommandPalette.test.ts` 3/3（含 release:view 过滤） |
| B60-P1-017 | P1 | **CLOSED（资产建立）** | `tests/test-cases/batch-63-function-point-matrix.md` |
| B60-P2-006 | P2 | **CLOSED（代码）** | `knowledge/index.tsx` lg 换行/小屏滚动；typecheck 通过（浏览器复核待补） |
| TPv2-B19-C1 | P2 | **CLOSED** | `CategoryManagerDialog.test.tsx` 7/7 |
| TPv2-B21-C2 | P2 | **CLOSED** | `_resolve_spec` Knife4j 发现 + `test_openapi_import_knife4j.py` 9/9 |
| B60-P1-006 | P1 | 部分（代码已实现） | `testcase/index.test.tsx` 批量删除确认存在；浏览器/DB/审计/失败回滚动态闭环待补 |
| B60-P1-008 | P1 | 部分（代码已实现） | `InteractionAnnotator.test.tsx` 存在；保存→重载→编辑真实截图闭环待补 |
| B60-P2-001 | P2 | 部分（代码已实现） | testplan/report keywordInput/keyword 分离存在；浏览器 Network 每次 1 GET 证据待补 |
| B60-P1-009 | P1 | 未关闭（遗留） | 菜单/权限种子已对账；testplan/requirement/report 等页只读写入口收敛未逐页完成 |
| B60-P1-010 | P1 | 未关闭（遗留） | API-only 能力产品化决策清单未完成 |
| B60-P2-002 | P2 | 未关闭（遗留） | 移动/平板触控与小按钮全局审计未执行 |

## 5. 外部阻塞（不计通过）

| 阻塞 | 解除条件 |
|---|---|
| Test5/VPN/六服务契约 | 书面 VPN 窗口 + 六契约 + 最小权限账号 |
| AI/蓝湖/OCR | 非生产凭据 + 数据范围 + 授权 |
| SMTP/Webhook/Jira/TAPD/ELK | 非生产端点 + 凭据 + 脱敏规则 |
| 真机性能 | 设备 + 包名 + 采集窗口 |
| 旧 PostgreSQL 快照 | 脱敏快照 + 升级断言 |
| 云注册 C58-01~06 | 外部注册 + 秘密回填 |
| test release 真实执行（OPS1/B62-C1/C2） | DevOps/DBA owner + 基础设施 |

## 6. 发布建议

状态：**LOCAL PASS WITH CONDITIONS**（生产仍 DEFERRED）。建议：
1. 本批合入后，Batch 63 续片继续收口 B60-P1-006/008/009/010、P2-001/002 的动态证据与实现；
2. 外部阻塞项由用户提供前置条件后按 R2 窗口执行，禁止用本地证据冒充；
3. A11 供应链门禁自本批起可转为 PASS（前端 0 漏洞 + 后端 pip-audit 0 漏洞）。
