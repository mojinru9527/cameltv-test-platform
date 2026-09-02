# Batch 212 — QA 报告：入口收敛（B2 / menu-convergence）

> **QA (🔍)** | Date: 2026-09-02 | Verdict: **PASS** | Executor: Codex | 完整批次

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 20 | 20 | 0 | 0（走查 14/14；硬门禁 + 逻辑审计见下） |

## 可执行门禁（命令 + 退出码 + 结果）
| 门禁 | 命令 | 退出码/结果 |
|------|------|------------|
| 前端 typecheck | `npm run typecheck` | 0 ✅ |
| 前端 lint | `npm run lint`（--max-warnings=0；prune-suppressions 后） | 0 ✅ |
| 前端 build | `npm run build` | 0 ✅ |
| 前端全量单测 | `npm test`（vitest run） | 130 files / 611 tests ✅ |
| 后端 F821 | `python -m ruff check app/ --select F821` | 0（All checks passed）✅ |
| 后端受影响 pytest | `test_batch63_menu_catalog.py`(13) + `test_menu_visibility_flags.py`(4) + `test_rbac_project_roles.py`(5) + `test_viewer_role.py`(3) | 25/25 ✅ |
| Alembic 单头 | `python -m alembic heads` | 单头 `20260904_aitde_v40_governance` ✅（本批无迁移） |
| 后端全量回归 | `python -m pytest tests -q` | **2360 passed / 1 failed / 49 skipped / 1 xfailed** |
| dev-gate（G0–G2） | `dev-gate.ps1` | G1 ruff ✅ / typecheck ✅ / lint ✅；G2 守卫 4/4 ✅；G0 全仓扫描命中存量未触碰文件（见下） |
| 小白走查 | playwright chromium（tester/admin 真实登录） | 14/14 ✅（证据 `work-logs/evidence/batch-212/walkthrough/`） |

### 全量回归失败集合核对（无新增失败）
- 失败 1 条：`tests/test_batch148_p0_fixes.py::TestExecutionErrorFields::test_execute_all_records_error_fields`
  （断言 `error_type in (TARGET_POLICY, NETWORK_ERROR)` 实际 `ASSERTION_FAILED`）。
- **基线核对**：在干净 `origin/main`(0af16025) 临时 worktree 复跑同一用例 → 同样失败 ✅ 判定为既有基线失败，与本批（seed/menu/前端入口收敛）无关；本批无新增失败。
- dev-gate G0 scan-common-bugs 命中 `app/services/requirement_service.py:229 except:pass` 等**存量未触碰文件** HARD/WARN 330 项；本批新增/修改文件 0 命中（逐文件 grep 核对）。该扫描非 CI 门禁（.github/workflows 无调用），历史基线债务随 batch-215 清理批次处理。

## 逐条件验证
### C1: tester 顶层仅 5 个一级入口
**变更文件**: frontend/src/layouts/nav-config.ts:48(MAIN_ROW_DEFS)；MainLayout.tsx:219
**证据**: 走查 `tester 顶层含 5 入口` PASS（导航菜单 | 工作台 | 版本验收 | 版本发布包 | 智能测试任务 | 结果与缺陷 | 报告中心 | 缺陷管理 | 知识中心 | 资产与更多 | 12）；单测 buildNavigation 计数 = mainRows 4 + 容器 1 = 5。

### C2: 其余入口收「资产与更多」分桶（资产/更多/专家/系统）
**变更文件**: nav-config.ts ASSET_BUCKET_DEFS / AssetsMoreGroup.tsx
**证据**: 走查 PASS（资产桶含 用例服务/接口测试/UI 自动化；专家桶含 DSH 任务/AI 配置/Durable Runtime）；admin 见系统桶；单测分桶全绿。

### C3: 用例/接口/UI 保留为资产
**证据**: nav-config.test「用例/接口/UI 保留为资产（不删除、不在顶层平铺）」✅；backend 目录测试 assert menu:testcase in codes & tester ✅。

### C4: C 级入口下架 —— Playground Tab
**变更文件**: frontend/src/pages/testcase/index.tsx（删 Tab/分支）、router/index.tsx（/playground → /testcase）
**证据**: 走查「用例服务无 Playground Tab :: 用例列表 | 脑图视图」PASS；命令面板无 Playground；/playground 重定向 /testcase PASS。

### C5: C 级入口下架 —— special/perftest 宣称
**变更文件**: test-platform-v2/README.md（删 音视频专项/性能监控 两行 + 表下标注）
**证据**: rg 无 `/special`/`/perftest` 菜单行（menu_service HIDDEN 既有）；README 新宣称已删除。UI 本无入口（batch-165 已隐），代码冻结随 batch-215。

