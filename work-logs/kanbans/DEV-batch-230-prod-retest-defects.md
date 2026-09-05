# 🗂️ Batch 230 — 生产复测缺陷修复 项目看板

> **用途**：追踪多批次开发的进度节点，防止上下文丢失。每次 Dev 部门启动时**必须先读取本看板**。
>
> **使用方式**：Dev Agent 在每个 batch 结束后更新本看板；下次启动时先读看板确认当前进度。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | Batch 230 — 2026-09-05 生产复测新录缺陷修复（DEF-20260905-001..007、-009） |
| **关联 PM 计划** | [work-logs/batch-230-prod-retest-defects-pm-plan.md](../batch-230-prod-retest-defects-pm-plan.md) |
| **关联 PRD** | [work-logs/batch-230-prod-retest-defects-prd-summary.md](../batch-230-prod-retest-defects-prd-summary.md) |
| **复测台账（证据源）** | [work-logs/evidence/sports-e2e-20260904/复测结论-20260905.md](../evidence/sports-e2e-20260904/复测结论-20260905.md) |
| **批次模式** | 完整批次（新增 `snapshot` 响应字段 / 新增版本任务列表视图 / 新增冻结与运行校验） |
| **分支** | `feature/batch-230-prod-retest-defects`（base `origin/main` = `9c721bc6`） |
| **worktree** | `F:/CamelTv-worktrees/claude-batch-230-prod-retest-defects`（executor=claude, workflow=agent-team） |
| **端口** | frontend 5231 / backend 8231 |
| **总预估工时** | 9.5h |
| **已用批次** | 1 批（7 个 Slice） |
| **看板创建** | 2026-09-05 |
| **最后更新** | 2026-09-05 |

---

## 🎯 交付切片进度

> 每个 Slice 经过：📝方案 → 💻编码 → 🔍自测 → ✅审批 → 🚀合入。标注当前停留位置 ⬅️

| # | Slice | 缺陷 | 优先级 | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|------|:------:|:----:|:----:|:----:|:----:|:----:|------|
| 1 | S1 契约快照可读 + 非空校验 | DEF-20260905-001 | P1 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 提交 `892df035`；后端回传已解析 `snapshot` 对象 + 空规则冻结拦截（HTTP 400，非 409）+ 前端 `ContractSnapshotView` 渲染规则/产出 + 契约页错误态 |
| 2 | S2 版本任务列表可达 | DEF-20260905-002 | P1 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 提交 `1ea77b47`；路由拆三条 + 新列表页 + `VersionTaskListItem` 补 `coverage`/`updated_at` + `statusLabels.ts` 字典集中 + 侧栏两处子项 Link 化（改法未互换） |
| 3 | S3 一键运行阻塞可见 | DEF-20260905-003 | P1 | ⏳ ⬅️ | ⏳ | ⏳ | ⏳ | ⏳ | **当前起点**；依赖 S2（同域文件已就绪）；`blocked` 原因复用 `failures`（`kind:"plan"`）+ 前端阻断提示 |
| 4 | S4 AI 自动发现假成功 | DEF-20260905-004 | P2 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | `discoverAiModels` 类型补 `ok/error`，前端按 `ok` 分支 |
| 5 | S5 缺陷搜索支持编号 | DEF-20260905-005 | P2 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | `or_(title, defect_id)`，`project_id` 隔离在 OR 之外 |
| 6 | S6 范围评审审计操作人 | DEF-20260905-006 | P2 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | `scope/service.py::_audit` 硬编码 `username=""` 修正 + 同类点排查 |
| 7 | S7 拼写 + 404 横幅边界 | DEF-20260905-007、-009 | P3 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 S1（同文件 `missions/contract.tsx`） |
| — | DEF-20260905-008 | （已撤回） | — | ❌ | ❌ | ❌ | ❌ | ❌ | 前端本已有 `toast.success('契约已生成')`；误报，取证方法缺陷已写入 PRD §1.1 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 230 — S3 一键运行阻塞可见
├── 已完成: Product PRD（550a5ce5）、PM Plan（b6af5c98）、Dev 看板 + 复测证据纳管（00a30b66）、
│           Design Spec（185c0d82，含 5 项决议 + 11 条走查发现）、看板定位（819de4b5）
│           Dev S1 契约快照可读 + 非空校验（892df035，11 文件）
│           Dev S2 版本任务列表可达 + 侧栏子项链接化（1ea77b47，12 文件）
├── 🔄 进行中: 无
├── ⏳ 待审批: S1、S2（等 QA 硬门禁复核 + Leader 终判）
└── ⏳ 下一步: Dev 进入 S3 编码（Task 3.1 起）
              Design 已决议 PM 下放的两项：
              D1 = S3 blocked 原因**复用 failures**（新增 kind:"plan"），不加顶层 reason 字段、不做 Alembic 迁移
              D2 = S7 横幅选 **(b) useMatches() splat 抑制**，不改前缀匹配（已对全量路由表验证无真实路由越界命中）
              另决议 D3（/version-tasks 变列表页、向导迁 /new）→ S2 已落地、
              D4（回传已解析 snapshot 对象）→ S1 已落地、
              D5（_audit 内部按 user_id 反查 nickname，不改服务签名）→ S6 待落地
              §6 放行条件执行情况：
                条件 2（空契约拦截必须用 400 而非 409）✅ S1 已满足
                条件 4（侧栏两处改法不得互换）✅ S2 已满足，并有 NavSubItemLinks.test.tsx 锁定
                其余条件继续约束 S3–S7
              ⚠️ 徽标一律走 StatusBadge / Badge tone，禁止手写裸色阶与 dark: 变体（§0 Token 架构）
              ⚠️ S3 回归面：`task.status` 由无条件 `executed` 改为按 run_status 条件化，
                 必须跑版本任务全量 pytest 并记录退出码（coverage 回写 C217-1、
                 releaseTask / buildReleasePackage / transitionVersionTask 的合法输入集合）
