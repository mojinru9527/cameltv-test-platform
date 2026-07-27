---
title: "DEV 看板 — Batch 48 需求服务验收修复"
owner: "qa-team"
created: "2026-07-27"
last_reviewed: "2026-07-27"
status: "ready_for_push"
tags: ["batch-48", "requirement-service", "acceptance-fixes", "agent-team", "codex"]
related:
  - "../../docs/superpowers/plans/2026-07-27-batch-48-acceptance-fixes.md"
  - "../../tests/test-cases/functional/BATCH47-测试平台需求服务-生产级验收.md"
  - "../../tests/test-cases/functional/BATCH48-测试平台需求服务-生产级复测.md"
  - "../../tests/test-case-standards/生产级模块验收规则.md"
---

# DEV 看板 — Batch 48：需求服务生产验收修复

> **执行方式**：Codex Agent Team
> **分支**：`feature/batch-48-acceptance-fixes`
> **目标**：修复 Batch 47 的 21 个缺陷，完整复测 48 条用例，并沉淀可复用的生产级模块验收规则。
> **基线**：`origin/main@a68e492` + Batch 47 验收资产提交。

## 当前位置

```text
Batch 48 — 验收修复与规则沉淀
├── 已完成：固定 Batch 47 的 48 条用例、21 个缺陷和证据基线
├── 已完成：后端、前端、迁移、供应链修复与行为自动化
├── 已完成：A01～A12 生产验收规则及 Batch 48 复测资产
├── 已完成：双端全量、浏览器三视口、真实 AI、旧 PG 升级和 PG 多连接并发复测
├── 已完成：真实蓝湖有界下载、并发提取、附件失败转人工和截图/OCR，48/48 行为通过
├── 已完成：lanhu-mcp 提交发布到可访问 fork 并通过独立克隆复核，A12 解除
└── 推送门禁：每一次 push 前重新向用户展示范围并取得明确授权
```

## 交付切片

> 实现与测试切片由 Agent Team 主 Agent 统一复核；本看板不以文件存在替代通过结论。

| # | Slice | 状态 | 完成标准 |
| ---: | --- | --- | --- |
| 1 | Batch 47 验收资产与证据导入 | ✅ | 48 条用例、21 个缺陷、报告和脱敏截图可追溯 |
| 2 | 上传/详情/分页/抽取/覆盖率 | ✅ | 专项行为测试通过，UI/API/DB/审计结果一致 |
| 3 | 审查/编辑/导入事务与幂等 | ✅ | 无部分提交；编辑值持久化；重复/并发最终态不产生重复数据 |
| 4 | 模块树/项目隔离/API 关联 | ✅ | 三层树一致；跨项目不泄露；关联校验与持久化正确 |
| 5 | 旧数据库迁移与 metadata | ✅ | 旧卷隔离克隆升级、重复升级、数据保留、唯一 head 与 `alembic check` 零漂移 |
| 6 | 前端数据流/审查 UX/移动端/轮询 | ✅ | 29 文件/124 Vitest，三视口 headed Playwright 通过 |
| 7 | 依赖供应链风险 | ✅ | 生产/全依赖 high=0、critical=0；2 moderate 已登记 |
| 8 | 生产验收规则与 Batch 48 复测资产 | ✅ | A01～A12、判定、证据、48 条复测字段与索引齐全 |
| 9 | 全量验证、QA 报告和发布判定 | ✅ | 48/48 行为通过；A01～A12 全部通过，结论 `READY` |
| 10 | 发布 `lanhu-mcp` 子模块提交 | ✅ | `74bfa7b463ef505008ea25466bc950ad9ed67324` 已从根仓配置的 fork 独立克隆并复核 |
| 11 | 用户确认后 push / Draft PR | 🔒 | 根仓变更完成提交后，再次取得“无其他变动”与本次 push 授权 |

状态：`⏳` 未开始｜`🔄` 进行中｜`✅` 已完成｜`🔒` 等待门禁。

## 验收资产

| 工件 | 路径 | 状态 |
| --- | --- | --- |
| 实施计划 | `docs/superpowers/plans/2026-07-27-batch-48-acceptance-fixes.md` | 已执行 / 已同步结果 |
| Batch 47 基线用例 | `tests/test-cases/functional/BATCH47-测试平台需求服务-生产级验收.md` | 已执行 / NEEDS WORK |
| Batch 48 复测用例 | `tests/test-cases/functional/BATCH48-测试平台需求服务-生产级复测.md` | 已执行：48 通过 / 0 失败 / 0 阻塞 |
| 生产验收规则 | `tests/test-case-standards/生产级模块验收规则.md` | 已建立 |
| Batch 48 QA 报告 | `work-logs/batch-48-需求服务验收修复-qa-report.md` | 已完成 / `READY` |
| Batch 48 证据 | `work-logs/evidence/batch-48-requirement-service/` | 已生成三视口、真实 AI、旧 PG、PG 并发和真实蓝湖三条专项的脱敏证据索引 |

## 阻塞与风险

| 阻塞/风险 | 严重度 | 影响 | 解除条件 |
| --- | :---: | --- | --- |
| 无交付阻塞 | — | `lanhu-mcp` fork 发布、根仓 URL 更新和独立克隆复核均完成；A12 通过 | — |
| React Router 2 个 moderate | P2 | 不影响 high/critical 门禁 | 路由 major 升级批次完成迁移与全量回归 |

## Push 确认门禁（Batch 48 起）

每一次 push（首次、后续修复、冲突处理后、完成确认证据）前，必须先展示待推送文件、提交、目标分支和完整自检结果，并向用户询问：

```text
当前待推送范围如下。是否还有其他变动需要合并？
如果有，我将暂停推送，完成合并和自检后再重新确认。
```

只有用户明确回答“没有其他变动”并授权本次 push，才可执行一次与已展示范围一致的 push。任何新增变更都会使原授权失效并触发重新确认。

## 批次记录

### Batch 47 — 需求服务生产级验收（2026-07-27）

- 结果：7 通过、34 失败、4 阻塞、3 未执行，共 48 条。
- 缺陷：B47-DEF-001～021。
- 结论：`NEEDS WORK`。

### Batch 48 — 验收修复与复测（2026-07-27）

- 已完成：初始实现提交 `d1f7e52be70757c14d4acc153dee17571773b931`、真实外部复测兼容与 PostgreSQL 修复提交 `4dc307ed481fdb9ba01f5b8f949aeed7aef24503`、A01～A12 规则、48 条复测回填、QA 报告、双端全量和三视口浏览器。
- 结果：48 通过、0 失败、0 阻塞；行为回归全部通过。
- 已完成外部复测：真实 AI；旧 PG 隔离克隆升级与 metadata；真实 PG 多连接并发；真实蓝湖有界下载、并发提取、附件失败转人工、截图/OCR。
- 发布结论：`READY`；`lanhu-mcp@74bfa7b463ef505008ea25466bc950ad9ed67324` 已发布到根仓配置的可访问 fork，并通过独立克隆复核。
- 待执行：提交最终证据更新，重新取得用户对根仓 push 的确认；根仓当前未 push、未建 PR。
