# Batch c165-2-entry-consolidation — PRD Summary（PRD-lite）
> **Product (🟦)** | Date: 2026-08-13 | Status: Approved
> **mode: light**
> **豁免理由**: 本批为 UI 入口收敛修复（隐藏/重定向两个冗余菜单），不新增接口/配置/依赖；按 SKILL.md「轻量批次」执行。
> **非目标**: 不删除项目/组织后端 API；不新增团队组织功能；不做 Playground 勾选用例（batch-166）。

## 1. 问题陈述
C165-2（P3）：系统管理/项目管理/组织管理/我的项目 4 个入口高度重叠。评估文档 §3.3 建议收敛为 2 个入口：`我的项目`（业务）+ `系统管理`（管理员）。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 冗余入口 | 系统管理/项目管理/组织管理/我的项目 | 仅保留 我的项目 + 系统管理（管理员） | 合入后 |
| 深链 `/project`、`/organizations` | 可打开旧页面 | 重定向到 `/my-projects` | 合入后 |

## 3. 非目标（本次不做）
- 不删除 `/api/v1/projects`、`/api/v1/organizations` 等后端能力（仅隐藏入口/重定向前端路由）。
- 不在 我的项目 内实现团队组织高级管理。

## 4. 用户故事 + 验收标准
- As 平台用户, I want 项目相关入口收敛到「我的项目」, so that 不再出现两个管理同一批项目的入口。
  - 验收：菜单与 Command Palette 不再出现「项目管理」「组织管理」；`/project` 与 `/organizations` 深链重定向到 `/my-projects`。
- As 管理员, I want 保留系统管理入口, so that 平台级用户/角色/审计/Token/邀请码管理不受影响。
  - 验收：系统管理入口仍对管理员可见。

## 5. 技术考量
- 后端：`menu_service.HIDDEN_MENU_CODES` 增补 `menu:project`、`menu:organization`（存量库立即生效）；`seed.py` 注释两菜单行（新库不再生成）；tester/viewer 角色菜单同步移除 `menu:organization`。
- 前端：路由 `/project`、`/organizations` → `<Navigate to="/my-projects" replace />`；Command Palette 的「项目管理」替换为「我的项目」；guestModuleCatalog 注释两模块；ProjectAccessBoundary 仅保留 `/my-projects` 起步路径。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全队 | CI 后端/前端全量回归绿 |
| 部署后走查 | 测试负责人 | 菜单仅剩 我的项目+系统管理；旧深链重定向 |

## 7. 技能使用
- cameltv-bug-guard → 前端路由/菜单收敛无副作用检查。
- cameltv-ui-conventions → 菜单/导航组件基线核对。