```

> **KB 检索记录**：编码前对 `platform_knowledge` / `defect_case` 检索契约冻结、版本任务、
> 侧栏导航相关条目均无命中。替代核查方法 = 直接读源码定位根因（file:line 写进 Design Spec）
> + `scan-common-bugs.ps1`（HARD 0）+ 既有后端/前端全量测试套件兜底。

---

## 📜 批次记录

### Batch 230 / Product — PRD Summary (2026-09-05)
- **产出**: `work-logs/batch-230-prod-retest-defects-prd-summary.md`（提交 `550a5ce5`）
- **要点**: 判定为完整批次；8 条缺陷逐条映射生产证据 + 代码根因（file:line）；§1.1 记录 DEF-20260905-008 误报撤回与流程教训（「无提示／无反馈」类结论必须用事件监听而非事后快照取证）
- **审批**: 自审通过，待 Leader 终判

### Batch 230 / PM — PM Plan (2026-09-05)
- **产出**: `work-logs/batch-230-prod-retest-defects-pm-plan.md`（提交 `b6af5c98`）
- **要点**: 7 Slice / 26 Task / 9.5h；Slice 依赖顺序 S2→S3（同域）、S1→S7（同文件 `missions/contract.tsx`）；两处显式下放给 Design 的决议项
- **审批**: 自审通过，待 Leader 终判

### Batch 230 / Dev — 看板创建 (2026-09-05)
- **产出**: `work-logs/kanbans/DEV-batch-230-prod-retest-defects.md`（本文件）
- **耗时**: 0.2h

### Batch 230 / Design — Design Spec (2026-09-05)
- **产出**: `work-logs/batch-230-prod-retest-defects-design-spec.md`（提交 `185c0d82`）
- **要点**: 5 项决议（D1–D5）+ 11 条走查发现（file:line 锚点）；§0 明确 Badge `tone` / StatusBadge `variant` 的 Token 架构；§6 给出 7 条放行条件
- **审批**: 自审通过，待 Leader 终判

### Batch 230 / Dev — S1 契约快照可读 + 非空校验 (2026-09-05)
- **产出**: 提交 `892df035`（11 文件）
- **实现**: `contract/schemas.py` 回传已解析 `snapshot: ContractSnapshot | None`（D4）；`contract/service.py` freeze 前置校验，空规则抛 `APIException(code=400, msg="CONTRACT_FREEZE_EMPTY: ...", http_status=400)`（§6 条件 2：必须 400 而非 409）；`api/v2/mission_contracts.py` 补 `response_model=R[list[ContractVersionRead]]`；前端新增 `pages/missions/ContractSnapshotView.tsx` 渲染规则/产出，`contract.tsx` 补 ErrorState 与冻结阻断提示
- **自测**: 后端 `pytest -q` 全绿（exit 0）、`ruff check app --select F821` All checks passed、`import app.main` OK；前端 `npm run typecheck` exit 0、`npm run build` 成功、`npx vitest run` 全绿（exit 0）；`scan-common-bugs.ps1` HARD 0
- **耗时**: 1.6h
- **审批**: 自测通过，待 QA 复核 + Leader 终判

### Batch 230 / Dev — S2 版本任务列表可达 (2026-09-05)
- **产出**: 提交 `1ea77b47`（12 文件，+607 / −22）
- **实现**: 路由拆三条（`version-tasks` 列表 / `version-tasks/new` 向导 / `version-tasks/:taskId` 详情，D3）；新增 `pages/version-tasks/list.tsx` 与 `statusLabels.ts` 字典集中（消除裸英文状态标签的历史返工点）；后端 `schemas/version_task.py::VersionTaskListItem` 补 `coverage`（`_json_to_dict` 容错）与 `updated_at`；`api/versionTask.ts::listVersionTasks` 改回 `VersionTaskPage` 并支持分页
- **Dev 自主增项（须在 QA 报告披露）**: 列表页加了分页控件——后端默认 `page_size=20` 且原实现丢弃 `total`，不分页会静默截断成「新缺陷」
- **侧栏两处改法（§6 条件 4，未互换）**: `MainNavRows.tsx` 删除 onClick（`navigateMenu` 只是纯 `navigate`，保留会双跳）；`NavigationMenuItems.tsx` 保留 `closeMobile`（移动端需收起抽屉）；由新增 `layouts/__tests__/NavSubItemLinks.test.tsx`（3 测试）锁定，含暴露 SidebarProvider 内部抽屉状态的 `MobileDrawerProbe`
- **自测**: 后端全量 `pytest -q` = 2431 passed / 49 skipped / 1 xfailed（exit 0）、`ruff F821` 通过、`pytest tests/test_version_task.py -q` = 34 passed；前端 `typecheck` exit 0、`build` ✓ 10.50s、全量 `vitest run` = 143 files / 647 tests passed（exit 0）、定向 `version-tasks + layouts` = 12 files / 67 passed、`eslint` 10 个改动文件 exit 0；`scan-common-bugs.ps1` HARD 0（WARN 330 均不在本批改动文件内）
- **耗时**: 2.1h
- **审批**: 自测通过，待 QA 复核 + Leader 终判

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| S1 契约内容仍为空壳的能力前提 | P2 | 本批只让「已生成的快照」可读 + 拦截「空规则冻结」；确定性 provider 能否对真实范围项产出非空规则取决于 `scope_key` 是否落地，若无 AI Key 仍可能生成 0 条规则——此时新校验会正确拦截并给出提示，属于预期行为而非新缺陷 | QA 复测时须区分 | 2026-09-05 |
| S2 与 DEF-20260904-001 的边界 | P2 | 侧栏 `href` 修复同时消除 DEF-20260904-001（5 个锚点 `href=null`）的一部分；QA 报告须写明本批只覆盖「侧栏子菜单不可达」，004-001 其余锚点留待后续批次 | QA | 2026-09-05 |
| S3 状态机回归 | P2 | `task.status` 从无条件 `executed` 改为按条件 `blocked`，可能影响既有已执行任务的展示与放行判定；须跑版本任务相关全量回归 | Dev + QA | 2026-09-05 |
| S6 审计字段回填 | P3 | 历史审计记录 `username` 为空，本批只修正写入侧，不做数据回填（PRD 非目标已记录） | — | 2026-09-05 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD Summary | [batch-230-prod-retest-defects-prd-summary.md](../batch-230-prod-retest-defects-prd-summary.md) | ✅ |
| PM Plan | [batch-230-prod-retest-defects-pm-plan.md](../batch-230-prod-retest-defects-pm-plan.md) | ✅ |
| Design Spec | [batch-230-prod-retest-defects-design-spec.md](../batch-230-prod-retest-defects-design-spec.md) | ✅ |
| QA Report | [batch-230-prod-retest-defects-qa-report.md](../batch-230-prod-retest-defects-qa-report.md) | ⏳ |
| Leader Verdict | [batch-230-prod-retest-defects-leader-verdict.md](../batch-230-prod-retest-defects-leader-verdict.md) | ⏳ |
| 复测台账（缺陷来源） | [evidence/sports-e2e-20260904/复测结论-20260905.md](../evidence/sports-e2e-20260904/复测结论-20260905.md) | ✅ |
| 待提供清单 | [evidence/sports-e2e-20260904/待提供清单-20260904.md](../evidence/sports-e2e-20260904/待提供清单-20260904.md) | ✅ |
| C 条件台账 | [C-CONDITIONS.md](../../C-CONDITIONS.md) | 🔄 |
| UI 规范技能 | `.agents/skills/cameltv-ui-conventions/`（控制 worktree，`.gitignore` 未纳管） | 🔄 |
| 避坑技能 | `.agents/skills/cameltv-bug-guard/`（同上） | 🔄 |
