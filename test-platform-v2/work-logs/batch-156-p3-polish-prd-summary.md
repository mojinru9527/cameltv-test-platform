# Batch 156 — P3 打磨项收口（PRD Summary）

> **Product (🟦)** | Date: 2026-08-12 | Status: Approved | Mode: light

mode: light
豁免理由: 全部为前端体验/文案/可达性修复，无新接口/新配置/新依赖（仅 seed 菜单文案与路由兜底），按轻量批次执行。
非目标: 执行模型统一（test_execution↔api_execution_task，架构项，单独批次）；不引入新功能页面。

## 1. 问题陈述（来源：docs/batch-147-issue-landing.md §4 + Batch 155 QA 遗留）
P3 打磨 18 项中，9 项已被 148–155 顺带修复（03/05/06/07/09/11/12/16/18 验收登记），本批解决剩余：
1. **P3-01** 未知路由显示「页面建设中」而非 404。
2. **P3-04** 报告快照/生成时间时区混用（created_at 本地 naive vs generated_at UTC）。
3. **P3-08** 用例脑图 SVG 键盘不可达（无焦点/无说明）。
4. **P3-10** Playground 未识别步骤静默生成 TODO，无显式提示。
5. **P3-13** 用例搜索受筛选影响无提示。
6. **P3-14** 主题实验室入口「实验功能未开放」与全局主题可切矛盾。
7. **P3-15** 执行历史 Trace 列空展示无引导（产物在详情可下载）。
8. **P3-17** 知识中心偶发重挂载（menus 缓存 + visited forceMount 已由 155 缓解，验收登记）。

另收口 Batch 155 遗留：菜单种子「版本测试任务」直接指向 /release-bundles（冗余重定向已消除，验收登记）；「专项测试」种子名已正确。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 未知路由 | 「页面建设中」 | 404 页（返回工作台入口） |
| 报告时间 | 8h 差 | 同一时区口径（本地 naive 统一） |
| 脑图键盘 | 不可达 | 可聚焦 + aria + 键盘提示 |
| Playground TODO | 静默 | 显式「未识别步骤」标注 |
| 用例搜索提示 | 无 | 筛选生效提示 |
| 主题实验室 | 矛盾文案 | 统一为「未开放」说明（全局主题不受影响） |

## 3. 用户故事 + 验收标准
- As 用户, I want 未知路由看到 404 而不是「建设中」, so that 明确页面不存在。
- As 用户, I want 报告时间与创建时间一致, so that 不再困惑 8 小时差。
- As 键盘用户, I want 脑图可聚焦并提示操作, so that 不依赖鼠标。
- As 测试人员, I want Playground 未识别步骤明确提示, so that 不会误以为全部编译成功。

## 4. 技术考量
- 路由 `*` 改用 NotFound 页（含返回工作台）。
- report_service generated_at 统一为本地 naive ISO（与 created_at 一致）；前端共用 toLocaleString。
- mindmap SVG 容器加 tabIndex/role/aria + 快捷键提示。
- Playground 生成 TODO 步骤改为「未识别步骤」注释 + 页面提示条。
- testcase 搜索区加筛选提示文案。
- theme-lab 未启用时显示统一说明页（非「建设中」）。

## 5. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全部 | checks 全绿 |
| 部署回归 | 测试人员 | 404/时区/键盘/TODO/提示逐项冒烟 |

## 6. 技能使用
- cameltv-ui-conventions（无障碍/文案/四态）
- cameltv-bug-guard（React 副作用四律）
- cameltv-agent-team 流水线
