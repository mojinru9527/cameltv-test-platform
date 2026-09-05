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
| 3 | S3 一键运行阻塞可见 | DEF-20260905-003 | P1 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 提交 `ae4f37c2` + `8f33ee80`；合成 `kind="plan"` 失败项（D1）+ `task.status` 去无条件化 + 前端按 `run.status` 三分支 + 运行状态徽标 + kind 中文/tone 分级 |
| 4 | S4 AI 自动发现假成功 | DEF-20260905-004 | P2 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 提交 `54f35c9a`；`discoverAiModels` 类型补 `ok/error/kind/count`（**未声明 `detail`**）+ `handleDiscoverModels` 在 `res.ok === false` 早退弹错误（不给 action，避免嵌套抽屉）+ 成功文案改用 `res.count` 与合并总数区分 |
| 5 | S5 缺陷搜索支持编号 | DEF-20260905-005 | P2 | ⏳ ⬅️ | ⏳ | ⏳ | ⏳ | ⏳ | **当前起点**；`or_(title.contains, defect_id.contains)`，⚠️ §6 条件 5：`project_id` 过滤必须在 `or_` **之外**，且必须有「keyword 命中另一项目 defect_id 返回空」的跨项目隔离测试 |
| 6 | S6 范围评审审计操作人 | DEF-20260905-006 | P2 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | `scope/service.py::_audit` 硬编码 `username=""` 修正 + 同类点排查 |
| 7 | S7 拼写 + 404 横幅边界 | DEF-20260905-007、-009 | P3 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 S1（同文件 `missions/contract.tsx`） |
| — | DEF-20260905-008 | （已撤回） | — | ❌ | ❌ | ❌ | ❌ | ❌ | 前端本已有 `toast.success('契约已生成')`；误报，取证方法缺陷已写入 PRD §1.1 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 230 — S5 缺陷搜索支持编号
├── 已完成: Product PRD（550a5ce5）、PM Plan（b6af5c98）、Dev 看板 + 复测证据纳管（00a30b66）、
│           Design Spec（185c0d82，含 5 项决议 + 11 条走查发现）、看板定位（819de4b5、6f5181b6、c0b6683e）
│           Dev S1 契约快照可读 + 非空校验（892df035，11 文件）
│           Dev S2 版本任务列表可达 + 侧栏子项链接化（1ea77b47，12 文件）
│           Dev S3 一键运行阻塞可见（ae4f37c2 代码 + 8f33ee80 窄屏 flex-wrap）
│           Dev S4 AI 自动发现假成功（54f35c9a，3 文件）
├── 🔄 进行中: 无
├── ⏳ 待审批: S1、S2、S3、S4（等 QA 硬门禁复核 + Leader 终判）
└── ⏳ 下一步: Dev 进入 S5 编码（Task 5.1 起）
              Design 已决议 PM 下放的两项：
              D1 = S3 blocked 原因**复用 failures**（新增 kind:"plan"），不加顶层 reason 字段、不做 Alembic 迁移 → ✅ S3 已落地
              D2 = S7 横幅选 **(b) useMatches() splat 抑制**，不改前缀匹配（已对全量路由表验证无真实路由越界命中）
              另决议 D3（/version-tasks 变列表页、向导迁 /new）→ S2 已落地、
              D4（回传已解析 snapshot 对象）→ S1 已落地、
              D5（_audit 内部按 user_id 反查 nickname，不改服务签名）→ S6 待落地
              §6 放行条件执行情况：
                条件 2（空契约拦截必须用 400 而非 409）✅ S1 已满足
                条件 4（侧栏两处改法不得互换）✅ S2 已满足，并有 NavSubItemLinks.test.tsx 锁定
                条件 5（project_id 过滤在 or_ 之外 + 跨项目隔离测试）⏳ 约束 S5，本切片唯一正确性风险点
                条件 6（S7 四条路径实测）⏳ 约束 S7；条件 1、3、7 已随 S1/S3 落地
              ⚠️ 徽标一律走 StatusBadge / Badge tone，禁止手写裸色阶与 dark: 变体（§0 Token 架构）
              ✅ S4 关键约束已兑现：`discoverAiModels` 未声明 `detail`（后端 discover 分支从不返回），
                 失败早退不落入合并分支，成功文案用 `res.count` 而非 `merged.length`
              ✅ S3 回归面已清：全量后端 pytest 2435 passed / 49 skipped / 1 xfailed（exit 0，581s），
                 coverage 回写（C217-1）、releaseTask / buildReleasePackage / transitionVersionTask
                 与 onboarding 基线全部通过；onboarding 只读 run.status 不读 task.status，未受影响
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

