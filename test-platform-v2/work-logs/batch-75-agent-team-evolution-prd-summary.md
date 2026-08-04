# Batch 75 — Agent Team 自我进化与提效改造（PRD Summary）

> **Product (🟦)** | Date: 2026-08-04 | Status: Draft → Review

## 1. 问题陈述

对 Batch 19–73 的历史工件审计发现 Agent Team 的学习闭环存在 5 个断点：

1. **经验不回写**：`cameltv-agent-team` SKILL.md 自 2026-07-23（Batch 36/37）合入后无新提交，而后续 30+ 批次产出了大量新经验（验收模式、执行器验证、C 条件复核），技能文件与真实流程脱节。
2. **门禁被悄悄绕过**：Batch 54–61 大量批次只有 QA/验收工件，缺少 PRD/PM/Design，但 SKILL.md 仍要求"所有改动全部门"，规则与执行不一致且无豁免记录。
3. **无量化复盘**：工件中没有批次耗时、缺陷数、返工次数、根因分类数据，无法衡量"学没学进去"、无法定位最大效率损失点。
4. **C 条件纯手工维护**：C-CONDITIONS.md 曾因合并被回退（Batch 45 的 07-26 版本被 07-28 develop 合并覆盖），且没有一致性校验工具。
5. **验收证据重复劳动**：每批从零做三视口截图/契约/回归，未沉淀可复用资产；本地 Codex 技能副本占位符损坏（"由 Codex 还是 Codex 执行"）。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| SKILL.md 规则完备 | 无双档/无回写/无复盘卡 | 双档流水线 + 流程回写 + 复盘卡 + 证据库引用全部写入 | 本批合入后 |
| DEPARTMENTS.md 模板 | Leader 模板混在第 6/7/8 节 | Leader 模板独立第 6 节 + 复盘卡模板 | 本批合入后 |
| 技能 CHANGELOG | 不存在 | 建立并含 Batch 19→75 历史条目 | 本批合入后 |
| 流程规范文档 | 不存在 | docs/agent-team 3 份规范（双档/复盘卡/证据库） | 本批合入后 |
| C 条件一致性审计 | 无工具 | audit-cconditions.ps1 冒烟 0 硬错 | 本批 QA |
| C-CONDITIONS 状态机 | 无状态定义 | 追踪规则含状态机说明，既有条件零改动 | 本批 QA |
| 本地副本 | 占位符损坏 | Codex 副本占位符修复并与仓库版一致 | 本批收尾 |

## 3. 非目标（本次不做）

- **不改 AGENTS.md**：git 门禁保持现状；双档模式以 SKILL.md 为权威，AGENTS.md 同步留待下批（避免门禁双源漂移）。
- **不改现有 audit-ai-pr.ps1 行为**：本轮仅新增独立脚本；接入现有审计的调用策略留待观察一轮后决定。
- **不删除 C64-2 两个误提交文件**（`pective pipeline — ...`）：豁免理由——删除属独立清理批次范围，避免本批夹带删除操作。
- **不改动 test-platform-v2 任何代码**：纯 Markdown + PowerShell 工具，前端/后端/CI 均不涉及。
- **不实现 KB 自动检索证据化**（原建议 P2）：下批再做。

## 4. 用户故事 + 验收标准

- As a 后续批次执行者, I want SKILL.md 明确"完整/轻量"两档判定标准, so that 验收类批次不再合规塌方。
  - 验收：Given 一个验收/修复类需求 / When Product 判定为轻量批次 / Then PRD-lite + QA + Leader 三件即合规，且豁免理由被记录。
- As a Leader, I want 每批必须写流程回写与复盘卡, so that 经验能回到技能与指标。
  - 验收：Given 批次完成 / When Leader 出判决 / Then 判决末尾含"流程回写"小节；QA 报告含复盘卡字段。
- As a 仓库维护者, I want C 条件有状态机与审计脚本, so that 条件不再丢失或回退。
  - 验收：Given C-CONDITIONS.md 与各 Leader Verdict / When 运行 audit-cconditions.ps1 / Then 返回 0 或明确失败清单。
- As a QA, I want 验收证据库规范, so that 新批可复用已通过的三视口/契约/回归资产。
  - 验收：Given docs/agent-team/acceptance-evidence-kit.md / When 新批做验收 / Then 可按索引复用基线证据并记录增量。

## 5. 技术考量

- 纯 Markdown + 单个 PowerShell 脚本（无第三方依赖），风险低。
- `audit-cconditions.ps1` 只读 C-CONDITIONS.md 与 leader-verdict 文件，不写任何文件，可安全纳入后续 PR 审计。
- C-CONDITIONS.md 采用"规则头 + Open/Closed 分区"结构，状态机只增说明、不动既有条件行。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批合入 | Agent Team 执行者 | SKILL.md/DEPARTMENTS 生效，C75 条件被下批 PRD 引用 |
| 下一批起 | 全部批次 | 双档判定 + 流程回写 + 复盘卡成为强制项 |
