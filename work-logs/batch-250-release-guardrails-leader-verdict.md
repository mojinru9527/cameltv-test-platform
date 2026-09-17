# Batch 250 — Leader Verdict（发布护栏）

> **🎯 Leader** | Date: 2026-09-17 | 抽检：PRD / 代码 / QA / 证据 / 流程回写

## 1. 抽检结论

| 部门 | 工件 | 抽检要点 | 结论 |
|---|---|---|---|
| 🟦 Product | `batch-250-release-guardrails-prd-summary.md` | 轻量批次判定有依据（`mode: light` + 豁免理由）；非目标明确列出 C249-5/6/7 不在本批；三条用户故事均为既有行为加固 | 通过 |
| 🟨 PM | 同文件 §5 + 看板 | 3 个切片各 30–60 分钟粒度，无 PRD 外需求 | 通过 |
| 🎨 Design | N/A | 本批无 UI/接口契约变化，控制面 `static/index.html` 未改动 | 通过（豁免理由已记录） |
| 💻 Dev | 2 个 commit（`2580c2ea`、`f186181d`） | 开关/清理与可观测性分切片提交；未夹带 `test-platform-v2` 改动 | 通过 |
| 🔍 QA | `batch-250-release-guardrails-qa-report.md` | 51 passed + 全目录 lint + DryRun 零副作用逐项核对；P2 缺陷 2 个均已修 | 通过 |

## 2. 判决

**CONDITIONAL — APPROVED（待用户一次总确认 + required checks 全绿 + M5 验收后完全生效）**

依据：C249-1/-3 有实测证据（DryRun 零副作用、lint 全绿）；C249-4 有失败/成功两侧单测；
但 **M5（真实发布验收）未完成**，而 C249-4 的价值恰恰在生产路径上，
因此本判决不代表 C249-4 已验收通过，只代表代码可进入合入流程。

## 3. 本批关闭 / 保持开放的条件

| ID | 内容 | 处置 |
|----|------|------|
| C249-1 | `release.ps1 -DryRun` | 本批关闭（合入后随证据） |
| C249-3 | 控制面测试 E402 清理 | 本批关闭（合入后随证据） |
| C249-4 | 迁移失败可观测性 | 本批关闭（**M5 验收通过后**才可置 Closed） |
| C249-5 | 沿用旧镜像前核对 `RUNNER_ENDPOINTS`；补丁镜像必须含 `alembic/versions` | 保持 Open（本批验收发布将顺带观察，不单独关闭） |
| C249-6 | SKILL.md/DEPARTMENTS.md 补「合并前先比对两侧同名文件规模」 | 保持 Open（属流程文档回写） |
| C249-7 | 控制面 Dockerfile 显式 COPY → `COPY *.py ./` 或守卫测试 | 保持 Open |

> 本批**未新增** C 条件，故 `C-CONDITIONS.md` 只需把 C249-1/-3/-4 从 Open 置 Closed（合入 + M5 后由 Dev 执行）。

## 4. 合入前置（不可跳过）

1. 用户**一次总确认**：推送 `feature/batch-250-release-guardrails` + 创建 Draft PR + required checks 通过后合入 main。
2. `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks` 全绿。
3. 合入后：重建控制面镜像 → 真实发布验收（M5）→ 证据落盘 → C249-1/-3/-4 置 Closed。

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 发布路径无演练开关，QA 实测函数即触发真实构建（Batch 249 事故） | 已修复：`-DryRun` 只算 manifest/digest 并显式声明"未构建/未登记/未上传/未发布" | `scripts/ops/release.ps1` + `C249-1`（本批关闭） |
| 迁移校验失败时远程零输出，控制面无法判读 | 已修复：校验步骤打印 `CAMELTV_MIGRATION target/actual`，事件 reason 落差异 | `deploy/release-console/{migrations,app}.py` + `C249-4` |
| 控制面 Dockerfile 显式列举 COPY 曾漏 `migrations.py`（"恢复平面"会起不来） | 已由 PR #464 补；系统性防复发（改 `COPY *.py ./` 或守卫测试）仍待做 | `C249-7`（保持 Open） |
| 沿用旧镜像 retag 是本仓库常规做法，但缺"转发面/版本目录已同步"的核对清单 | 本批不处理，验收发布时记录观察 | `C249-5`（保持 Open） |

## 6. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际约 2h（不含发布验收） | 0/0/2/2 | 1 | 工具链 + 流程 | 凡是发布路径上的新命令，先用 `-DryRun`/单测锁住"命令构造 + 空跑"，再上生产 |
