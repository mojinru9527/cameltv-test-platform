---
title: "Batch 63 PRD — 汇总问题遗留解决版本"
owner: "product-team"
created: "2026-08-02"
status: "approved-for-implementation"
batch: "63"
tags: ["prd", "batch-63", "legacy-debt", "regression-closure"]
related:
  - "batch-63-regression-57-62-summary.md"
  - "../../C-CONDITIONS.md"
---

# Batch 63 — PRD Summary

> **Product (🟦)** | Date: 2026-08-02 | Status: Approved for implementation

## 1. 问题陈述

Batch 57–62 已合入 6 个版本，平台在生产安全、测试可信度、发布事实源上持续加固。
但回归汇总（`batch-63-regression-57-62-summary.md`）显示三类债务仍悬而未决：

1. **本地可控但未收口**：Batch 60/61 台账中 8 个 MUST 项仍是 `NOT RUN` 或部分关闭
   （项目隔离复测、production guard 统一、五入口一致性、批量删除/历史标注闭环、
   三身份权限矩阵、菜单/PRD 对账、功能点验收资产），以及 3 个 P2 UX 项被连续延期。
2. **供应链风险**：backend `ecdsa 0.19.2` 高危（CVE-2024-23342，CVSS 7.4）自 Batch 61
   起一直是 A11 的 FAIL 项，无补丁且未获风险接受；这是本地代码可以关闭的唯一 FAIL。
3. **事实源漂移**：`C-CONDITIONS.md` 中 45 项 Open 条件大部分是早期批次孤儿，部分实际
   已被后续批次覆盖但仍留在 Open 表；菜单/命令面板/PRD 与真实能力不一致，用户无法发现
   成熟模块，只读用户仍看到无权限写入口。

用户关心的是：**下一个版本应先把"能解决、该解决"的遗留问题一次性收口**，让 QA 结论
从 `NOT READY` 向 `LOCAL HARDENING COMPLETE / EXTERNAL BLOCKED` 收敛，而不是继续叠加
新功能。

## 2. 成功指标

| 指标 | 基线（Batch 62） | 目标 | 测量方式 |
|---|---|---|---|
| backend 高危 runtime 漏洞 | 1 个 high 未接受 | 0 个未接受 | `pip-audit` + 依赖替换回归 |
| Batch 60/61 本地 MUST 项 | 8 项 NOT RUN / FAIL | 0 项本地可控未关闭 | 问题台账状态更新 |
| 菜单/命令/权限/PRD 一致 | 部分隐藏、命令面板缺项 | 对账矩阵 100% 一致 | 路由/菜单/命令/权限对照表 |
| 全功能点验收资产 | 以模块/流程零散证据为主 | 功能点→用例→证据矩阵可复核 | QA 资产矩阵 |
| 前端全量回归 | 293 passed | ≥293 passed 且无新增失败 | `npm test -- --run` |
| 后端全量回归 | 980 passed / 3 skipped | ≥980 passed 且无新增失败 | `pytest -q` |

## 3. 非目标（本次不做 + 理由）

| 排除项 | 理由 |
|---|---|
| Test5/VPN、六服务契约、R2 真实执行（B60-BLK-001、B60-P1-012/013） | 无 VPN 授权与凭据包，外部阻塞 |
| 真实 AI/OCR/DeepSeek/蓝湖（G56-011、B60-BLK-002） | 无独立非生产凭据与数据授权 |
| SMTP/Webhook/Jira/TAPD/ELK（B60-BLK-003） | 无非生产端点与凭据 |
| 真机性能采集（CP-C1/CP-C2、B60-BLK-004） | 无授权设备与采集窗口 |
| 旧 PostgreSQL 快照迁移（B56-B08、G56-010/A10、B60-BLK-005） | 无脱敏快照，空库不能替代 |
| 云注册真实完成与生产部署（C58-01～06） | 需用户在外部注册并回填秘密，本批只保留对账 |
| test release 真实执行/回滚（OPS1、B62-C1/C2） | 需 DevOps/DBA owner 与基础设施 |
| release-control 写命令 API/UI（OPS2-CORE-002 后半） | 真实 executor 未配置，先保持只读事实源 |
| 新业务模块/新 UI 主题 | 本批是遗留收口，不叠加新功能 |

