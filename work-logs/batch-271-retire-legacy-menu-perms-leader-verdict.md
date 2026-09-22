# Batch 271 — Leader Verdict

> **Leader (🎯)** | Date: 2026-09-23 | Decision: **有条件通过**（待用户一次总确认）
> 档位：**轻量批次**（存量数据治理 + 内部运维脚本；平台运行时零改动）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|:----:|------|
| 实现质量 | 优 | 清单复用 `HIDDEN_MENU_CODES`（单一事实源）；默认 dry-run；幂等；只删关联不删权限行 |
| 风险 | 低 | 生产变更 = 18 行 `sys_role_permission`，有回滚 SQL；**导航渲染前后一致**（21/7 未变） |
| 覆盖 | 良 | 6 例新测试 + 菜单目录/路由清单守卫 20 passed；生产 dry-run→apply→独立 SQL 复核 |
| 诚实度 | 优 | 明确写"这次清理**不会**让左侧变短"；把用户问题的另一半（专家区自动展开）登记 `C271-2` 而非悄悄改行为 |

## 关键决策（已批准）

1. **只治数据，不改行为**：用户选 C，本批就只做数据对账；"让左侧只显示 4 行"属另一件事，登记 `C271-2` 等用户选择（A 不自动展开 / B 按角色瘦身）。
2. **保留 `sys_permission` 行**：老书签与 `/testcase?tab=mindmap` 这类深链仍依赖这些权限行存在（前端重定向），删掉会制造新的 404 面。
3. **不碰软下线**：`menu:notify`/`menu:integration` 由 `DISABLED_MENUS` 控制，是可逆配置；解绑会让"改回配置即恢复"失效——这属于**语义边界**，已在 PRD 非目标与脚本 docstring 双处写明。
4. **生产动作三段式**：先 `--check`/dry-run 看清单 → 导出回滚材料 → 才 `--apply`；完成后用**独立 SQL** 复核（不信脚本自述）。
5. **脚本入镜像问题不许含糊**：本次用 `docker cp` 送进容器，属于"不可复现的运维动作" → 登记 `C271-1`（P3）：把运维脚本纳入镜像或改为迁移，并把 `--check` 接进发布前巡检。

## 抽检通过

- ✅ `scripts/retire_legacy_menu_permissions.py` — 清单来源、dry-run 默认、幂等、只删关联，四项与 PRD A1–A3 对应。
- ✅ 生产证据 `work-logs/evidence/batch-271/prod-retire-legacy-menu-perms-20260923.md` — dry-run/apply 输出逐字、独立 SQL 复核、回滚命令齐备。
- ✅ `rollback-restore-bindings.sql` — 18 行原始 id 与 dry-run 清单逐条对应。
- ✅ `test_batch63_menu_catalog.py`（13 例）通过 → seed 侧从未把这些 code 绑回，说明"复发防线"在读时过滤 + seed 两侧都在。

## 判决

**有条件通过**，合入前置：

1. 用户一次总确认（推送 `feature/batch-271-retire-legacy-menu-perms` + Draft PR + required checks 通过后合入 main）；
2. `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks` 通过。

## 下一批次 Leader 条件

| ID | 优先级 | 一句话 | 解除条件 |
|----|:------:|--------|---------|
| `C271-1` | P3 | 运维脚本不在镜像内（`/app/scripts` 不存在），对账要靠 `docker cp` → 不可复现 | 把 `scripts/`（至少 ops 子集）纳入后端镜像，或把该对账写成 Alembic 数据迁移；并把 `--check` 接进发布前巡检 |
| `C271-2` | P2 | 专家区在"当前页位于其中"时强制展开，视觉上仍像一长串入口（用户问题的另一半） | 按用户选择实现：A=去掉自动展开（只按手动展开），B=按角色瘦身 + 搜索直达（与 `C259-1` 合并） |

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| "读时过滤"被当成了"已下线"，存量数据长期不一致（排查时误导结论） | 本批补数据对账脚本 + 把"下线必须配套数据对账"写进复盘卡 | 本批脚本 + `C271-1` |
| 运维脚本靠 `docker cp` 进容器 → 运维动作不可复现 | 登记 `C271-1`（入镜像或改迁移） | `C-CONDITIONS.md` |
| Windows 长路径导致 worktree 创建失败（嵌套目录 + 超长证据文件名） | 复盘卡沉淀"建 worktree 传 `-DestinationRoot` 指浅目录" | QA 复盘卡 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 2h / ~1.5h | 0/0/2/1 | 1 | 技术债（下线只做读时过滤）+ 工具链（长路径） | 同 QA 复盘卡两条 |

**技能使用**: `cameltv-bug-guard`（三问）；`cameltv-agent-team`（轻量批次工件与门禁）。
