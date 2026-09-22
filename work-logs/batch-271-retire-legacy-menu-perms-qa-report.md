# Batch 271 — QA 报告

> **QA (🔍)** | Date: 2026-09-23 | Verdict: **PASS**
> 档位：轻量批次（存量数据治理 + 内部运维脚本；平台运行时零改动）

## 可执行门禁

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/test_batch271_retire_legacy_menu_permissions.py -q` | **6 passed**（本批新增） |
| `python -m pytest tests/test_batch271_… tests/test_batch63_menu_catalog.py tests/test_route_inventory.py -q` | **20 passed**（菜单目录与路由清单守卫无回归） |
| `python -m ruff check scripts/retire_legacy_menu_permissions.py tests/test_batch271_…py` | All checks passed |
| `pwsh scripts/git/scan-common-bugs.ps1` | HARD **0**；WARN 353（= 基线 344 + 本批 9，**逐条复核见下**） |
| `python scripts/ci/classify_ci_changes.py`（本批文件） | `{"backend": true, "frontend": false, "reasons": ["backend","documentation"]}` |
| `pwsh scripts/git/dev-gate.ps1`（G0–G2 一键门禁） | **`GATE_RESULT=PASS_WITH_WARN`**：scan HARD 0 · ruff F821 过 · `QUALITY_RATCHET=PASS` · backend 依赖审计过 · `npm run typecheck` 过 · `npm run lint` 过 · `NPM_AUDIT_RATCHET=PASS`（16/16/new 0）· `found 0 vulnerabilities` · 路由守卫 4 passed |
| **生产执行**（dry-run → apply → 复核） | 残留绑定 **0**；权限行 **13** 条保留；`--check` 退出码 **0** |

**WARN 逐条复核（新增 9 条）**：全部命中规则 `scripts print（运维脚本可接受，需复核）`，位置为本脚本 `_print_report()` 与 `main()` 里的 CLI 报告输出（`retire_legacy_menu_permissions.py:120-151`），**不是调试遗留**（无 `pdb`/`breakpoint`/调试日志），按规则属"可接受"。

## 逐条验证（A1–A6）

### A1 默认只读 + 单一事实源 ✅

`test_dry_run_changes_nothing`：`retire(apply=False)` 后 `applied=False / deleted=0`，库中绑定未变。
`test_hidden_codes_source_is_shared_with_menu_service`：断言 `module.HIDDEN_MENU_CODES is menu_service.HIDDEN_MENU_CODES`（**同一对象**，杜绝抄第二份清单），并确认软下线 `menu:notify` 不在硬下线集合内。

### A2 只解绑已下线、保留在用与权限行 ✅

`test_apply_unbinds_only_retired_and_keeps_rows`：解绑后该角色仍绑定 `menu:workbench`（在用）与 `menu:notify`（软下线）；`menu:special`/`menu:project` 的 **`sys_permission` 行仍在**。
生产实测：`retired_permission_rows_kept = 13`。

### A3 幂等 ✅

`test_apply_is_idempotent`：第二次 `apply` → `deleted=0`。
生产复跑：`--check` → `待解绑绑定：0 条 / 残留绑定：0`，退出码 0。

### A4 生产残留 = 0（独立 SQL 复核）✅

```sql
select count(*) from sys_role_permission rp join sys_permission p on p.id=rp.permission_id
 where p.code in (13 个已下线 code);   -- → 0
```

（不依赖脚本自述；连的是生产 `cameltv_production`。）

### A5 可回滚 ✅

解绑前导出 18 行 `(role_code, permission_code, role_id, permission_id)` → `evidence/batch-271/rollback-restore-bindings.sql`（`INSERT … ON CONFLICT DO NOTHING`）。回滚命令写在证据文档 §5。

### A6 导航渲染前后一致（不夹带行为变更）✅

| 角色 | 解绑前可见菜单数 | 解绑后 |
|------|:---------------:|:------:|
| tester | 21 | **21** |
| viewer | 7 | **7** |

即：这次清理**不会**让左侧变短（那 13 个 code 早就在读时被过滤）。它的价值是**数据可信**——不再出现"库里绑着 × 界面看不到"。

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|:------:|------|------|
| D1 | P2 | **读时过滤与存量数据不一致**：13 个已下线菜单仍被 tester/viewer 绑定 18 条 → 排查入口数量时产生歧义（Batch 271 用户提问的诱因之一） | ✅ 本批修复（生产残留 0） |
| D2 | P3 | **运维脚本不在镜像内**：生产后端镜像无 `/app/scripts`，本次靠 `docker cp` 送脚本进容器 → 将来的对账/巡检不可复现 | 🆕 登记 `C271-1` |
| D3 | P2 | **专家区在当前页位于其中时强制展开**（`effectiveOpen = open \|\| containsActive`）→ 视觉上仍是"一长串入口"（用户最初问题的另一半） | 🆕 登记 `C271-2`（用户本轮只选 C 处理数据侧） |

## bug-guard「未关闭已知风险」表核对（三问）

1. **本批是否新增清单中任一项？** 否——新增的唯一写路径是 `DELETE FROM sys_role_permission`（无出网/无凭据/无执行代码）；迁移类铁律不适用（不加列、不建迁移）。
2. **本批是否修复/关闭任一项？** 属新发现（D1）并在生产闭环；同时顺带核对菜单目录守卫 `test_batch63_menu_catalog.py`（13 例）仍通过，说明 seed 侧从未把这些 code 绑回。
3. **新增路径是否过铁律？** 写库动作有 `--apply` 开关 + 默认 dry-run + 幂等 + 回滚材料 + 生产前先 dry-run 看清单；**不吞异常**（DB 失败直接抛，退出码非 0）。

## CI 分层核对

本批改 `test-platform-v2/backend/scripts/**` + `tests/**` + `work-logs/**` + `C-CONDITIONS.md` → 分类器 `backend: true`，后端 required 汇总将跑真实后端域；前端域不涉及。不把 required 名称存在当作重测试已跑。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 2h / ~1.5h | 0/0/2/1 | 1（worktree 长路径失败重开） | 技术债（"读时过滤"没有配套数据对账）+ 工具链（Windows 长路径） | ① 任何"下线/隐藏"都要同时给**数据侧对账**（否则库里与界面长期不一致）；② 建 worktree 一律传 `-DestinationRoot` 指浅目录，避开长路径 |

**技能使用**: `cameltv-bug-guard`（三问 + 迁移/写库铁律）；`cameltv-agent-team`（轻量批次流程）。
