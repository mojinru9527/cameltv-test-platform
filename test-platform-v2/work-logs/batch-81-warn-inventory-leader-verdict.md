# Batch 81 — Leader Verdict（WARN 清单长期维护机制，C80-1）

> **Leader (🎯)** | Date: 2026-08-04 | Decision: **APPROVED**（待用户 push 授权 + 二次确认后合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | mode: light，仅建机制（基线/对比/节奏），不减数量、不扩范围 |
| 证据 | PASS | 基线写入 exit 0；对比 delta 0 / 新增 0；SelfTest PASS |
| 诚实性 | PASS | 230 项按 4 类如实分类，未虚构清除 |
| 风险 | 低 | 只读工具 + 文档 |

## 关键决策（已批准）

1. **C80-1 长期化**：WARN 清单进入"周/10 批次审计 + 新增归因 + 趋势记录"的稳态维护，基线刷新须经 Leader 复核。
2. **机器可追踪**：`-WriteBaseline` / `-BaselinePath` 使 WARN 增量可自动对比，不再靠人眼数。

## 抽检通过

- ✅ [scan-common-bugs.ps1](scripts/git/scan-common-bugs.ps1) — 基线模式 Parser 0 错 + 实测
- ✅ [warn-baseline.json](docs/agent-team/warn-baseline.json) — 230 项分类
- ✅ [warn-inventory.md](docs/agent-team/warn-inventory.md) — 4 类 + 节奏 + 趋势
- ✅ `git diff --name-only` — 仅声明文件

## 判决

**APPROVED**。可进入 push → Draft PR → 首轮 checks → 用户二次确认 → 合入流程。

## 下一批次 Leader 条件

- **C81-1（P2）**：每周或每 10 批次执行 WARN 基线审计（`scan-common-bugs.ps1 -BaselinePath docs/agent-team/warn-baseline.json`），把结果追加到 `warn-inventory.md` 趋势表；新增 WARN 类别必须归因。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| WARN 清单缺可追踪基线 | scan 增加 -WriteBaseline/-BaselinePath | scan-common-bugs.ps1 |
| 缺审计节奏与趋势记录 | inventory 文档 + C80-1 长期化 | warn-inventory.md / C-CONDITIONS.md |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际 1.5h | 0/0/0/0 | 0 | — | — |

**技能使用**: `cameltv-agent-team` 轻量批次；`scan-common-bugs.ps1` 基线模式。