### C6: C 级入口下架 —— 知识专家 Tab
**变更文件**: frontend/src/pages/knowledge/index.tsx（维护权限收敛 Tab）
**证据**: 走查 tester 知识中心只读 3 Tab（项目知识/平台研发/检索）PASS、无图谱/AI审核台/概览；admin 可见全部维护 Tab PASS；KnowledgeTabs.test 5 例 ✅。

### C7: 删除旧测试计划独立入口（URL 不 404）
**变更文件**: backend seed.py/menu_service.py（menu:testplan 下架 + HIDDEN）、router/index.tsx（/testplan、/testplan/:id → /testcase）
**证据**: /testplan 走查重定向 /testcase PASS；API 登录权限已无 menu:testplan；test_batch212_testplan_menu_removed_from_seed ✅；命令面板/访客目录/LegacyNoticeBanner 同步移除。

### C8: 菜单/权限/命令面板三处对账
**变更文件**: CommandPalette.tsx（删两项 + menuBacked 对账）
**证据**: CommandPalette.test 更新全绿；走查 Ctrl+K 搜「计划」无 测试计划 PASS；后端 /system/menus 已无 /testplan。

### C9: 无 console 报错/告警（走查）
**证据**: 走查全程仅记录 [vite] 连接 debug 级信息，无 error（脚本捕获 console.error 为空）。

## 代码实现逻辑审计（R211-2）
- **后端过滤链**：seed `_MENUS` 不再生成 menu:testplan → 新库无权限行；`menu_service.HIDDEN_MENU_CODES` 新增 menu:testplan → 存量库旧行对 admin(`*`) 与各角色一律过滤；`_TESTER_MENUS` 同步移除避免孤儿（`test_tester_menu_entries_exist_in_catalog` 兜底）。审计通过（test_batch63 + visibility flags 17/17）。
- **前端组装**：`buildNavigation` 按「角色已过滤的可见菜单」组装 5 行 + 分桶；组内按 seed sort 升序；空组/空桶/空容器不渲染；未命中 code fail-safe 落「更多」。用 tester/viewer/admin 三组菜单单测覆盖 ✅。审计无死分支。
- **C 级路由**：/testplan* 与 /playground 均 Replace 重定向 /testcase，页面组件不再挂载（保留文件待 batch-215 清理）；无 404、无循环。
- **知识 Tab**：`allowedTabs` 由维护权限派生；深链不可见 Tab 回落 allowed[0]（project），不崩；TabsContent 未 forceMount 不会误挂载专家组件。权限最小集 = `*|knowledge:manage|knowledge:approve|wiki:manage|wiki:approve`（tester 仅 knowledge:view/wiki:view → 3 Tab 成立）。
- **命令面板**：menuBacked 条目随 `/system/menus` 可见路径过滤；无菜单的 AITDE 专家页保持 requiresAitde；删除项无残留引用（rg 核对）。
- **真实数据防假成功**：走查用本地真实后端 + seed 真实账号（tester/admin）登录执行，断言基于真实 DOM/URL，非 mock；菜单树来自真实 `/system/menus` 响应（登录 API 权限 88 项、无 menu:testplan）。

## 设计走查发现（P0–P3）
- ⚪ P3-1：资产与更多 容器数量徽标 = 分桶条目总数（12），非分桶数——语义为「可展开项」，已按总数展示（与原 更多功能 一致）。
- ⚪ P3-2：版本验收/结果与缺陷 组 children 常显（非折叠），保证「tester 一眼看到主线」；后续 batch-216+ 主线页面成型后可改为折叠组。记录非缺陷。

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 无 | — | — | — | — |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0
（1 条后端全量回归失败为 origin/main 既有基线，已双端复现核对，非本批引入）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 约 6h / 约 6h | 0/0/0/0 | 1（走查脚本 aside 选择器误用 → 改用 data-slot=sidebar-content） | 环境探测 | 走查前先探测真实 DOM 结构再写断言 |

## 技能使用
- `cameltv-agent-team` → 完整批次六部门工件（本文件 + PRD/PM/Design/Leader/看板）
- `cameltv-ui-conventions` → 侧边栏采用 shadcn sidebar 语义组件（SidebarMenuButton/SidebarMenuSub/Collapsible），无自造样式（对照通过）
- `cameltv-bug-guard` → 编码前核对 useEffect 清理/路由重定向/权限最小集（本批无新增副作用 useEffect；重定向均 replace；命令面板无新增网络请求）