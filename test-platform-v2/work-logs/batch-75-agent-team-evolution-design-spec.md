# Batch 75 — Design Spec（Agent Team 自我进化与提效改造）

> **Design (🎨)** | Date: 2026-08-04 | Status: 就绪

## 0. 技术体系确认

本批不涉及前端/后端代码；技术体系为 Markdown 规范 + PowerShell 只读审计脚本，无依赖。

## 1. 文件结构设计

| 文件 | 动作 | 内容 |
|------|------|------|
| `.claude/skills/cameltv-agent-team/SKILL.md` | 修改 | +双档流水线 / +流程回写 / +复盘卡 / +证据库引用 |
| `.claude/skills/cameltv-agent-team/DEPARTMENTS.md` | 修改 | Leader 模板独立第 6 节；QA/Leader 加复盘卡；Product 加技能使用行 |
| `.claude/skills/cameltv-agent-team/CHANGELOG.md` | 新增 | 技能变更日志（Batch 19→75） |
| `docs/agent-team/pipeline-modes.md` | 新增 | 完整/轻量双档判定 + 豁免记录格式 |
| `docs/agent-team/retro-card-template.md` | 新增 | 复盘卡模板（耗时/缺陷/返工/根因） |
| `docs/agent-team/acceptance-evidence-kit.md` | 新增 | 验收证据库规范与索引结构 |
| `scripts/git/audit-cconditions.ps1` | 新增 | C 条件一致性只读审计 |
| `C-CONDITIONS.md` | 修改 | 追踪规则加状态机说明；最后更新 → 2026-08-04 |

## 2. SKILL.md 新增章节骨架

### 双档流水线

- 完整批次：功能/重构/配置/Schema → PRD/PM/Design/Dev/QA/Leader 六件 + 看板。
- 轻量批次：验收/修复/纯文档/纯证据 → PRD-lite + QA + Leader 三件 + 豁免记录（`mode: light` + 理由）。
- 判定标准：是否引入新行为/新接口/新配置；是 → 完整；否 → 轻量。

### 流程回写（Leader 必做）

```markdown
## 流程回写（Batch 75 起强制）
| 发现 | 处理 | 落点 |
|------|------|------|
| {流程/技能/模板缺陷} | {改 SKILL.md / 开 C 条件 / KB 入库 / 无需处理} | {文件 + 行 或 C id} |
```

### 复盘卡（QA 报告 + Leader 判决必含）

| 字段 | 内容 |
|------|------|
| 计划耗时 | 计划 vs 实际 |
| 缺陷 | P0/P1/P2/P3 计数 |
| 返工次数 | 打回/重做次数 |
| 根因分类 | 需求不清/技术债/外部依赖/工具链/流程 |
| 下次避免 | 1 条可执行动作 |

### 验收证据库引用

> 涉及验收时先读 `docs/agent-team/acceptance-evidence-kit.md`，复用基线证据，只跑增量。

## 3. audit-cconditions.ps1 接口设计

| 项 | 设计 |
|----|------|
| 参数 | `-RepositoryPath`（默认当前目录）、`-WorklogsPath`（默认 `<root>/test-platform-v2/work-logs`）、`-RequireLatestBatch`（开关） |
| 检查 1 | C-CONDITIONS.md 存在且含状态机规则头 |
| 检查 2 | 每个 leader-verdict 的 `C{id}` 都出现在 C-CONDITIONS.md（无孤儿条件） |
| 检查 3 | `✅ Closed` 行必须带证据（PR/commit/#/链接 之一），否则 WARN |
| 检查 4 | C id 无重复定义 |
| 检查 5 | 头部"最后更新"日期不晚于最新 leader-verdict 日期（-RequireLatestBatch 时失败，否则 WARN） |
| 退出码 | 0=通过；1=硬错；2=仅警告 |
| 输出 | 人类可读摘要 + `-Verbose` 明细；只读不写 |

## 4. C-CONDITIONS 状态机说明

```text
状态: Open（待处理）→ In-Progress（处理中）→ Closed（已关闭，必须带证据）
                                       ↘ Deferred（延期，必须带原因与解除条件）
```

规则头新增 3 行：状态定义、Closed 必须带证据、Deferred 必须带解除条件。既有 Open/Closed 分区结构不变。

## 5. 设计 QA 走查发现

### ⚪ P3-01 历史遗留：AGENTS.md 与 SKILL.md 的"双档"措辞暂不同步
SKILL.md 先落地双档，AGENTS.md 保持全量门禁 → **建议**：下批同步 AGENTS.md，本批在 PRD 非目标中记录豁免。

### ⚪ P3-02 本地 .agents 副本与仓库版基线差异
Codex 本地副本有 executor 替换痕迹 → **建议**：本批收尾时以仓库版为源同步，并记录"唯一事实源 = 仓库 .claude/skills"。

## 6. 设计签核

结论：通过（P3 项不阻断，均记录）。