## 4. 用户故事 + 验收标准

### US-1：安全负责人关闭供应链 FAIL
**作为** 后端安全负责人，**我想要** 移除或替换引入 `ecdsa` 高危的 `python-jose`，
**以便** A11 供应链门禁不再因无补丁漏洞 FAIL。

**验收**：
- Given backend 依赖锁定且 `security.py` 使用 JWT 编解码
- When 将实现切换到无高危链的库（PyJWT/joserfc）并替换依赖
- Then `pip-audit` 不再报告未接受 high/critical，且登录/鉴权/强改密全量回归通过

### US-2：测试负责人收口项目隔离复测
**作为** QA 负责人，**我想要** testcase/testplan/report/defect/trace/environment/dataset/
integration/uitest 全部完成项目 A→B 切换复测，**以便** 消除陈旧数据与错项目写请求风险。

**验收**：
- Given 项目 A 已有数据且浏览器已登录
- When 切换到项目 B 并触发列表/详情/写操作
- Then 所有域仅按 B 上下文请求；无 A 陈旧行渲染；写请求项目头为 B；API/DB 无跨项目副作用

### US-3：架构负责人统一生产保护
**作为** 平台架构负责人，**我想要** 所有执行入口共用同一 production guard 与执行请求构造器，
**以便** 任何入口都不会在目标/范围不明时触发写请求。

**验收**：
- Given API quick/asset/single/group/batch、UI 自动化、发布包回归、双向集成
- When 对生产目标执行或跨项目环境执行
- Then 全部入口拒绝/允许行为一致；拒绝时零外呼、零任务、零 DB/审计副作用

### US-4：产品负责人对账导航与权限
**作为** 产品负责人，**我想要** 菜单、命令面板、路由、权限与 PRD 一致，
**以便** 用户能发现成熟模块且只读角色不被暴露写入口。

**验收**：
- Given 平台模块清单与三身份角色
- When 对照路由/菜单/命令面板/权限种子与 PRD
- Then 成熟模块可发现；未完成模块显式标注；只读用户无写入口且后端仍拒绝

### US-5：QA 负责人获得可复核验收资产
**作为** QA 负责人，**我想要** 全功能点正负面矩阵与遗留 C 条件对账，
**以便** 每个功能点和每条历史条件都有明确状态与证据归属。

**验收**：
- Given 全平台功能清单与 C-CONDITIONS.md
- When 生成功能点→用例→证据→缺陷矩阵并复核 Open 条件
- Then 矩阵与台账、报告、C-CONDITIONS 完全一致；已满足条件关闭并附合入证据

## 5. 技术考量

- JWT 替换：全仓唯一引用为 `backend/app/core/security.py`；`requirements.lock` 已含
  `pyjwt[crypto]==2.13.0`（python-jose 传递依赖），切换到 PyJWT 并调整异常映射，
  保留 `HS256` 行为，避免引入新依赖。
- 五入口统一：以 `api_execution_service.py` 现有 execution 入口为单一事实源，
  前端收敛到统一请求构造器（参考 Batch 61 的 `apiExecutionRequest.ts`）。
- 权限对账：以 `backend/app/seed.py` 权限种子为基准，前端菜单/命令面板引用统一清单，
  避免硬编码重复。
- 遗留条件对账：以 `C-CONDITIONS.md` 为准逐条复核，禁止无证据关闭；外部项显式标注
  `EXTERNAL-BLOCKED` 并保留解除条件。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|---|---|---|
| Slice 1–3（安全/隔离/生产保护） | 后端 | 定向回归 + 全量回归无新增失败 |
| Slice 4–5（导航/前端闭环） | 前端 | typecheck/build/Vitest 全绿 + 浏览器证据 |
| Slice 6–7（对账/QA） | QA/Leader | 台账、矩阵、报告、C-CONDITIONS 一致后出判决 |
