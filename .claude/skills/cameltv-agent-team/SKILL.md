---
name: cameltv-agent-team
description: Use for ANY change to the CamelTv test platform (test-platform-v2/) — 需求/新功能/重构/改进/Bug修复/配置/Schema变更. Runs the six-department Agent Team pipeline (Product→PM→Design→Dev→QA→Leader), writes the standard work-logs/ batch artifacts, and keeps the Dev kanban to survive multi-batch context loss. Triggers: "走 agent team", "六部门流水线", "开一个 batch", "改测试平台", "team pipeline".
---

# CamelTv Agent Team 流水线

## 何时使用（强制门禁）

**涉及 `test-platform-v2/` 的所有改动，无论类型或大小，都必须走这条流水线。** 本文件与仓库根目录 `AGENTS.md` 是门禁事实源。

只有以下三种情况可绕过：纯文档 typo / 非平台代码（`lanhu-mcp/`、`deploy/`、`tests/` 的独立改动）/ 紧急生产热修（事后必须补走完整流程并在 work-logs 记录跳过原因）。

## 流水线

```
需求输入 → Product(PRD) → PM(Tasks) → Design(Spec) → Dev(Code) → QA(Test) → Leader(Review) → 交付
```

一个「批次（batch）」= 走完一轮六部门。每个部门产出一份 `work-logs/` 工件（见下）。执行方式是**工件驱动的手动流水**：依次扮演各部门角色、逐份写出工件，不是运行某个脚本（历史的 `team-orchestrator.js` 已不存在，别引用它）。

| # | 部门 | 角色规则 | 交付工件 |
|---|------|------------|---------|
| 1 | 🟦 Product 产品 | `DEPARTMENTS.md` Product 节 | `batch-{name}-prd-summary.md` |
| 2 | 🟨 PM 项目管理 | `DEPARTMENTS.md` PM 节 | `batch-{name}-pm-plan.md` |
| 3 | 🎨 Design 设计 | `DEPARTMENTS.md` Design 节 | `batch-{name}-design-spec.md` |
| 4 | 💻 Dev 开发 | `DEPARTMENTS.md` Dev 节 | 代码 + `kanbans/DEV-{name}.md` |
| 5 | 🔍 QA 测试 | `DEPARTMENTS.md` QA 节 | `batch-{name}-qa-report.md` |
| 6 | 🎯 Leader 领导 | `DEPARTMENTS.md` Leader 节 | `batch-{name}-leader-verdict.md` |

各部门的角色定位、关键规则和**交付物模板**见 [DEPARTMENTS.md](DEPARTMENTS.md)。

## Git 工作流（强制）

以下步骤是 Agent Team 代码交付的标准 git 流程，**不可跳过**。违反此流程导致的分支保护拒绝合入 / 合并冲突 / 代码丢失，由 Dev 部门负责。

### 分支命名

- 功能批次：`feature/batch-{N}-{简短描述}`（如 `feature/batch-20-fix-seven-gaps`）
- Bug 修复：`fix/{简短描述}`（如 `fix/duplicate-requests`）
- 描述用短横线 kebab-case，不超过 5 个单词

### 标准流程

```bash
# 0. 开工前强制拉取最新代码
git fetch origin main

# 1. 从最新 main 创建独立 worktree；固定入口自动写入 owner=agent-team
pwsh scripts/git/start-agent-team-task.ps1 -Kind feature -Task batch-{N}-{name} -Scope test-platform-v2 -FrontendPort {独立端口} -BackendPort {独立端口}

# 1.1 在新 worktree 开工前验证
pwsh scripts/git/verify-ai-worktree.ps1 -RequireClean -RequireMetadata -ExpectedOwner agent-team

# 2. 每切片结束后只暂存本切片文件（防夹带其他任务或生成物）
git status --short
git add -- path/to/file1 path/to/file2
git diff --cached --name-status
git commit -m "feat(batch-{N}): {切片描述}"
git push -u origin feature/batch-{N}-{name}

# 3. 全部 Slice 完成 + Leader APPROVED 后，创建 PR
#    ⚠️ 必须先 push 到 feature 分支，再建 PR
#    ⚠️ 禁止直接 git merge/push 到 main（本地 hook 与远端规则均会拒绝）
gh pr create \
  --base main \
  --head feature/batch-{N}-{name} \
  --title "feat: Batch {N} — {一句话摘要}" \
  --body "Agent Team 六部门流水线已完成。工件见 work-logs/batch-{N}-*-*.md"

# 3.1 PR 创建后做基础审计；三项 required checks 全绿后做最终审计
pwsh scripts/git/audit-ai-pr.ps1 -ExpectedOwner agent-team
pwsh scripts/git/audit-ai-pr.ps1 -ExpectedOwner agent-team -RequireSuccessfulChecks

# 4. PR 合入且确认无需继续修复后，从控制 worktree 更新 main 再清理任务 worktree
git -C F:/CamelTv-control pull --ff-only origin main
git worktree remove {任务 worktree 绝对路径}
git branch -d feature/batch-{N}-{name}
```

