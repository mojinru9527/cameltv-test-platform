# Batch 271 证据 — 生产「已下线菜单 × 角色」存量数据对账（用户选项 C）

> 执行时间：2026-09-23 ｜ 目标：生产 `111.230.155.116` 的 `cameltv_production`
> 动因：用户问"生产左侧入口为什么还是这么多"，排查发现**读时过滤**（`HIDDEN_MENU_CODES`）与**存量数据**不一致：
> 界面上看不到这些菜单，但 `sys_role_permission` 里仍绑着 18 条 → "库里有、界面没有"，排查时产生歧义。用户裁定"按照 C 来处理"。
> 变更性质：**只解绑角色关联**，不删权限行、不改代码、不改 Schema。

## 1. 剧本（先只读，再写）

```bash
# ① 本地试点库演习（确认脚本可用、退出码正确）
DATABASE_URL=sqlite:///…/probe.db python scripts/retire_legacy_menu_permissions.py --check
#   → 残留 0（试点库本来就干净），tester 可见 21 / viewer 7

# ② 脚本送进生产后端容器（镜像里没有 scripts/ 目录，故 docker cp）
scp scripts/retire_legacy_menu_permissions.py root@…:/tmp/
docker cp /tmp/retire_legacy_menu_permissions.py cameltv-tp-production-backend-1:/app/

# ③ dry-run（只读）——必须先看清单再动手
docker exec -w /app cameltv-tp-production-backend-1 \
    python retire_legacy_menu_permissions.py --json /tmp/retire-dryrun.json

# ④ 导出回滚材料（18 行 role_id/permission_id）
psql … -c "select r.code, p.code, rp.role_id, rp.permission_id from sys_role_permission rp join …"

# ⑤ 执行解绑
docker exec -w /app cameltv-tp-production-backend-1 \
    python retire_legacy_menu_permissions.py --apply --json /tmp/retire-apply.json
```

## 2. dry-run 输出（生产，逐字）

```
已下线菜单 code：13 个（单一事实源 menu_service.HIDDEN_MENU_CODES）
待解绑绑定：18 条
  - menu:agent-workbench <- tester
  - menu:knowledge:artifacts <- tester, viewer
  - menu:knowledge:graph <- tester, viewer
  - menu:knowledge:platform <- tester, viewer
  - menu:knowledge:project <- tester, viewer
  - menu:mindmap <- tester
  - menu:organization <- tester, viewer
  - menu:perftest <- tester
  - menu:playground <- tester
  - menu:special <- tester
  - menu:testplan <- tester
  - menu:trace <- tester, viewer
角色可见菜单数（前）：{'tester': 21, 'viewer': 7}
（dry-run：未写库；加 --apply 执行）
残留绑定：18
```

## 3. apply 输出（生产，逐字）

```
已删除角色绑定：18 条
角色可见菜单数（后）：{'tester': 21, 'viewer': 7}
残留绑定：0
```

## 4. 独立复核（不依赖脚本自述）

```sql
-- 剩余"已下线菜单 × 角色"绑定
select count(*) from sys_role_permission rp join sys_permission p on p.id=rp.permission_id
 where p.code in ('menu:testplan','menu:special','menu:perftest','menu:project','menu:organization',
                  'menu:agent-workbench','menu:mindmap','menu:playground','menu:trace',
                  'menu:knowledge:project','menu:knowledge:platform','menu:knowledge:graph','menu:knowledge:artifacts');
--   → 0

-- 被保留的权限行（老书签 / ?tab= 深链仍靠它）
select count(*) from sys_permission where code in (…同上 13 个…);
--   → 13
```

脚本自查（复跑 dry-run）：

```
docker exec -w /app cameltv-tp-production-backend-1 python retire_legacy_menu_permissions.py --check
→ check_exit=0；待解绑绑定：0 条；残留绑定：0
```

## 5. 回滚

**回滚材料**：`rollback-restore-bindings.sql`（18 条 `INSERT … ON CONFLICT DO NOTHING`，含 role_id/permission_id 原始值）。

```bash
docker exec -i cameltv-tp-production-postgres-1 psql -U cameltv -d cameltv_production < rollback-restore-bindings.sql
```

生成时间：解绑前（2026-09-23），与 dry-run 清单逐条对应。

## 6. 重要口径：这次清理**不会**让左侧变短

这 13 个 code **早就在读时被过滤**（`menu_service.HIDDEN_MENU_CODES`），所以：

- **导航渲染结果前后完全一致**（`tester 21 / viewer 7` 两个数字都没变）；
- 本批解决的是**数据可信度**：再也不会出现"库里绑着 × 界面看不到"的歧义（Batch 271 排查入口数量时就是被它误导过）；
- 想让左侧"看起来只有 4 行"是另一件事 → 见 Batch 271 QA 报告 §缺陷 中的 `C271-2`（专家区自动展开）。

## 7. 残留与后续

| 项 | 说明 |
|----|------|
| 镜像内无 `scripts/` | 本次用 `docker cp` 送脚本进容器；**将来要在容器里跑对账得重复这一步** → 登记 `C271-1`：把运维脚本纳入镜像（或改为迁移），避免运维动作依赖"拷贝文件" |
| 容器里留有脚本副本 | `/app/retire_legacy_menu_permissions.py`（幂等、只读/解绑两种模式）；下次容器重建即消失，不影响运行 |
| 软下线菜单 | `menu:notify` / `menu:integration` **未解绑**（`DISABLED_MENUS` 可逆配置，解绑会让"改回配置即恢复"失效） |
