# Batch 212 — PRD Summary：入口收敛（B2 / menu-convergence）

> **Product (🟦)** | Date: 2026-09-02 | Status: Review | Executor: Codex | 完整批次（配置 + 前端）

## 1. 问题陈述

- 平台当前侧边栏把「导航菜单」高频区平铺 10 个一级入口 + 「更多功能」折叠组（c165-3 频率分层），
  无角色分层：tester 角色被授予 19 个菜单权限，普通测试员第一眼看到的是「模块工具集合」，不是「AI 版本验收工作台」；
- 01 定位文档定稿：测试工程师界面默认 ≤5 个一级入口（我的待办 / 版本验收 / 结果与缺陷 / 知识复用 / 资产与更多），
  其余模块按 资产/专家/系统 收进第 5 个入口（02 白名单 §1/§2、§3 用户定稿）；
- C 级入口仍残留可见面：用例服务页内 **Playground Tab**（02 §3 C1，仅 P2b 收敛了独立路由，Tab 仍在）、
  **special/perftest 文档宣称**（README 模块矩阵仍列出音视频专项/性能监控）、知识中心普通用户仍看到
  **图谱/AI 审核台/来源管理/实体/迭代/Wiki 差异等专家 Tab**（02 §3「知识中心普通用户多余 Tab 收维护入口」）；
- 旧**测试计划**（menu:testplan）仍是独立一级菜单 + 独立页面 + 命令面板 + 访客目录四处入口
  （02 §3 C4：独立入口直接删除，数据只读归档不保留入口；URL 处置由 Product 定）。
- 证据：2026-09-02 路线图 B2 出口标准（tester 默认只见 5 项；旧 URL 不 404；菜单/权限/命令面板三处对账）。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| tester 默认一级入口 | 10 平铺 + 更多折叠 | ≤5（工作台 / 版本验收 / 结果与缺陷 / 知识中心 / 资产与更多） | 本批 QA + 小白走查截图 |
| C 级入口可见面 | Playground Tab、README special/perftest 行、知识专家 Tab | 全部下架 | rg + 浏览器走查 |
| 旧测试计划入口 | 菜单/命令面板/访客目录/独立页 4 处 | 0 处；/testplan* 不 404（重定向） | rg + 路由走查 |
| 用例/接口/UI 资产 | 独立模块 | 保留并收「资产」分桶（不删除） | QA 菜单核对 |
| 三处对账 | 菜单/权限/命令面板各自为政 | 命令面板按菜单可见性（menuBacked）+ 权限过滤 | 单元测试 + 走查 |

## 3. 非目标（本次不做）

- 不做「我的待办」工作台内容改造（batch-213）、不做版本验收任务模型/向导（batch-216/217）、
  不做结果与缺陷聚合页（batch-218/219）——B2 只收敛「入口/可见性」，不重建页面；
- 不删除死代码/页面文件（Playground 面板、testplan 页面等保留，batch-215 统一清理）；
- 不冻结/删除 special/perftest 后端代码（API-only 冻结随 batch-215）；
- 不收敛 TestPlan 数据模型/归档视图（D 级，batch-224）；
- 不加埋点（owner 单用户，用户已取消）；
- 不改 knowledge 数据结构 / Wiki 能力，仅按权限收敛 Tab 可见性。

## 4. 用户故事 + 验收标准

- As 黑盒测试员，I want 默认只见 5 个入口（其余收「资产与更多」），so that 我能立刻说出平台主线。
  - 验收：tester 登录 → 侧边栏顶层 = 工作台 / 版本验收(智能测试任务+版本发布包) / 结果与缺陷(报告中心+缺陷管理) / 知识中心 / 资产与更多；其余模块只在「资产与更多」内按 资产/更多/专家/系统 分桶出现。
- As 测试员，I want Playground / 知识专家 Tab / special+perftest 宣称不可见，so that 平台不展示半成品/专家入口。
  - 验收：用例服务无 Playground Tab；知识中心普通用户只留 项目知识/平台研发/检索 3 Tab；README 无 special/perftest 模块宣称行；Ctrl+K 无 Playground/测试计划。
- As 拥有旧书签的用户，I want /testplan* 不 404，so that 老链接可访问。
  - 验收：/testplan、/testplan/:id → 重定向 /testcase；无 NotFound。
- As 超级管理员，I want 专家/系统入口仍可达，so that 不丢失自运营能力。
  - 验收：admin 登录 → 资产与更多含 专家/系统 分桶；命令面板仍可直达专家页（AITDE requiresAitde 项保留）。

## 5. 技术考量

- 菜单数据来自后端 `/system/menus`（按角色权限过滤，seed.py `_MENUS`/`_TESTER_MENUS`/`menu_service.HIDDEN_MENU_CODES`）；
  前端负责「按 code 组装 5 入口 + 分桶」的纯展示分层（沿用 c165-3 的前端分层思路，重构为角色友好分组）；
- 命令面板与菜单对账：给有对应菜单的条目加 `menuBacked`，随菜单可见性联动；AITDE 无菜单专家页保留 `requiresAitde`；
- 知识专家 Tab 门禁用现有权限点：`knowledge:manage/approve`、`wiki:manage/approve`（tester 仅有 `knowledge:view`/`wiki:view`，天然满足普通视图 3 Tab）；
- 风险：角色菜单裁剪影响 e2e 断言（batch51/batch56/smoke 等引用 /testplan）；知识 Tab 门禁若误伤普通阅读（wiki/skills），owner 单用户可先收专家，B11 再补「复用建议」Tab；
- 依赖：batch-211 基线（02 白名单/03 术语表/路线图 R211-1/2/3）。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批合入 main | owner（唯一真实用户） | 小白走查证据：tester 5 入口 + 3 Tab + 无 C 级入口；admin 专家入口可达；/testplan 重定向 |
| M0 出口（B1–B5） | owner | 登录第一眼即「我的待办」（B3 起逐步达成）；C 级入口已下架 |

## 7. 技能使用

- `cameltv-ui-conventions` → 侧边栏/分组组件用 shadcn sidebar 语义组件核对（非测试证据）
- `cameltv-bug-guard` → 前端 useEffect/路由/权限改动前避坑核对（见 QA 报告技能使用节）
- `cameltv-agent-team` → 本批为完整批次六部门工件流程
