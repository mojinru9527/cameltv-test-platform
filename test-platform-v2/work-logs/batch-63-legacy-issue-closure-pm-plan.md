---
title: "Batch 63 PM Plan — 汇总问题遗留解决版本"
owner: "pm-team"
created: "2026-08-02"
status: "in-progress"
batch: "63"
tags: ["pm", "batch-63", "legacy-debt", "plan"]
related:
  - "batch-63-legacy-issue-closure-prd-summary.md"
  - "batch-63-regression-57-62-summary.md"
---

# Batch 63 — PM Plan

> **PM (🟨)** | Date: 2026-08-02

## 规格摘要

**原始需求**: PRD §1——把本地可控遗留问题一次性收口：供应链 FAIL、项目隔离复测、
production guard 统一、导航/权限/PRD 对账、前端闭环、验收资产与 C 条件对账。
**目标时间**: 7 个切片，每切片 30–90 分钟；外部阻塞项一律不排期。

## 开发任务

### [ ] Slice 1: 供应链安全 — 移除 python-jose/ecdsa 高危链（B61-P1-001）
**描述**: 将 `backend/app/core/security.py` 从 `python-jose` 切换到 PyJWT
（lock 已含 `pyjwt[crypto]==2.13.0`），更新 `requirements.txt` 与
`requirements.lock`，移除 `python-jose`/`ecdsa`；保持 HS256 行为与异常映射。
**验收标准**:
- `pip-audit`（或等价锁定审计）不再报告 high/critical；
- `security.py` 无 `jose` 导入，`pyjwt` 编解码往返 + 过期/非法 Token 测试通过；
- 登录/强改密/鉴权定向回归与全量回归无新增失败。
**涉及文件**:
- `test-platform-v2/backend/app/core/security.py` — 换库与异常映射
- `test-platform-v2/backend/requirements.txt` / `requirements.lock` — 依赖调整
- `test-platform-v2/backend/tests/test_security_jwt.py`（新建） — 契约测试
**参考**: PRD US-1；Batch 61 QA §8；Batch 62 QA 残余 B61-P1-001

### [ ] Slice 2: 项目隔离全模块复测（B60-P0-003）
**描述**: 将项目 A→B 切换隔离从需求页扩展到
testcase/testplan/report/defect/trace/environment/dataset/integration/uitest；
修复任何陈旧数据渲染或错项目写请求。
**验收标准**:
- 每个域切换后列表请求仅带 B 项目上下文且仅 1 次有效 GET；
- A 域陈旧行在 B 下不渲染；写操作项目头为 B；API 拒跨项目；
- 失败注入时无部分副作用。
**涉及文件**:
- `test-platform-v2/frontend/src/layouts/ProjectScopeBoundary.tsx` — 统一作用域守卫
- `test-platform-v2/frontend/src/layouts/__tests__/ProjectScopeBoundary.test.tsx` — 扩展矩阵
- 各页面组件（如发现硬编码项目源时修复）
**参考**: PRD US-2；B60 issue register B60-P0-003

### [ ] Slice 3: 生产保护统一 + API 五入口一致性（B60-P0-004 + B60-P1-019）
**描述**: 后端所有执行入口（quick/asset/single/group/batch、UI 自动化、
发布包回归、双向集成）共用同一 production guard 与执行服务入口；前端统一
执行请求构造器，五入口的环境/变量/保护/结果 schema 完全等价。
**验收标准**:
- 生产目标、跨项目环境、无确认三类请求在全部入口参数化测试中行为一致；
- 拒绝时零外呼、零任务、零 DB/审计副作用；
- 同一 GET/POST 用例五入口结果 schema 一致。
**涉及文件**:
- `test-platform-v2/backend/app/services/api_execution_service.py` — 统一执行入口
- `test-platform-v2/backend/app/api/v1/apitest.py`、`ui_test.py`、`release_bundles.py`、`integration.py` — 接入 guard
- `test-platform-v2/backend/tests/test_batch63_production_guard_matrix.py`（新建）
- `test-platform-v2/frontend/src/pages/apitest/apiExecutionRequest.ts` 及调用方 — 统一构造器
**参考**: PRD US-3；B60 issue register B60-P0-004/B60-P1-019

