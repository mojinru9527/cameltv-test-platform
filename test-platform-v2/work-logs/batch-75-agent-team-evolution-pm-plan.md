# Batch 75 — PM Plan（Agent Team 自我进化与提效改造）

> **PM (🟨)** | Date: 2026-08-04

## 规格摘要

**原始需求**: PRD §2 成功指标 7 项；非目标 §3（不动 AGENTS.md / 不动现有审计行为 / 不删 C64-2 / 不动平台代码）。
**目标时间**: 单日批次，5 个 Slice。

## 开发任务

### [ ] Task 1: SKILL.md 规则更新
**描述**: 在 `cameltv-agent-team/SKILL.md` 增加 4 节：双档流水线（判定标准 + 轻量批次豁免记录）、流程回写（Leader 必写 + CHANGELOG 维护）、复盘卡（QA 报告 + Leader 判决必含）、验收证据库引用。
**验收标准**: - 4 节齐全；- 轻量批次有明确判定与豁免格式；- 保留全部既有强制门禁不变。
**涉及文件**: `.claude/skills/cameltv-agent-team/SKILL.md`
**参考**: PRD §4 US-1/US-2；docs/agent-team/pipeline-modes.md

### [ ] Task 2: DEPARTMENTS.md 模板更新
**描述**: 修复 Batch 37 遗留编号问题（Leader 模板独立为第 6 节）；Product/QA/Leader 模板加入复盘卡与技能使用一行；新增轻量批次模板变体说明。
**验收标准**: - Leader 模板独立章节；- 复盘卡字段表在 QA/Leader 模板中；- 模板无遗留 `{...}` 外占位。
**涉及文件**: `.claude/skills/cameltv-agent-team/DEPARTMENTS.md`
**参考**: PRD §4 US-2

### [ ] Task 3: CHANGELOG + 规范文档
**描述**: 新建技能 CHANGELOG.md（含 Batch 19→75 历史条目与本批条目）；新建 docs/agent-team/ 下 pipeline-modes.md、retro-card-template.md、acceptance-evidence-kit.md。
**验收标准**: - CHANGELOG 不少于 8 条历史；- 3 份文档结构与 PRD 一致；- 文件可被 SKILL.md 相对链接引用。
**涉及文件**: `.claude/skills/cameltv-agent-team/CHANGELOG.md`、`docs/agent-team/*.md`
**参考**: PRD §2

### [ ] Task 4: C 条件审计脚本 + 状态机
**描述**: 新建 scripts/git/audit-cconditions.ps1（只读校验 C 条件一致性）；C-CONDITIONS.md 追踪规则增加状态机说明并更新"最后更新"。
**验收标准**: - 脚本 `-RepositoryPath` 冒烟通过；- 对当前仓库返回 0 或明确失败清单；- C-CONDITIONS 既有条件零改动。
**涉及文件**: `scripts/git/audit-cconditions.ps1`、`C-CONDITIONS.md`
**参考**: PRD §4 US-3

### [ ] Task 5: 本地副本同步 + QA 证据
**描述**: 修复 F:\CamelTv\.agents\skills\cameltv-agent-team 占位符并同步仓库版；QA 执行脚本冒烟、Markdown 结构检查、CI 分类核对；Leader 出判决。
**验收标准**: - 本地副本与仓库版 SKILL.md 一致（除 executor 中性外）；- QA 报告含命令/退出码；- Leader 判决含流程回写与复盘卡。
**涉及文件**: 本地 `.agents/skills/*`、工件
**参考**: PRD §4 US-4

## 质量要求

- [x] 无前端/后端代码变更（CI 分类=docs+scripts/git，跳过前后端重测试，记录分类）
- [x] PowerShell 脚本通过 Parser 语法检查与冒烟
- [x] Markdown 文件无损坏结构（标题/表格可解析）
- [ ] 无调试遗留输出、无密钥
