# Batch 271 PRD-lite — 已下线菜单权限的存量数据对账（用户选项 C）

> **Product/PM** | Date: 2026-09-23 | 档位：**轻量批次**
> `mode: light`
> 豁免理由：**存量数据治理 + 内部运维脚本**——不新增平台接口/配置/依赖，不改 Schema，不改平台运行时行为（导航渲染前后一致）。判定依据 `docs/agent-team/pipeline-modes.md`：属"内部流程工具 / 纯证据"档；先例=Batch 262/263（运维与裁定，轻量）。

## 1. 背景（用户提问 → 排查 → 裁定）

用户问："生产环境为什么左边列表还是这么多入口？"

排查结论（`work-logs/evidence/batch-271/prod-retire-legacy-menu-perms-20260923.md`）：

1. 菜单收敛**已上线**（生产 bundle 含"专家区"/"结果与缺陷"，无"资产与更多"），一级入口确实只有 4 个；
2. 用户看到的是**专家区展开后的二级条目**（资产/引擎与配置/个人/系统 分桶）；
3. 排查中发现**数据不一致**：`HIDDEN_MENU_CODES` 的 13 个已下线菜单在**读时被过滤**，但存量库 `sys_role_permission` 里仍绑着 **18 条**（tester 12 / viewer 6）——"库里有、界面没有"。

用户裁定：**按选项 C 处理**（治理数据，让"库=界面"一致）。

## 2. 本批做什么

| # | 动作 | 产出 |
|---|------|------|
| B1 | 新增**幂等**对账脚本：把已下线菜单从所有角色解绑（默认 dry-run，`--apply` 才写） | `test-platform-v2/backend/scripts/retire_legacy_menu_permissions.py` |
| B2 | 代码清单**复用** `menu_service.HIDDEN_MENU_CODES`（单一事实源）+ 回归测试 6 例 | `tests/test_batch271_retire_legacy_menu_permissions.py` |
| B3 | 生产执行：dry-run → 导出回滚材料 → apply → 独立复核 | `work-logs/evidence/batch-271/**`（2 份 JSON 报告 + 回滚 SQL + 证据说明） |
| B4 | 登记后续条件（脚本入镜像、专家区展开口径） | `C-CONDITIONS.md`：`C271-1`、`C271-2` |

## 3. 非目标（明确不做）

- ❌ **不改平台代码/接口/Schema/权限模型**（脚本只删 `sys_role_permission` 行）；
- ❌ **不删 `sys_permission` 行**：老书签与 `?tab=` 深链仍依赖这些权限行继续走前端重定向；
- ❌ **不碰软下线**（`DISABLED_MENUS` 的 `menu:notify`/`menu:integration`）：那是可逆配置，解绑会让"改回配置即恢复"失效；
- ❌ **不改专家区展开行为**（用户本轮只选 C）→ 若要"左侧只显示 4 行"，走 `C271-2`；
- ❌ 不宣称"清理后左侧会变短"——**导航渲染前后一致**，本批解决的是数据可信度。

## 4. 验收判据

| # | 判据 | 实测 |
|---|------|------|
| A1 | 脚本默认只读；`--apply` 才写；清单来自 `HIDDEN_MENU_CODES` | ✅ 6 例单测（含 dry-run 不改库、单一事实源断言） |
| A2 | 只解绑已下线 code，在用/软下线绑定与权限行保留 | ✅ 单测 + 生产复核（13 条权限行仍在） |
| A3 | 幂等：重复执行第二次为 0 删除 | ✅ 单测 + 生产 `--check` 退出码 0 |
| A4 | 生产残留绑定 = 0 | ✅ SQL 独立复核 `remaining_retired_bindings = 0` |
| A5 | 可回滚 | ✅ `rollback-restore-bindings.sql`（18 条原始 role_id/permission_id） |
| A6 | 导航结果不受影响（不制造"顺手改行为"） | ✅ 前后 `{'tester': 21, 'viewer': 7}` 不变 |

## 5. bug-guard 预检

- 新增写路径仅一条：`DELETE FROM sys_role_permission WHERE permission_id IN (13 个已下线 code)`，**有 `--apply` 开关 + dry-run 默认 + 幂等 + 回滚材料**；
- 无出网、无凭据、无执行代码路径；
- 迁移类铁律：本批**不加列、不做迁移**，只做数据行删除（不涉及 `alembic`）。