### Batch 230 / Dev — S3 一键运行阻塞可见 (2026-09-05)
- **产出**: 提交 `ae4f37c2`（代码，6 文件）+ `8f33ee80`（窄屏 `flex-wrap`，Design Spec §3）
- **实现**: 后端合成 `kind="plan"` 失败项承载阻塞原因（D1）；计数算术不动（`total`/`blocked` 保持 0，伪造 `blocked=1` 会造成 `blocked > total`）；`task.status` 去无条件化 → `"executed" if run_status in ("done","failed") else "blocked"`。前端 `handleRun` 按 `run.status` 三分支（禁止无条件 success）；顶栏补运行状态徽标；覆盖在 `total=0` 时显 `—`；失败分类走中文 + tone 分级（只有 `business` 染红）；含 `plan`/`environment` 时标题改「未通过 / 阻塞明细」；证据状态换 `StatusBadge`（顺带纠正 `skipped` 被染红与裸英文）；`api/versionTask.ts` 补 `failures[].http_status`、`evidence[].status` 收窄为 `StatusVariant`
- **⚠️ Design Spec 未覆盖、Dev 编码中发现并闭合的两处可达回归（QA 须复核、Leader 须终判）**:
  1. `FAILURE_KINDS` / `FAILURE_KIND_LABEL` 缺 `plan` → 合成项在前端同样渲染「转缺陷草稿」按钮，点击会在 `create_defect_draft` 抛「未知失败类型：plan」（label 缺失还会 `KeyError`）。已补 `plan`
  2. `release_task` 准入集合只有 `executed`/`verdict` → `task.status=blocked` 后「打回／有条件放行」（前端始终可点）会报「当前状态 blocked 不可放行」，而被阻塞恰恰是最需要打回的场景。已补 `blocked`；`verdict=="pass"` 仍由 coverage 校验独立拦截，放宽准入不会让未跑通的任务被放行（已加测试锁定）
- **Dev 文案细化（须披露）**: Design Spec 给的 blocked 文案是固定串「没有可执行的方案条目」，但 `run.status=blocked` 另有两类成因（条目 `not_run` 累计、全 skipped），固定串会误报。改为按 `failures` 是否含 `kind="plan"` 分流，环境侧报「N 项未能执行」，两侧均有测试
- **自测**: 后端 `test_version_task` 38 passed、`test_mainline_walkthrough` 5 passed、**全量 `pytest -q` = 2435 passed / 49 skipped / 1 xfailed（exit 0，581s）**、`ruff F821` 通过、`import app.main` OK；前端 `typecheck`/`build` exit 0、**全量 `vitest run` = 144 files / 655 tests passed（exit 0）**、定向 `version-tasks` 3 files 16 passed、`eslint` 4 个改动文件 exit 0；`scan-common-bugs.ps1` HARD 0 且 S3 文件零命中
- **测试环境注意**: 全量 vitest 首轮出现 6 个**无关文件**（theme-lab / DebugTab / ReviewPage / UiRunDetail）超时失败，单独复跑 4 文件全绿（857ms vs 6500ms），`--maxWorkers=3` 重跑全量 655 全绿 → 判定为 worker 资源争用抖动，非回归。QA 复现时建议同样限并发
- **耗时**: 1.9h
- **审批**: 自测通过，待 QA 复核 + Leader 终判

