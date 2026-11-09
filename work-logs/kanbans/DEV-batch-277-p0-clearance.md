# 🗂️ Dev 看板：Batch 277a — AIQE §0 P0 代码侧清零

> **用途**：M1 前 P0 清零的**代码侧**：删除 ai_gateway 全套残留（P0-5）、DROP 守卫与可逆迁移（P0-2 代码侧）、TA-001.5 门禁脚本。生产操作与 `/uitest` 剥离拆到 277b。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | AIQE P0 代码侧清零（batch-277a） |
| **批次号** | batch-277（拆 a/b，本批 a） |
| **关联文档** | [13 号 §0](../../docs/platform-refactor/13-ai-quality-agent-merged-spec.md)、[baseline C-06/C-07](../../docs/aiqe/baseline.md) |
| **关联 PR** | 本批新建（feature/batch-277-aiqe-ta-000-p0-clearance） |
| **批次模式** | 完整（PRD/PM/Design/Dev/QA/Leader + 看板） |
| **Executor** | DeepSeek Harness（agent-team） |
| **分支 / 基线** | feature/batch-277-aiqe-ta-000-p0-clearance / origin/main `9cf83ee2e` |
| **看板创建** | 2026-11-09 |

---

## 🎯 交付切片进度

| # | 任务 | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | T277a-1 ai_client 直连 | ✅ | ✅ | ✅ | ✅ | 🔄 | 774→484 行 |
| 2 | T277a-2 删 gateway 目录/端点/配置 | ✅ | ✅ | ✅ | ✅ | 🔄 | 8 文件 + 6 端点 + 10 配置 |
| 3 | T277a-3 AiAgent→ExecutionNode（表保留） | ✅ | ✅ | ✅ | ✅ | 🔄 | 零数据迁移 |
| 4 | T277a-4 迁移 drop + downgrade 重建 | ✅ | ✅ | ✅ | ✅ | 🔄 | up/down/up 全 0 |
| 5 | T277a-5 嵌入本地化 + 死代码删除 | ✅ | ✅ | ✅ | ✅ | 🔄 | scripts/ai_agent 删除 |
| 6 | T277a-6 TA-001.5 守卫 + self-test | ✅ | ✅ | ✅ | ✅ | 🔄 | real=FAIL(4/5) 符合预期 |
| 7 | T277a-7 ADR/文档/13 号状态 | ✅ | ✅ | ✅ | ✅ | 🔄 | 3 ADR superseded |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

切片 1-7 全部 ✅；全量回归与 PR checks 进行中。

---

## 📝 本批特殊说明

- **P0-5 已清零**：`app/tests/scripts` 残留 0；`ai_agents` 仅改名不改表（生产节点数据零迁移）。
- **迁移可逆**：`20261109_b277_drop_retired_tables` 的 downgrade 按原定义重建两表。
- **守卫 fail-closed**：真实运行 4/5 未过（P0-1/2/3/4 证据缺失；P0-4 Dockerfile 仍装浏览器）——这是正确状态，不是脚本失败。
- **277b**：`/uitest` 剥离（ExecutionJob kind=ui → cameltv-node）+ 控制面 Dockerfile 去 Chromium + P0-4 证据。
- **运维**：P0-1 Key 轮换 / P0-3 磁盘 / P0-2 备份演练 → 产出 `work-logs/p0-evidence/*.json` 后守卫转绿。

---

## 📌 下一步

1. 全量 pytest 绿 → PR → audit → merge；
2. 277b：P0-4 `/uitest` 剥离；
3. 运维证据到位后跑 `check-p0-ready.ps1` 应为 PASS；
4. batch-279（M1）在 M0 Gate 全绿后开工。
