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

本地可控的 Batch 63 范围已全部收口：供应链 FAIL、项目隔离矩阵、生产保护
五入口矩阵、菜单/命令面板对账、只读写入口收敛、能力产品化决策、批量删除
闭环、历史标注闭环、搜索提交态、触控目标与遗留 C 条件对账均已关闭并通过
全部本地门禁。真实业务环境、Test5、AI/OCR、真机、旧库快照、云注册与
DevOps 基础设施仍为外部阻塞，不计入通过。

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
| 后端全量 | `pytest tests -q` | PASS，999 passed / 3 skipped / 0 failed |
| 后端供应链 | `pip-audit -r requirements.lock` | PASS，No known vulnerabilities（ecdsa/python-jose 已移除） |
| Alembic | `alembic heads` | PASS，单一 head |
| release-control | `pytest deploy/release-control/tests -q` | PASS，22 passed |
| 前端 typecheck | `npm run typecheck` | PASS |
| 前端全量 | `npm test -- --run` | PASS，85 files / 326 passed |
| 前端构建 | `npm run build` | PASS，Vite 生产构建成功 |
| 差异卫生 | `git diff --check` | PASS |

后端全量 3 个 skip 均来自 `test_batch48_postgresql_concurrency.py`（PG 集成专用，
与 Batch 62 基线一致，非新增失败）。本次新增测试：后端 +19（JWT 6、菜单 4、
生产保护矩阵 6、批量删除闭环 3），前端 +33（隔离矩阵 10、请求头 2、命令面板 3、
CategoryManagerDialog 7、标注闭环 1、testplan/report 提交态 3、触控守护 6、只读矩阵 2）。

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
| B60-P1-006 | P1 | **CLOSED** | 前端确认/取消/幂等/失败保留 4 项 + 后端 DB/审计/跨项目/回滚 3 项（`test_batch63_batch_delete_closure.py`）；`delete_case` 移除行内 commit 恢复批量原子性 |
| B60-P1-008 | P1 | **CLOSED** | `InteractionAnnotatorLoop.test.tsx` 保存→重载→编辑→保存坐标保持闭环 |
| B60-P2-001 | P2 | **CLOSED** | testplan/report 搜索提交态测试：输入不请求、按钮/回车单次 GET（各 1 项） |
| B60-P1-009 | P1 | **CLOSED** | testplan/report/schedule(既有)/environment/dataset/notify/requirement/DebugTab 写入口统一收敛（隐藏或禁用）；只读矩阵测试 2 项 + typecheck |
| B60-P1-010 | P1 | **CLOSED（决策）** | `docs/能力产品化决策清单.md`：Token/Playground/用例导入导出=API-only（文档化），报告模板=部分 UI，改密=已完成，追溯下钻=后续补 UI |
| B60-P2-002 | P2 | **CLOSED** | 关键操作按钮 `min-h-11`（≥44px）+ 6 页触控守护测试 |

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

状态：**LOCAL PASS WITH EXTERNAL CONDITIONS**（本地可控项全部关闭；生产仍 DEFERRED）。建议：
1. 本批合入后，Batch 64 按决策清单排期 Token/Playground/用例导入导出/追溯下钻 UI；
2. 外部阻塞项由用户提供前置条件后按 R2 窗口执行，禁止用本地证据冒充；
3. A11 供应链门禁自本批起可转为 PASS（前端 0 漏洞 + 后端 pip-audit 0 漏洞）。