### Batch 230 / Dev — S4 AI 自动发现假成功 (2026-09-05)
- **产出**: 提交 `54f35c9a`（3 文件，+80 / −3）
- **TDD**: 先写两条失败用例（`ok=false` 早退 / 成功用 `count` 报数）确认红（2 failed / 4 passed），再改实现转绿（6 passed）
- **实现**: `api/aiConfig.ts::discoverAiModels` 返回类型补 `ok/models?/count?/error?/kind?`——后端 `ai_config_service.py:272-312` 业务失败仍走 HTTP 200 且返回 `{ok:false, error}`，旧类型只声明 `{models}` 使调用方无从判定失败；`pages/ai-config/index.tsx::handleDiscoverModels` 在 `res.ok === false` 时 `toast.error(res.error || '模型发现失败', {duration: 10_000})` 后 **`return`**，不再落入合并分支（失败时 `res.models` 为 `undefined`，与模板既有模型合并出非空清单 → 弹绿色成功提示，即 DEF-20260905-004 的假成功）；成功文案由「已拉取厂商全量模型（共 ${merged.length} 个）」改为「已拉取 ${res.count} 个模型，合并后共 ${merged.length} 个」，把「实际拉取数」与「合并后总数」分开
- **§6/Design 约束兑现**: ①**未声明 `detail`**（discover 分支从不返回，声明后端永不发送的字段＝假契约，正是本缺陷成因类型，已在类型里写注释留痕）；②**不给 action 按钮**（`:207-215` 的「更新密钥」是打开*已存在*提供方的编辑抽屉，而 discover 发生在新建/编辑抽屉内部，再开一次会嵌套），测试用 `toHaveBeenCalledWith(msg, {duration: 10_000})` 精确锁定参数形态；③`:255-257` 的 `merged.length === 0 → toast.error('未发现可用模型')` 按 Spec 保留不动（`ok===true` 后后端保证 `count ≥ 1`，该分支实际不可达，删除属无关清理）；④后端不改（`R.ok(...)` 无条件包裹业务失败是全仓系统性模式，PRD 已列非目标）
- **走查确认**: `discoverAiModels` 是唯一消费端（全仓 grep 仅 `pages/ai-config/index.tsx:249`），类型收紧无其它波及面
- **自测**: `npx vitest run src/pages/ai-config` = 6 passed（exit 0）；`npm run typecheck` exit 0；`npm run build` ✓ 9.67s exit 0；`npx eslint` 3 个改动文件 exit 0；`scan-common-bugs.ps1` HARD 0 / WARN 330（与 S3 基线一致，S4 文件零命中）。**未跑后端测试**：本切片零后端改动。**未跑全量 vitest**：定向套件已覆盖唯一消费端，全量留到 S7 结束后统一跑（`--maxWorkers=3`），避免与后端 pytest 争用 worker 造成 S3 那类超时抖动
- **耗时**: 0.5h
- **审批**: 自测通过，待 QA 复核 + Leader 终判

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| S1 契约内容仍为空壳的能力前提 | P2 | 本批只让「已生成的快照」可读 + 拦截「空规则冻结」；确定性 provider 能否对真实范围项产出非空规则取决于 `scope_key` 是否落地，若无 AI Key 仍可能生成 0 条规则——此时新校验会正确拦截并给出提示，属于预期行为而非新缺陷 | QA 复测时须区分 | 2026-09-05 |
| S2 与 DEF-20260904-001 的边界 | P2 | 侧栏 `href` 修复同时消除 DEF-20260904-001（5 个锚点 `href=null`）的一部分；QA 报告须写明本批只覆盖「侧栏子菜单不可达」，004-001 其余锚点留待后续批次 | QA | 2026-09-05 |
| S3 状态机回归 | ✅ 已清 | `task.status` 从无条件 `executed` 改为按条件 `blocked`；Dev 已跑全量后端 `pytest -q` = 2435 passed / 49 skipped / 1 xfailed（exit 0），onboarding 只读 `run.status` 未受影响。**遗留关注点**：Dev 自主闭合的两处（`FAILURE_KINDS` 补 `plan`、`release_task` 准入补 `blocked`）超出 Design Spec 范围，QA 须在真实界面复核「转缺陷草稿」与「打回」两条路径 | QA | 2026-09-05 |
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
