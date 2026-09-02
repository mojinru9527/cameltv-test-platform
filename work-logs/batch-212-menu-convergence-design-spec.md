# Batch 212 — Design Spec：入口收敛（B2 / menu-convergence）

> **Design (🎨)** | Date: 2026-09-02 | Status: 已验收（实现后回填）

## 0. 技术体系确认
shadcn/ui + Radix（sidebar/dropdown/collapsible/tooltip）+ Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border）。
真实栈不是 Ant Design。菜单入口一律复用 `components/ui/sidebar.tsx` 组件族，禁止自造样式。

## 1. 侧边栏一级入口蓝图（tester ≤5，全角色适用）

| 行 | 类型 | 名称 | 代码映射 | 说明 |
|----|------|------|---------|------|
| 1 | 链接 | 工作台 | menu:workbench | 「我的待办」内容改造在 batch-213，本批不动页面 |
| 2 | 分组 | 版本验收 | 智能测试任务 menu:missions、版本发布包 menu:versionmission | 组内按 seed sort 升序 |
| 3 | 分组 | 结果与缺陷 | 报告中心 menu:report、缺陷管理 menu:defect | |
| 4 | 链接 | 知识中心 | menu:knowledge | 普通视图 3 Tab 见 §3 |
| 5 | 折叠容器 | 资产与更多 | 分桶见 §2 | 默认收起；持久化展开态 |

规则：组内 child 为用户可见菜单（后端已按权限过滤）；组无可见成员则不渲染该行；入口数 = 1+1+1+1+1 = 5（tester 全有）。

## 2. 资产与更多分桶（代码 → 桶）

| 桶 | 菜单 code（按 seed sort） |
|----|--------------------------|
| 资产 | menu:requirement(需求文档)、menu:testcase(用例服务)、menu:apitest(接口测试)、menu:uitest(UI 自动化)、menu:dataset(测试数据集)、menu:environment(目标环境) |
| 更多 | menu:schedule(定时任务)、menu:myproject(我的项目)、其他未命中 code（fail-safe） |
| 专家 | menu:dsh_tasks(DSH 任务)、menu:ai_config(AI 配置)、menu:lanhu_evidence(蓝湖证据包)、menu:runtime(Durable Runtime) |
| 系统 | menu:system(系统管理)、menu:integration(集成配置)、menu:notify(通知配置) |

- 桶内保持 seed sort 顺序；空桶不渲染；桶头 = SidebarGroupLabel（text-xs muted）；桶项 = SidebarMenuButton（复刻 NavigationMenuItems）。
- 折叠 icon 模式（collapsible="icon"）：不做折叠容器，分桶项以图标平铺（沿用 c165-3 处理）。

## 3. 知识中心 Tab 收敛（普通 vs 维护）

| 视角 | Tab |
|------|-----|
| 普通用户（缺 knowledge:manage/approve 且缺 wiki:manage/approve） | 项目知识 project / 平台研发 platform / 检索 search（3 Tab，默认 project） |
| 维护者/管理员（拥有上述任一权限 或 `*`） | 全部 12 Tab（概览/项目/平台/检索/来源管理/AI审核台/图谱/实体/迭代/Wiki/Skills/Wiki差异）默认维持 overview |

行为：?tab= 深链到普通用户不可见 Tab → 落到默认 project（不 404、不崩）；搜索常驻条保留。

## 4. 命令面板对账（CommandPalette）

- 删除：测试计划（/testplan）、Playground（/testcase?tab=playground）；
- 有对应菜单的「页面」条目加 `menuBacked: true`（工作台/智能测试任务/用例服务/需求文档/报告中心/定时任务/缺陷管理/版本发布包/知识中心/测试数据集/目标环境/我的项目/系统管理/接口测试/UI 自动化/DSH 任务/AI 配置/蓝湖证据包）；
- 无菜单的 AITDE 专家条目保持 `requiresAitde`（执行中心/愈合评审/Flaky/数据源/Fixture/Durable Runtime/AI 建议收件箱等）——专家工具仍可经 Ctrl+K 直达；
- 带 query 的次级入口（质量追溯/思维导图）保持现状（父页面已 menuBacked）。

## 5. 状态设计核对
| 组件 | Loading | Empty | Error | 折叠 |
|------|---------|-------|-------|------|
| 侧边栏 | menuError 提示保留 | 分桶空 → 桶头不渲染；资产与更多空 → 不渲染容器 | 菜单加载失败重试保留 | icon 模式图标平铺 |
| 知识 Tab 收敛 | — | 无可见 Tab → 默认 project | — | — |

## 6. 设计 QA 走查发现（P0–P3）
- （实现后回填，见 QA 报告设计走查节）

## 7. 设计签核
结论：通过（回填见 QA 报告 §走查）。
