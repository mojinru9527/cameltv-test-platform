# Batch 70 — PRD Summary（能力产品化 UI 补齐：C63-1）

> **Product (🟦)** | Date: 2026-08-03 | Status: Approved（用户已确认执行器 Codex 并授权启动）

## 1. 问题陈述

按 `docs/能力产品化决策清单.md`（C63-1，P1），平台存在「文档声称能力与实际用户可操作能力不一致」的
API-only 缺口，不得无限期停留在 API-only。本批补齐四块 UI：

1. **API Token 管理**：后端 `/tokens` CRUD 完整，前端无入口（`token:list/manage` 权限已存在）。
2. **用例 Excel/XMind 导入导出**：后端导入导出端点存在，前端无入口、`testcase.ts` 无导入/导出函数。
3. **质量追溯下钻**：`/trace` 列表无明细下钻，接口契约（`trace/case/{id}`、`trace/requirement/{doc_id}`）已具备。
4. **报告模板管理**：模板选择已接入报告生成，但新建/编辑/删除 UI 缺失。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| API Token 管理 UI | 无入口 | 系统管理页可列表/新建/编辑/删除 Token | 本批 QA（浏览器 + API） |
| 用例导入导出 UI | 无入口 | testcase 页 Excel/XMind 导入 + 导出（模板/当前页） | 本批 QA |
| 追溯下钻 UI | 列表无明细 | trace 页可下钻用例/需求详情（覆盖率→明细） | 本批 QA |
| 报告模板管理 UI | 无管理入口 | 报告页模板新建/编辑/删除 | 本批 QA |
| 回归 | 基线 | 前端 typecheck/build + 受影响 Vitest 全绿；后端回归无新增失败 | CI + 本地 |

## 3. 非目标（本次不做）

- **Playground 前端入口**：受 C22-C2/C3 约束（runner 链路稳定后才可展示），本批评估并文档化，不具备则维持 API-only。
- **C69-3**（分批生成性能优化）：P2 非阻塞，顺延。
- **C58-01/03/04、C63-1 之外产品化项**：维持原状态。
- **移除死能力**：需独立审计批次（决策清单规则 3），禁止本批顺带删除。

## 4. 用户故事 + 验收标准

- As a 管理员，I want 在系统管理页管理 API Token，so that 集成方凭据可自助发放/回收。
  - 验收：Given 有 token:manage 权限 / When 新建-列表-编辑-删除 / Then UI 与 API/DB 一致，权限不足 403。
- As a 测试人员，I want 用例可导入导出，so that 用例资产可批量迁移。
  - 验收：Given Excel/XMind 文件 / When 导入 / Then 用例入库且与手工导入一致；导出文件可下载。
- As a 负责人，I want 追溯可下钻，so that 覆盖率数字可追溯到具体用例/需求。
  - 验收：Given coverage 卡片 / When 点击需求/用例 / Then 明细钻取展示同源链（执行/缺陷）。
- As a 测试人员，I want 报告模板可管理，so that 报告格式可自助配置。
  - 验收：Given 模板页 / When 新建-编辑-删除 / Then UI 与 API/DB 一致。

## 5. 技术考量

- 前端沿用 shadcn/ui + Radix + Tailwind（`cameltv-ui-conventions`）；新增 API client 遵循现有 `src/api/*.ts` 模式。
- 菜单/命令面板/权限三处同步（决策清单规则 1）：`seed.py _MENUS`、`CommandPalette ALL_COMMAND_ROUTES`。
- 追溯下钻复用现有 `trace.ts` 查询；用例导入导出复用后端 `/test-cases/import/excel|xmind` 与导出端点。
- 测试：每个 UI 切片补 Vitest（组件/API client mock）+ Playwright 冒烟；后端受影响模块 pytest。

## 6. 上线计划

| 阶段 | 成功门槛 |
|------|---------|
| Slice 1 API Token UI | 浏览器 + API 证据；权限 403 验证 |
| Slice 2 用例导入导出 UI | 导入入库 + 导出下载证据 |
| Slice 3 追溯下钻 UI | 钻取链路证据 |
| Slice 4 报告模板管理 UI | CRUD 证据 |
| 收口 | QA PASS + Leader APPROVED + PR 合入 |

## 7. 条件对账（C-CONDITIONS.md）

- **纳入**：C63-1（产品化 UI）、C63-3（引用 C 条件）。
- **豁免/延后**：C22-C2/C3（Playground runner 条件，本批评估）、C69-3（P2 顺延）、C58-01/03/04、C68-1/J15/J16。
