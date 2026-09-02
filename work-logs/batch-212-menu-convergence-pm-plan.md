# Batch 212 — PM Plan：入口收敛（B2 / menu-convergence）

> **PM (🟨)** | Date: 2026-09-02 | Executor: Codex

## 规格摘要
**原始需求**: PRD batch-212 §4 + 02 白名单 §3 + 路线图 B2 出口标准（tester ≤5 一级入口；C 级入口下架；
旧测试计划独立入口删除且 /testplan* 不 404；用例/接口/UI 保留资产；菜单/权限/命令面板三处对账）。
**目标**: tester 默认 5 入口 + 资产与更多分桶；Playground Tab/知识专家 Tab/special+perftest 宣称下架；testplan 入口删除。
**出口验收**: (1) tester 菜单顶层=工作台/版本验收/结果与缺陷/知识中心/资产与更多；(2) /testplan* 重定向 /testcase；(3) 命令面板无 Playground/测试计划；(4) 知识中心普通用户 3 Tab；(5) README special/perftest 行删除；(6) 全量 typecheck/build + 受影响 vitest/pytest 绿；(7) 小白走查证据。

## 开发任务
### [ ] Slice 1: 后端菜单配置（testplan 下架 + HIDDEN + 角色清单 + 测试）
**描述**: seed.py `_MENUS` 移除 menu:testplan（注释 P2 模式说明）；`_TESTER_MENUS` 移除 menu:testplan；
menu_service.HIDDEN_MENU_CODES 增加 menu:testplan；补 batch-212 目录契约测试（仿 P2a/P2b 模式）。
**验收**: pytest test_batch63_menu_catalog.py + test_menu_visibility_flags.py 绿；`/system/menus` 不再返回 /testplan。
**涉及文件**: backend/app/seed.py、backend/app/services/menu_service.py、backend/tests/test_batch63_menu_catalog.py

### [ ] Slice 2: 前端导航模型（5 入口 + 资产与更多分桶）
**描述**: 重写 layouts/nav-config.ts：定义主链路 5 行蓝图（工作台/版本验收组/结果与缺陷组/知识中心）+
资产分桶（资产/更多/专家/系统）+ `buildNavigation()`；新建 AssetsMoreGroup 折叠容器（替换 MoreMenusGroup）；
MainLayout 改为渲染 buildNavigation 结果；更新/删除旧 nav-config 与 MoreMenusGroup 测试。
**验收**: tester 菜单输入 → 顶层 5 行；分桶正确；未知 code fail-safe 落「更多」；空分桶不渲染；路由命中容器自动展开。
**涉及文件**: frontend/src/layouts/nav-config.ts(+test)、MoreMenusGroup.tsx(+test)→AssetsMoreGroup.tsx(+test)、MainLayout.tsx、NavigationMenuItems.tsx

### [ ] Slice 3: C 级入口下架（Playground Tab / knowledge 专家 Tab / palette / guest）
**描述**: 用例服务页删 Playground Tab 与分支；router /playground → /testcase；知识中心按维护权限收敛 Tab
（普通 3 = project/platform/search，专家 Tab 仅维护者）；命令面板删 Playground/测试计划条目并为有菜单条目加 menuBacked；
guestModuleCatalog 删 /testplan 条目；更新对应测试（CommandPalette.test、guestModuleCatalog.test、知识相关若存在）。
**验收**: vitest 绿；浏览器：tester 无 Playground Tab/3 Tab；admin 专家 Tab 可见；Ctrl+K 无 Playground/测试计划。
**涉及文件**: frontend/src/pages/testcase/index.tsx、router/index.tsx、pages/knowledge/index.tsx、components/CommandPalette.tsx(+test)、layouts/guestModuleCatalog.ts(+test)、components/legacy/LegacyNoticeBanner.tsx（如含 /testplan 需评估）

### [ ] Slice 4: 旧测试计划 URL 处置 + 文档宣称下架
**描述**: router /testplan、/testplan/:id → <Navigate to="/testcase" replace/>（保留页面文件，B5 清理）；
test-platform-v2/README.md 能力矩阵删 音视频专项/性能监控 行并标注已冻结；顺手修 e2e 里引用 /testplan 的静态断言列表（smoke/batch51/batch89）为新行为。
**验收**: 路由走查 /testplan 不 404；README 无 special/perftest 宣称；受影响 e2e 静态清单无 /testplan 期望页。
**涉及文件**: frontend/src/router/index.tsx、test-platform-v2/README.md、frontend/e2e/smoke.spec.ts、batch51-ui-regression.spec.ts、batch89-responsive.spec.ts（最小更新）

### [ ] Slice 5: 路线图 §5 交接区 + 合规工件
**描述**: docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md §5 更新 B2 行（状态 ✅ + 摘要 + 未完成移交）；
工作日志工件齐全（PRD/PM/Design/QA/Verdict/看板）；C-CONDITIONS.md 记录 R211-1/2 关闭与新增 C212（如有）。
**验收**: 文档交叉一致；Leader 判决 APPROVED 前所有工件存在。

## 质量要求
- [x] 响应式（Desktop + 折叠 icon 模式可用）  - [ ] OpenAPI 无 schema 变更（无后端 API 契约变化）  - [ ] 单元测试覆盖（nav/command/palette/后端目录契约）
- [ ] 无障碍（ARIA：sidebar 分组 label/折叠展开按钮保持可访问）  - [ ] 无 console 报错/告警（走查录制）
- [ ] 硬门禁：ruff F821 + typecheck + build + 受影响 vitest/pytest