### 防冲突规则

每个代码任务从 `origin/main` 独立创建 worktree。仓库内 ADR-0014、`AGENTS.md` 和本文件是共同事实源；路径绑定的个人 Memory 只作辅助。已结束的旧任务分支禁止继续追加 commit。

### 多窗口并行开发（强制）

**当 Agent Team 同时开启 ≥2 个窗口处理不同任务时，必须使用 Git Worktree 隔离工作目录。** 共享单一工作目录会导致分支切换时代码互相覆盖、未提交改动丢失。违反此规则导致的问题由 Dev 部门承担全部责任。

#### 为什么必须隔离

```
❌ 错误：3 个窗口共享 F:\CamelTv
   窗口1 checkout feature/fix-A → 窗口2 看到的文件变了
   窗口2 checkout feature/fix-B → 窗口1 的改动被覆盖
   → 互相踩踏，代码丢失

✅ 正确：每个窗口独立 worktree
   F:\CamelTv-control\      ← 控制 worktree（main，只同步不开发）
   F:\CamelTv-worktrees\claude-fix-a\ ← Claude：feature/fix-a
   F:\CamelTv-worktrees\codex-fix-b\  ← Codex：feature/fix-b
   F:\CamelTv-worktrees\agent-team-c\ ← Agent Team：feature/c
   → 各自隔离，互不影响
```

#### 多窗口生命周期

```bash
# ═══════ V1 开发周期 ═══════

# Step 1：每个窗口开工前，在主仓库执行一次
pwsh scripts/git/start-claude-task.ps1 -Kind feature -Task batch-{N1}-{name1} -Scope {模块1} -FrontendPort 5173 -BackendPort 8000
pwsh scripts/git/start-codex-task.ps1 -Kind feature -Task batch-{N2}-{name2} -Scope {模块2} -FrontendPort 5174 -BackendPort 8001
pwsh scripts/git/start-agent-team-task.ps1 -Kind feature -Task batch-{N3}-{name3} -Scope {模块3} -FrontendPort 5175 -BackendPort 8002

# Step 2：每个 VSCode 窗口 Open Folder 打开对应的 worktree 目录
# Step 3：各自独立开发、每切片 commit+push（遵循上方标准流程）
# Step 4：全部完成后，各自创建 PR 合入 main

gh pr create --base main --head feature/batch-{N1}-{name1} --title "..."
gh pr create --base main --head feature/batch-{N2}-{name2} --title "..."
gh pr create --base main --head feature/batch-{N3}-{name3} --title "..."

# Step 5：所有 PR 合入后，main = V1 完整版本
# Step 6：清理 worktree
git worktree remove ../CamelTv-w1
git worktree remove ../CamelTv-w2
git worktree remove ../CamelTv-w3
git branch -d feature/batch-{N1}-{name1} feature/batch-{N2}-{name2} feature/batch-{N3}-{name3}

# ═══════ V2 开发周期 ═══════

# Step 7：V2 窗口从最新 main（已含 V1 全部修复）切出
pwsh scripts/git/start-agent-team-task.ps1 -Kind feature -Task batch-{N4}-{name4} -Scope {模块4} -FrontendPort 5176 -BackendPort 8003
# ... 自动继承 V1 全部代码，无需手动拉取 V1 各分支
```

