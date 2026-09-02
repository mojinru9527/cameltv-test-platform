# Batch 212 — Leader Verdict：入口收敛（B2 / menu-convergence）

> **Leader (🎯)** | Date: 2026-09-02 | Decision: **APPROVED**

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 5/5 | 后端过滤链 + 前端组装模型 + 路由/命令面板/访客目录同步，改动闭合、无残留引用（rg 核对） |
| 风险 | 低 | 仅入口/可见性收敛：不删除任何数据与后端 API；页面文件保留待 batch-215；旧 URL 全部重定向不 404 |
| 覆盖 | 5/5 | typecheck/build/lint/vitest 611 + ruff F821 + 受影响 pytest 25 + 全量 pytest 2360（1 条 origin/main 既有基线失败已双端复现）+ 小白走查 14/14 |

## 关键决策（已批准）
1. **tester 5 入口映射**：工作台（workbench）+ 版本验收（智能测试任务/版本发布包）+ 结果与缺陷（报告中心/缺陷管理）+ 知识中心 + 资产与更多（资产/更多/专家/系统分桶）——严格对齐 01 §3.1，不提前建页面（B3/B6+ 逐步落地）；
2. **旧测试计划 URL 处置（Product 定稿）**：独立入口删除；`/testplan`、`/testplan/:id` 重定向 `/testcase`（不 404）；test-plan 数据仍经报告/追溯/apitest API 只读引用；页面文件保留待 batch-215 清理，数据归档视图随 batch-224；
3. **知识中心普通视图 3 Tab = 项目知识/平台研发/检索**（维护 Tab 收专家）；「版本记录/复用建议」命名与补 Tab 随 B11 知识管线定稿；
4. **special/perftest 宣称下架范围**：菜单/命令面板本就无入口，README 模块矩阵两行删除 + 表下标注（代码冻结随 batch-215）；
5. 命令面板对账采用 menuBacked（随 /system/menus）+ requiresAitde（无菜单专家页）双机制。

## 抽检通过
- ✅ backend seed.py:36 → menu:testplan 注释化；_TESTER_MENUS 移除；menu_service.HIDDEN_MENU_CODES 增 menu:testplan；目录测试 `test_batch212_testplan_menu_removed_from_seed` 断言 seed/角色/HIDDEN/承接资产四项 ✅
- ✅ nav-config.ts MAIN_ROW_DEFS/ASSET_BUCKET_DEFS ↔ 02 白名单 A/B 行一致（用例/接口/UI→资产；DSH/AI 配置/蓝湖/Runtime→专家；系统/集成/通知→系统）
- ✅ 单测：nav-config 18、AssetsMoreGroup 7、KnowledgeTabs 5、CommandPalette 对账更新 —— 全绿
- ✅ 全量 vitest 611 / build / lint 绿；路由 /testplan、/playground 重定向代码抽查
- ✅ 小白走查证据（tester/admin 真实登录、真实后端）：14/14；截图 6 张 + 日志入库 `work-logs/evidence/batch-212/`
- ✅ 全量 pytest 失败集合 = origin/main 基线同款（`test_batch148_p0_fixes.py::...error_fields`），无新增失败

## 判决
**APPROVED** — 合入条件满足：QA 硬门禁全绿（除 origin/main 既有基线 1 条，已双端核对）、小白走查通过、无 C 级残留、
用户一次总授权（推送+PR+合入）已就绪。按流程：push → Draft PR → required checks → 最终审计 → squash 合入 main。

## 下一批次 Leader 条件（如有）
- 无新增 C 条件。路线图 R211-1（B2 出口标准）与 R211-2（每批逻辑审计+真实数据防假成功）**随本批关闭**；
  R211-3（B15 后终审 + 黑盒验收 + 交付文档）保持 Open（见路线图 §5 交接区与 C-CONDITIONS batch-212 处理记录）。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| batch-211 的 R211-1/2/3 条件只写在 verdict 未同步 C-CONDITIONS.md | 本批在 C-CONDITIONS.md 增加 batch-212 处理记录（R211-1/2 关闭附 PR 证据；R211-3 保持 Open），避免追踪断裂 | C-CONDITIONS.md（batch-212 节） |
| 旧导航「更多功能」与「导航菜单」10 平铺不区分角色 | 导航模型改为 5 行 + 分桶，蓝图集中在 nav-config.ts 单点维护 | frontend/src/layouts/nav-config.ts |
| 命令面板入口与菜单/权限各自为政 | 新增 menuBacked 机制随菜单可见性联动，删除项无残留 | frontend/src/components/CommandPalette.tsx |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 约 6h / 约 6h | 0/0/0/0 | 1（走查选择器） | 环境探测 | 先探测 DOM 再写走查断言；代码批开工前先跑受影响全量自检 |

## 技能使用
- `cameltv-agent-team` → 六部门流程与工件（本批完整批次）
- `cameltv-bug-guard` / `cameltv-ui-conventions` → 编码前避坑与组件规范（见 QA 报告技能使用节）