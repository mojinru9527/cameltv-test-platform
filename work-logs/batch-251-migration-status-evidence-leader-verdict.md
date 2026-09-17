# Batch 251 — Leader Verdict（C250-1 迁移状态证据取源修复）

> **🎯 Leader** | Date: 2026-09-17 | 抽检：PRD / 代码 / QA / 生产证据 / 流程回写

## 1. 抽检结论

| 部门 | 工件 | 抽检要点 | 结论 |
|---|---|---|---|
| 🟦 Product | `batch-251-…-prd-summary.md` | `mode: light` + 豁免理由成立（取源变更，无新接口/配置/依赖）；非目标明确；M1–M4 可判定 | 通过 |
| 🟨 PM | 同文件 §5 + 看板 | 2 个切片（修复 + 生产验证），无 PRD 外需求 | 通过 |
| 🎨 Design | N/A | 无 UI/接口契约变化（`ExecutorResult` 新增**可选**字段，事件 reason 文本增强） | 通过（豁免理由已记录） |
| 💻 Dev | commit `ebed7c96` | TDD 先红后绿；改动集中在 `tencent_executor.py` / `app.py` + 3 个用例；未夹带 `test-platform-v2` | 通过 |
| 🔍 QA | `batch-251-…-qa-report.md` | 54 passed + ruff 全绿 + 生产事件 reason 前后对比；含 TDD 红绿记录 | 通过 |

## 2. 判决

**APPROVED（待用户推送确认 + required checks 全绿）**

依据：修复有单测锁定"不依赖日志窗口"（`logs` 不含状态行、`migration_status` 仍取到），
且已在生产用真实发布验证：`release-20260917-0007` 的 `PROD_OBSERVING.reason` 带出
`migration target=20260922_ai_agent_token actual=20260922_ai_agent_token`，`PRODUCTION_VERIFIED`，
6 容器 healthy、DB revision = target。失败路径语义未变（Batch 250 用例继续全绿）。

## 3. 条件处置

| ID | 内容 | 处置 |
|----|------|------|
| C250-1 | 迁移状态正向证据被 4000 字符日志窗口截断 | ✅ **本批关闭**（完整输出解析 + 事件 reason 生产实测） |
| C248-8 | `--target runner` 本机不可构建 | 保持 Open（本轮以服务器端复用镜像绕过，未做构建修复） |
| C249-5 / C249-6 / C249-7 | 复用镜像核对清单 / SKILL+DEPARTMENTS 回写 / Dockerfile COPY 守卫 | 保持 Open |

> 本批**未新增** C 条件；`C-CONDITIONS.md` 中 C250-1 由 Open 置 Closed（附本批证据路径）。

## 4. 合入前置

1. 用户逐次确认：推送 `fix/batch-251-migration-status-evidence` + 创建 Draft PR + required checks 通过后合入 main。
2. `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks` 全绿。
3. 合入后：清理任务 worktree（生产侧控制面 `release-20260917-3` 与本批发布已完成，无需再发布）。

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 诊断写进事件时复用了"展示用"的截断日志（4000 字符尾部窗口），导致成功路径证据丢失 | 已修复：执行器解析**完整输出**并随结果字段返回；展示日志窗口保持不变 | `deploy/release-console/tencent_executor.py` + `app.py` + `C250-1`（本批关闭） |
| 生产验证需要"再跑一次发布"，但发布制品可复用且无需重新构建 | 已实践：服务器端 retag `-0006` 镜像生成 `-0007` 制品（含 digest 校验），窗口约 1–2 分钟 | `batch-251-…-production-evidence-20260917.md` |
| 复用镜像前缺可执行的核对清单（C249-5） | 本批再次以服务器端核对 `RepoTags` + `config digest` 的方式绕过 | `C249-5`（保持 Open） |

## 6. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1.5h / 实际约 1.5h | 0/0/1/1 | 0 | 流程（上游遗留） | 把诊断写进事件/返回体前先确认取值源是**完整数据**，而不是展示用的截断窗口 |