#### 防冲突规则（多窗口版）

1. **开工前声明模块范围**：每个窗口在开工时声明自己要改的模块/文件范围。如果与已有活跃窗口的模块重叠 → 协调合入顺序（先小后大）
2. **后合入者负责解决冲突**：如果两个窗口改了同一文件，后合入 main 的 PR 负责 `git merge origin/main` 解决冲突
3. **同一版本所有窗口从同一起点切出**：确保 `origin/main` 基线一致，避免起点不同导致的历史分叉
4. **每日至少一次 `git fetch origin main`**：感知远端变动，尽早发现冲突
5. **PR 按顺序合入**：变动范围小的先合、变动范围大的后合；如果窗口 A 的改动被窗口 B 依赖，则 A 先合入

#### Red Flag

- 🚨 多个 Agent Team 窗口共享同一个工作目录直接改代码 → 立即停止，创建 worktree 后重来
- 🚨 在某个 worktree 分支上 `git merge` 其他窗口的分支（而非通过 PR 合入 main）→ 破坏追溯性
- 🚨 跳过 worktree 直接用 `git stash` + `git checkout` 切换任务 → 代码覆盖风险极高

### 权限或安全策略阻塞处理

若 `git push` / `gh pr create` 被权限或安全策略阻塞，保留本地提交并向用户报告具体命令、错误和所需授权；禁止绕过安全策略。

## 标准工作流程

### 第 0 步（Dev 必做）：先读看板

多批次开发**必须**先读 `work-logs/kanbans/DEV-{项目名}.md`，确认当前停在哪个 Slice / 上次审批到哪 / 下一步做什么。看板不存在则从 `work-logs/kanbans/_TEMPLATE.md` 创建。开工前先向用户汇报进度：

```
📍 当前进度：[项目名] → Slice X → 🔄编码/✅审批 阶段
上次完成：[具体内容]   本次继续：[具体内容]
```

### 第 1–6 步：逐部门产出工件

1. **Product**：**先读 `C-CONDITIONS.md`**，检查上一批次遗留条件，在 PRD「非目标」段中明确哪些纳入本次、哪些豁免及理由。然后写问题陈述 → 成功指标 → 非目标 → 用户故事+验收标准（Given/When/Then）。先答「为什么用户关心」，再写需求。可用技能存在时再调用；技能不可用不得阻断交付，须在工件中记录替代核查方法。
2. **PM**：拆成 30–60 分钟可完成的任务，每个任务含描述/验收标准/涉及文件/参考。**不加 PRD 外的「豪华」需求**。
3. **Design**：只输出真实代码能落地的规范；若前端已实现则**反向回填**规范并做设计走查（用「文件:行号」锚点）。UI 细节走 `cameltv-ui-conventions` skill。API/模块接口设计不确定时，用 `design-an-interface` skill 并行生成多套方案对比；UI/状态机不确定时，用 `prototype` skill 做一次性原型验证后再写规范。
4. **Dev**：**TDD 红绿重构为默认编码方法**（先写失败测试→最小实现→重构→循环）。按切片（Slice）推进：📝方案→💻编码→🔍自测→✅审批→🚀合入。每 batch 结束更新看板。相关技能存在时用于补充检查，不得把“调用过技能”当作测试证据。
   - **KB 检索**：编码前检索知识库中本次修改模块的历史缺陷和已知问题模式（`chunk_type=platform_knowledge` + `defect_case`）。检索到的每个相关问题须在代码中明确处理或在 commit message 中注明豁免理由。
5. **QA**：默认立场「需要改进」。证据驱动——每个结论要有截图/日志/指标，不预设缺陷数量；零缺陷结论必须同时提供干净检出、类型检查、构建、自动化测试和关键用户路径证据。缺陷按 P0–P3 定级。
   - **最小硬门禁**：前端 `npm ci && npm run typecheck && npm run build`；后端 app 导入、`ruff check app --select F821`、Alembic 单头与 revision 长度测试。涉及模块的单元/集成测试必须执行并记录退出码。
   - **禁止静态代替执行**：文件存在、代码目测、工件齐全不能单独判定 PASS。
   - **KB 辅助定级**：出具 QA 报告前，检索知识库中与被测模块相关的历史缺陷模式。相似历史缺陷须在报告中列出，用于辅助缺陷定级（P0–P3）和评估回归风险。
   **遇到硬 bug 或性能回归时，走 `diagnose` skill 的纪律化诊断循环**（复现→最小化→假设→插桩→修→回归测试），不靠猜测修。
