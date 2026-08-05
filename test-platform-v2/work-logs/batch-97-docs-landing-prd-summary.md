# Batch 97 — PRD-lite（全景盘点结论落盘 + 环境/账号文档更新 + 决策登记）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

```markdown
mode: light
豁免理由: 纯文档（盘点结论、环境/数据库/账号汇总更新、体育平台承接与瘦身规划、用户决策登记），
无代码、接口、配置、Schema 或依赖变更；按 pipeline-modes.md 判定轻量批次（PRD-lite + QA + Leader + 看板）。
非目标: 不执行代码瘦身（Batch 98/99）；不迁移 CI（Batch 98）；不回填 prod 业务 DB/Redis
（待用户确认提供物）；不补拉 Test5 契约（待 Test5 环境恢复）。
```

## 1. 问题陈述

用户要求对测试平台做一次生产级全景盘点并落盘文档：

- 生产级验收还剩哪些待调整/待优化项；
- 测试平台与体育平台的测试/生产环境地址、数据库、服务器、管理与子账号（admin/tester/viewer 等）整理成文档；
- 规划后续正式承接体育平台项目（在平台生产环境用正常浏览器行为接入）；
- 承接前先给测试平台代码瘦身，做成可复用于其他项目的测试平台。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| 盘点文档 | 无 | `docs/生产级验收现状与体育平台承接规划.md` 落盘（现状/待办/承接/瘦身/路线图/决策） |
| 环境与账号文档 | v1.1（2026-07-25，部分过时） | 更新到 v1.2：Railway、viewer、业务 DB/Redis、admin-service/konfi 账号、版本与 PG 17.6 修正 |
| 用户决策登记 | 未登记 | 8 项决策登记进规划文档 §8，作为 Batch 98/99 输入 |
| 文档保鲜 | 汇总文档缺 frontmatter | 补 frontmatter；`check_doc_freshness.py` exit 0 |
| 范围门禁 | — | 仅 docs/ + test-platform-v2/work-logs/ 文件；audit 0 硬错 |

## 3. 用户故事 + 验收标准

- As a **平台负责人**, I want 生产级验收现状与剩余待办清单，so that 知道下一步优先级与发布门禁差距。
- As a **承接负责人**, I want 体育平台环境/账号/数据库清单与接入路径，so that 正式承接前输入齐备。
- As a **维护者**, I want 代码瘦身与可复用化方案，so that 测试平台可服务其他项目。

Given 文档已按标准元数据落盘且只含凭据槽位，When 保鲜检查与范围审计执行，Then exit 0 且无越界文件。

## 4. 技术考量

- 文档落点：`docs/`（仓库级权威文档），工件落 `test-platform-v2/work-logs/`（Batch 84+ 约定）。
- 安全：只记录公开地址/账号名/凭据槽位，不含明文密码、Token、API Key。
- 事实源：`C-CONDITIONS.md`、`docs/production-delivery/*`、`docs/agent-team/staging-environment.md`、Batch 96 工件、`.github/workflows/*`、`test-platform/config/environments/*.yaml`；生产地址 2026-08-05 实测（Vercel/Railway/`www.camel1.tv` 200）。
- 关键发现已入文档：CI 仍依赖 4 个已批准废弃的 V1 工具（删除前必须迁移）；v1 `test.yaml` test3/test5 不一致；`.env.example` 弱密码已回退。
