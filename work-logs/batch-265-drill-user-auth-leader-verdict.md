# Batch 265 — Leader Verdict

> **Leader (🎯)** | Date: 2026-09-19 | Decision: **有条件通过**
> 待用户一次总确认（推送 + Draft PR + required checks 通过后合入）后转 APPROVED。

## 评审摘要

| 维度 | 评分 | 备注 |
|------|:----:|------|
| 实现质量 | 良 | 修的是根因（凭据口径），不是给 401 打补丁；错误信息可操作 |
| 风险 | 低 | 只动 QA 脚本；平台端点权限未变；凭据不落盘 |
| 覆盖 | 良 | 单测 3 例 + 真实 3 版本实跑 |
| 流程合规 | 良 | 轻量批次（内部流程工具）；PRD-lite 记 mode/豁免/非目标 |

## 关键决策（已批准）

1. **修驱动而不是放宽端点权限**：`execution-jobs` 的 `execution:manage` 是正确设计；错的是驱动用节点令牌冒充用户。
2. **保留 `--node-token` 但不再用于请求**：避免破坏既有命令行，同时把"节点令牌 ≠ 用户令牌"写进 `--help`，防止再次踩坑。
3. **不编复用命中率**：3 版本实跑中 `reuse_hit_rate` 为 null 且判定不达标，照实保留，并登记 `C265-1`（需要走版本任务流程才能得到真实建议/采纳数）。
4. **顺带修 `--out` 目录**：实跑命中即修，属同一批次的低风险健壮性修复。

## 抽检通过

- ✅ `drill_three_versions.py` — 调用点 `headers = _auth_headers(args)`；`--help` 明确两类令牌用途。
- ✅ `tests/test_batch265_drill_user_auth.py` — 3 例覆盖"用户令牌→Bearer""仅节点令牌→明确失败""调用点不回退"。
- ✅ 实跑报告 `evidence/batch-265/drill-three-versions.json` — 3 个版本、证据完整；SLO 明细含未达标的复用率。
- ✅ 未越界 — 未改 `app/`（除测试目录），未动权限模型。

## 判决

**有条件通过**，合入前置：

1. 用户一次总确认（推送 + Draft PR + required checks 通过后合入 main）。
2. `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks` 通过。

## 下一批次 Leader 条件

- **C265-1（P1）**：⑦ 条的**复用命中率**必须有真实数字。解除条件=通过平台"版本任务"流程跑 ≥3 个版本，使 `reuse_suggestion_event` 产生真实建议/采纳数，再用 `--reuse-suggested/--reuse-adopted` 如实回填并复跑，`meets_all` 才能判定。
- **C265-2（P2）**：把"脚本调平台端点前先确认用户态/节点态"写进 `cameltv-bug-guard` 铁律，避免同类 401 复发。

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| 驱动凭据口径与端点权限不一致（节点令牌调用户端点） | 本批修复 + 回归测试 + `--help` 说明 | 本批代码与 QA D1 |
| 复用命中率无法由驱动自动观测，会成为 ⑦ 条的"永远差一项" | 登记 `C265-1`，明确必须走版本任务流程 | `C-CONDITIONS.md` |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 2h / ~1h | 0/1/1/1 | 1 | 需求（凭据口径未先对齐）+ 健壮性 | 同 QA 复盘卡 |

**技能使用**: `cameltv-bug-guard` → 三问核对（新路径=账号登录，凭据只作参数）；`cameltv-api-test` 口径参考（平台端点鉴权）。