6. **Leader**：抽检各部门工件 → 给 APPROVED / 有条件通过 / 打回，并可设下一批次的 Leader 条件（C 编号）。**设定的 C 条件必须同步追加到 `C-CONDITIONS.md`**。Leader 只在 QA 硬门禁全绿、`audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过后给 APPROVED；没有运行日志、只有文档结论时必须打回。
   - **知识审计**：合入前验证 (a) 本批次是否产出了可入库的知识（设计决策、踩坑记录、新发现的问题模式）；(b) 如有，是否已通过 `ingest_platform_knowledge` 入库；(c) 本批次决策是否与 KB 中已有知识矛盾，如有矛盾须在 leader-verdict 中记录并说明取舍理由。
   **跨会话交接时用 `handoff` skill 压缩上下文为交接文档**，避免下一个 session 丢失进度。

### 第 7 步：合入 + 收尾

- 合入前：QA 判决 PASS + Leader APPROVED + PR 必需检查全部通过。若仓库尚未配置 required checks，禁止自动合并，必须由人工确认检查结果。
- 合入：**必须通过 PR**（`gh pr create`），禁止直接 `git merge` 到 main 再 push（本地 hook 与分支保护都会拒绝）。详见上方 [Git 工作流](#git-工作流强制)。
- 合入后：更新看板批次记录（产出+审批+耗时）；本地分支确认无未推送提交后删除，远端分支按仓库自动删除策略或人工决定。
- ⚠️ 工作树可能被外部进程周期性重置 → **每切片即刻 commit + push**（见 `[[worktree-reset-hazard]]`）。

## 工件命名规范

- 批次工件：`work-logs/batch-{name}-{prd-summary|pm-plan|design-spec|qa-report|leader-verdict}.md`
- Dev 看板：`work-logs/kanbans/DEV-{name}.md`（模板 `work-logs/kanbans/_TEMPLATE.md`）
- Leader 周报 / 深度审查：`work-logs/reviews/{LEADER|QA}-{name}.md`
- `{name}` 用短横线 kebab（如 `batch-18-wiki-diff`、`batch-e`），与看板、PR 保持一致。

## Red Flags — 停下来重做

- 跳过某个部门直接写代码 → 破坏可追溯性，违反门禁。
- QA 报告只有「通过」没有证据/缺陷清单 → 不可信，退回。
- PM 任务里塞了 PRD 没写的功能 → 范围蔓延，删掉。
- Dev 连续多 batch 看板「当前位置」没变 → 可能卡住/上下文丢失，先对齐再动手。
- Design 规范写「基于 Ant Design」→ 过时，真实栈是 shadcn/ui + Radix + Tailwind，见 `cameltv-ui-conventions`。

## KB 自动检索（RAG）

Agent Team 各部门执行任务时自动通过 RAG 检索知识库。检索优先级：
1. `platform_knowledge` —— 平台研发知识（问题模式、设计决策）
2. `defect_case` —— 历史缺陷
3. `test_case` —— 相关测试用例
4. `api_schema` —— 相关 API 接口

检索关键词从当前批次的 PRD/PM-plan/Design-spec 中的模块名、文件路径、API 端点自动提取。

## 关联

- [DEPARTMENTS.md](DEPARTMENTS.md) — 六部门角色与交付物模板
- `cameltv-ui-conventions` skill — 设计/前端组件与样式规范
- `cameltv-bug-guard` skill — 编码前避坑清单
- 嫁接单点利器：`tdd`（Dev） `diagnose`（QA） `review`（Leader） `grill-with-docs` `ubiquitous-language` `zoom-out`（Product） `design-an-interface` `prototype`（Design） `improve-codebase-architecture` `handoff`（Leader）
- [ADR-0014](../../../docs/adr/0014-single-main-trunk-ai-worktrees.md) — 单一主干与 worktree 隔离决策