### [ ] Slice 4: 导航/权限/事实源对账（B60-P1-002 + B60-P1-009 + B60-P1-010）
**描述**: 以 `backend/app/seed.py` 权限种子与路由清单为基准，对账前端菜单、
命令面板与 PRD：成熟模块恢复入口或显式标注；只读角色隐藏写入口（后端仍拒绝）；
API-only 能力形成决策清单（补 UI / 明确 API-only / 移除死能力）。
**验收标准**:
- 路由/菜单/命令/权限四表一致，命令面板覆盖全部成熟模块；
- admin/tester/readonly 三身份矩阵：只读角色无写入口且后端 403；
- API-only 能力清单写入 PRD/README，无"文档声称但不可操作"项。
**涉及文件**:
- `test-platform-v2/frontend/src/layouts/MainLayout.tsx` — 菜单
- `test-platform-v2/frontend/src/components/CommandPalette.tsx` — 命令
- `test-platform-v2/backend/app/seed.py` — 权限种子
- `test-platform-v2/frontend/src/pages/{testplan,requirement,report,schedule,environment,dataset,notify}` — 写入口收敛
- `docs/现状功能PRD.md`、`test-platform-v2/README.md` — 事实同步
**参考**: PRD US-4；B60 issue register B60-P1-002/009/010

### [ ] Slice 5: 前端闭环 + UX 遗留（B60-P1-006/008、B60-P2-001/002/006）
**描述**:
- 批量删除：取消零请求；确认后 UI/API/DB/审计一致；失败回滚证据；
- 历史交互标注：保存→重载→编辑闭环，真实坐标不丢；
- testplan/report 搜索：committed keyword 每次提交仅 1 个有效 GET，旧请求取消；
- 移动/平板触控与小按钮审计：最小触控面积 ≥44px；
- 知识中心桌面标签/卡片密度：1440×900 无横向滚动、响应式列数。
**验收标准**: 每项对应定向 Vitest + 浏览器/Network 证据；全量回归无新增失败。
**涉及文件**:
- `test-platform-v2/frontend/src/pages/testcase/index.tsx` — 批量删除
- `test-platform-v2/frontend/src/pages/release-bundles/components/InteractionAnnotator.tsx` — 历史标注
- `test-platform-v2/frontend/src/pages/{testplan,report}/index.tsx` — 搜索提交态
- `test-platform-v2/frontend/src/pages/knowledge/index.tsx` 及相关组件 — 桌面布局
**参考**: PRD US-5 附带项；B60 issue register B60-P1-006/008/P2-001/002/006

### [ ] Slice 6: 验收资产 + 遗留 C 条件对账（B60-P1-017 + C-CONDITIONS）
**描述**:
- 建立全功能点正负面资产矩阵（功能点→用例→证据→缺陷，Mock/真实分层统计）；
- 逐条复核 `C-CONDITIONS.md` Open 条件：可本地关闭的关闭并附证据
  （含 TPv2-B19-C1 CategoryManagerDialog vitest、TPv2-B21-C2 Knife4j URL 自动发现、
  C25v2-C2 分辨率验证、C24-C1/C2 theme-lab/liquid-glass）；外部项标注
  `EXTERNAL-BLOCKED` 并保留解除条件；超过 60 天无进展的升级或废弃。
**验收标准**: 台账/矩阵/报告/C-CONDITIONS 四者一致；无证据不关闭。
**涉及文件**:
- `C-CONDITIONS.md` — 条件状态更新
- `tests/test-cases/batch-63-function-point-matrix.md`（新建） — 资产矩阵
- `test-platform-v2/frontend/src/pages/knowledge/components/CategoryManagerDialog.test.tsx`（新建）
- `test-platform-v2/backend/app/services/api_asset_service.py`（Knife4j 自动发现）
**参考**: PRD §5；skill C-CONDITIONS 维护约定

### [ ] Slice 7: QA 全量回归 + 判决（收尾）
**描述**: 执行硬门禁（后端 F821/全量 pytest/Alembic，前端 typecheck/build/Vitest、
release-control 套件）、仓库卫生扫描，产出 QA 报告与 Leader Verdict；
完成用户二次确认后走 Draft PR → 审计 → 合入流程。
**验收标准**: 门禁全绿或明确登记失败集合；台账/矩阵/报告一致；用户确认执行器与授权。

## 质量要求
- [x] 响应式（Desktop + Tablet + Mobile 关键页）
- [x] OpenAPI 同步（API 变更时）
- [x] 单元测试覆盖（每个修复先有失败测试）
- [x] 无障碍（label/aria/键盘，涉及页面）
- [x] 无 console 报错/告警、无调试遗留、无秘密入库

## 风险

| 风险 | 控制 |
|---|---|
| Slice 3 五入口改动面大 | 以统一服务入口收口，参数化测试覆盖，禁止前端各入口自行实现 guard |
| Slice 4 权限对账牵涉多页 | 以 seed.py 为唯一基准，矩阵驱动，分页提交 |
| 前端证据类任务耗时 | 先补可稳定失败的测试，浏览器证据按页分批 |
| 外部项被误记通过 | 严格状态词汇，EXTERNAL-BLOCKED 不计 PASS |
