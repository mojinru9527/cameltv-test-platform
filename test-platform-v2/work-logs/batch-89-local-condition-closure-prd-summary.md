# Batch 89 — PRD Summary（C55-5-P2 响应式回归 / C81-1 WARN 周审计 / C64-2 仓库清理 / C21-P1-2 单测验证）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

## 0. 批次模式判定（C75-1 强制）

```markdown
mode: full
判定理由: 响应式回归可能引出前端修复（新行为），并含仓库边界变更（删除误提交文件 + repo-boundaries.json 同步）；
按 pipeline-modes.md「拿不准按完整」执行六部门。
```

## 1. 问题陈述

### C55-5-P2 — tablet/mobile 响应式回归缺口

平台生产级验收的 PC 视口（1440×900）已闭环（batch-56），但 tablet `768×1024` 与 mobile `390×844` 的响应式、溢出与完整可操作性回归从未系统性执行（P2 非阻断项）。用户关心点：运营同学可能在平板上做用例维护、在手机上查看报告/缺陷；布局溢出或按钮不可点会直接阻塞移动端使用。

### C81-1 — WARN 周审计节奏

`run-warn-audit.ps1`（batch-82 交付）要求每周或每 10 批次执行一次基线对比 + 趋势表追加。距上次（batch-86，2026-08-04）已间隔 3 批次，且 batch-88 新增了代码——需执行周审计确认无新增 WARN 类别。

### C64-2 — 根目录误提交文件残留

根目录存在两个 `pective pipeline — Agent Team work-logs + 10 TypeScript fixes + domain CRUD API` 误提交文件（batch-64 登记，待独立审计删除），且 `repo-boundaries.json` 仍声明这两个路径。它们污染仓库根目录、混淆 CI 分类器与拆仓边界。

### C21-P1-2 — 三服务单测（追踪器未关闭）

`failure_analyzer` / `report_aggregator` / `task_worker` 三个服务的单测**已存在**（commit `a3608b8`，Batch 41 引入），本批实测 103 项全部通过，但 C-CONDITIONS.md 仍标记 Open——属追踪器未回写，本批以证据关闭。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| C55-5-P2 | PC 1440×900 已闭环；tablet/mobile 未系统验证 | 关键页面在 768×1024 与 390×844 下：无水平溢出、主要操作可点击、无遮挡；截图证据 + 自动化断言 | 本批 |
| C81-1 | 209 WARN（batch-86 基线） | run-warn-audit 执行；趋势表追加；HARD=0；无新增类别（如有则归因） | 本批 |
| C64-2 | 2 个误提交文件在根目录 | 文件删除 + repo-boundaries.json 同步 + validate_repo_boundaries.py --check 全绿 | 本批 |
| C21-P1-2 | 追踪器 Open | 三服务单测 103/103 通过证据 + C-CONDITIONS 关闭（commit a3608b8 + PR #124 同批） | 本批 |
| 门禁 | — | ruff F821、pytest 全量、vitest/build、scan HARD=0、audit-cconditions 0 硬错 | push 前 |

## 3. 非目标（本次不做）

- **不处理外部项**：iOS 真机（CP-C2/C84-1）、Test5（C74-2/C65-3/C63-2）、staging 类（C27-*）、生产账号（C31-*）维持 Deferred。
- **不做大规模前端重设计**：响应式回归只修发现的具体溢出/可操作性缺陷，不做布局重构。
- **不新增依赖**：复用 Playwright、现有 e2e 基建与 scan 工具。
- **不改 WARN 豁免清单类别**：周审计只对比基线，不重分类既有豁免项（C80-1 语义不变）。

### C 条件纳入/豁免清单

| C 条件 | 处理 |
|--------|------|
| C55-5-P2 / C81-1 / C64-2 / C21-P1-2 | **纳入**本批 |
| C75-1 | 本 PRD 记录 `mode: full` |
| C75-2 | Leader 判决含「流程回写」 |
| C75-3 | push 前 audit-cconditions -RequireLatestBatch 0 硬错 |
| C76-2 / C78-1 / C80-1 / C86-1 | 本批遵守（scan/pytest/404 双约定） |
| C21-P1-3 / C21-P1-5 / C21-P2 / C21-P3 等其余孤儿 | 不在本批（豁免理由：与本批四项无关，后续批次处理） |

## 4. 用户故事 + 验收标准

- As a **移动端/平板用户**, I want 关键页面在 768×1024 与 390×844 下完整可读可操作，so that 我不用切 PC 也能完成查看与操作。
  - Given Playwright 以 tablet 视口打开登录/工作台/用例/计划/报告/缺陷/定时/知识页，When 检查横向溢出与元素可点，Then 无 body 水平溢出、主按钮可点击、无元素相互遮挡。
  - Given mobile 视口打开同一组页面，When 检查导航与弹窗，Then 侧边栏/弹窗可开合、表单可输入、滚动正常。

- As a **仓库维护者**, I want 根目录误提交文件被删除且边界事实源同步，so that CI 分类与拆仓不受污染。
  - Given 删除两个 `pective pipeline — ...` 文件并更新 repo-boundaries.json，When 运行 `validate_repo_boundaries.py --check`，Then 全绿。

- As a **质量守门人**, I want WARN 基线周审计与三服务单测证据入库，so that 技术债趋势可见、旧条件不再误挂 Open。

## 5. 技术考量

1. **C55-5-P2**：新增 `e2e/batch89-responsive.spec.ts`（Playwright），以 `viewport` 768×1024 / 390×844 覆盖关键页面：登录、工作台、用例列表、计划、报告、缺陷、定时任务、知识中心；断言 `document.documentElement.scrollWidth <= innerWidth`（无水平溢出）+ 主操作元素可点击；截图存 `evidence/batch-89/`。发现的缺陷按 P0–P3 定级并修复。
2. **C81-1**：`run-warn-audit.ps1 -BatchLabel "batch-89"`；结果追加 `docs/agent-team/warn-inventory.md` 趋势表。
3. **C64-2**：删除两个误提交文件（第二个文件名含不可见字符 `\uF022`，用 LiteralPath/通配确认后删），`repo-boundaries.json` 移除对应两行；`validate_repo_boundaries.py --check` 验证。
4. **C21-P1-2**：直接以 commit `a3608b8` + 本批 103/103 执行为证据关闭；如发现测试缺口再补（预期无）。
5. **风险**：Playwright 需本机 chromium（batch-60+ 已验证可用）；响应式回归可能发现若干 P2/P3 缺陷需修复，属预期。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批 worktree 验收 | 平台用户 | 四条件证据 + 门禁全绿 |
| Draft PR → checks | CI | required checks 全绿 + 审计通过 |
| 合入 main 后 | 全平台 | C55-5-P2/C81-1/C64-2/C21-P1-2 按证据关闭 |

## 7. 技能使用

- `cameltv-agent-team` → 本流水线工件
- `cameltv-api-test` / `playwright-skill` → 响应式回归执行与证据
- `cameltv-ui-conventions` → 若发现前端样式缺陷，按规范修复
- `cameltv-bug-guard` → 编码/删除文件前避坑
