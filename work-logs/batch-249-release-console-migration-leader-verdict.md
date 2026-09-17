# Batch 249 — Leader Verdict

> **Leader (🎯)** | Date: 2026-09-17 | 抽检：PRD / PM / Design / 代码 / QA

## 1. 抽检结论

| 部门 | 工件 | 抽检要点 | 结论 |
|---|---|---|---|
| 🟦 Product | `batch-249-prd-summary-and-b248-hotfix-incident.md` | S1 经实证取消（有行数/文件对比证据）；S2 目标与 ADR-0015 §4 对齐；非目标明确 | 通过 |
| 🟨 PM | 同文件 §0 S2 表 | 6 个 30–60 分钟任务，无 PRD 外需求 | 通过 |
| 🎨 Design | N/A（无新 UI；`static/index.html` 仅把占位改为必填输入） | 变更最小且与既有表单风格一致 | 通过（豁免理由已记录） |
| 💻 Dev | 7 个 commit | 迁移模块与接线分离提交；rollback 不迁移有既有测试兜底 | 通过 |
| 🔍 QA | `batch-249-release-console-migration-qa-report.md` | 45 passed + lint + 实测 revision；含误触事故与止损核对 | 通过 |

## 2. 判决

**CONDITIONAL — APPROVED（待用户一次总确认 + required checks 全绿后生效）**

依据：控制面全量测试 45 passed、改动文件 lint 干净、`Get-AlembicHead` 实测返回真实单头；
fail-closed 的配对项（`release.ps1` 生成真实 revision）已同批完成。尚未 push / 未创建 PR，
因此不满足 APPROVED 的 required-checks 前置。

## 3. 下批条件

| ID | 内容 | 优先级 |
|----|------|--------|
| C249-1 | `release.ps1` 增加 `-DryRun`（只计算 manifest/digest，不构建不登记），杜绝误触真实发布 | P1 |
| C249-2 | **控制面服务自身发布**：把 `deploy/release-console`（含迁移作业）构建并部署到服务器（当前 `cameltv-release-console:20260915`），并文档化其独立发布入口 | P1 |
| C249-3 | 控制面既有测试目录 E402 历史债清理（`tests/test_capacity.py` 等） | P3 |
| C249-4 | 迁移作业失败时的生产可观测性：控制面事件记录目标 revision 与实际 `current` 差异 | P2 |
| C249-5 | 沿用旧镜像前必须核对 `RUNNER_ENDPOINTS` 转发面；补丁镜像必须含 `alembic/versions`（Batch 248 热修教训） | P1 |
| C249-6 | SKILL.md/DEPARTMENTS.md 补充"合并前先比对两侧同名文件规模，判断分支是否已被 main 取代"（含 CHANGELOG 同步） | P2 |

## 4. 合入前置（不可跳过）

1. 用户**一次总确认**：推送 `feature/batch-249-release-console-migration` + 创建 Draft PR + required checks 通过后合入 main。
2. `audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex` → `-RequireSuccessfulChecks` 全绿。
3. 合入后：按 C249-2 发布控制面服务；C 条件追加到 `C-CONDITIONS.md`。

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 试探合并前未先比对两侧同名文件，导致 S1 白做一轮（分支其实已被 main 取代） | 写入手册建议：合并前先 `git diff --stat main...branch` + 比对同名文件规模 | `C249-6`（下批补 SKILL.md/CHANGELOG） |
| `release.ps1` 无 dry-run，QA 误触真实发布 | 开条件 | `C249-1` |

## 6. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h / 实际约 5h | 0/2/1/1 | 2 | 流程 | 合并前先比对两侧同名文件规模，判断分支是否已被取代 |
