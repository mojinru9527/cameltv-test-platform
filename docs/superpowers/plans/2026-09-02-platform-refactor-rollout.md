# 平台重构落地路线图（B1–B15）Implementation Plan

> **For agentic workers:** 本计划按仓库 agent-team 批次执行。每个批次 = 一个独立 worktree/分支 + 一次新 Codex 会话；步骤用 `- [ ]` 跟踪。执行器统一 = **Codex**（用户已确认）；推送/PR/合入已获用户一次总授权（2026-09-02）。
> **目标:** 把测试平台重构为「AI 版本验收工作台 + 傻瓜化界面」，落地 ABCD 去留白名单与知识闭环。
> **架构:** 引擎（AITDE/DSH/资产）保留为底层，其上重构「双界面薄壳」；主链路 = 版本验收任务唯一事实源；知识为副产品自动沉淀。
> **事实源:** `docs/platform-refactor/`（定位/白名单/术语/傻瓜化规范）与本路线图。
> **Saved:** 2026-09-02

---

## 0. 批次 ↔ 真实仓库号映射（B1=Batch 211 起）

| 逻辑批次 | 真实批次/分支 | 模式 | 阶段 |
|---------|--------------|------|------|
| B1 | batch-211-refactor-baseline-docs | 轻量（纯文档） | M0 |
| B2 | batch-212-menu-convergence | 完整（配置+前端） | M0 |
| B3 | batch-213-home-todo | 完整（前后端） | M0 |
| B4 | batch-214-foolproof-components | 完整（前后端） | M0 |
| B5 | batch-215-dead-code-cleanup | 完整（后端+清理） | M0 |
| B6 | batch-216-version-task-model | 完整（后端+DB） | M1 |
| B7 | batch-217-version-task-wizard | 完整（前后端） | M1 |
| B8 | batch-218-execution-evidence-view | 完整（前后端） | M1 |
| B9 | batch-219-acceptance-verdict | 完整（前后端） | M1 |
| B10 | batch-220-real-version-walkthrough | 轻量（验收+修复） | M1 |
| B11 | batch-221-knowledge-pipeline | 完整（后端+DB） | M2 |
| B12 | batch-222-smart-regression-defect | 完整（前后端） | M2 |
| B13 | batch-223-compare-metrics | 完整（前后端+DB） | M2 |
| B14 | batch-224-model-convergence | 完整（后端+DB） | M2 |
| B15 | batch-225-business-onboarding | 完整（前后端+DB） | M3 |

## 1. 每批次执行协议（用户定稿，全批强制）

1. **执行器**：全部 Codex（无需再问）；
2. **新会话**：每个批次在本地**新开一个 Codex 会话**执行，防上下文超长溢出；上一会话结束前必须输出「交接备忘录」（本文件更新 + 会话摘要）；
3. **worktree/分支**：从最新 `origin/main` 创建 `feature/batch-{N}-{name}`（`pwsh scripts/git/start-agent-team-task.ps1 -Executor codex -UserConfirmedExecutor -Kind feature -Task batch-{N}-{name} -Scope ... -FrontendPort {空闲} -BackendPort {空闲}`）；端口与已存在 worktree 冲突时换空闲端口；
4. **范围**：只提交本批文件；完成前仅本地提交；
5. **分支完成审计（强制）**：每批开发完做一次**代码实现逻辑审计**；涉及执行/数据的验证**尽可能使用体育真实数据 mock**，防止假成功；审计结论写入 QA 报告；
6. **未完成事项**：若本批分支未处理完，逐条记录到「交接区」（本文件 §5），交给下一批次/下一分支继续；
7. **推送与合入（已授权）**：`git push -u origin feature/batch-{N}-{name}` → `gh pr create --draft --base main` → `audit-ai-pr.ps1` 基础审计 → 等 required checks → `audit-ai-pr.ps1 -RequireSuccessfulChecks` → squash merge → 从 main 更新后清理 worktree；一个接一个，直到 B15；
8. **每批门禁**：QA 硬门禁（按变更域 typecheck/build/ruff/受影响 pytest+vitest/Alembic 单头）+ 小白走查证据 + C 条件 + Leader 判决 + 复盘卡。

## 2. 批次明细与出口标准

| 批 | 内容 | 出口标准 |
|----|------|---------|
| B1(batch-211) 本文档批 | 定位/白名单/术语/傻瓜化规范/路线图落盘 + PRD-lite/QA/Verdict/看板 | 方案文档合入 main，B2 可开工 |
| B2(batch-212) 入口收敛 | 角色化菜单（tester 5 项 + 资产与更多/专家/系统）；C 级入口下架（Playground Tab、special/perftest 宣称、知识专家 Tab）；**删除旧测试计划独立入口**；用例/接口/UI 保留为资产 | tester 默认只见 5 项；旧 URL 不 404（只藏/重定向）；菜单/权限/命令面板三处对账 |
| B3(batch-213) 首页我的待办 | 工作台改「我的待办」（待审/在跑/失败/待放行聚合）；dashboard API | 3 分钟说出今天点哪；无埋点 |
| B4(batch-214) 傻瓜化组件层 | PageIntro/TermTip/EmptyStateGuide/StepWizard/AskAi 助手 MVP；页面一句话+空态教学 | 全站列表页空态有教学；问「这页干嘛」有业务化回答 |
| B5(batch-215) 死代码清理 | V1 工具删除、special/perftest 冻结代码、无引用页面/组件/路由/服务/文档删除、根目录 `_tmp_*`/重复文档清理 | rg 引用审计零遗漏；全量 pytest+typecheck+build 绿；删除项可回滚 |
| B6(batch-216) 版本任务模型 | VersionTask 统一事实源（表/状态机/关联 requirement、release_bundle、executions、defect、verdict）；旧数据兼容映射 | 单头 migration + 可逆 drill；旧数据可读不双写 |
| B7(batch-217) 建任务向导+审核 | 3 步向导 + 审核面板（采纳/改/删/追问 + 置信度 + 待确认） | 拖入需求→可审方案→逐条确认，无引擎术语 |
| B8(batch-218) 执行与证据 | 一键运行版本任务 + 进度 + 证据回放 + 失败自动分类→缺陷草稿 | 一键跑完；失败四分类正确；证据可回放 |
| B9(batch-219) 放行与证据包 | 放行页（覆盖/通过率/风险）+ 绑定 release_bundle + 报告/通知 | 一个版本产出可分享放行证据包 |
| B10(batch-220) 真实走查+手册 | 真实业务版本走查 + 卡点修复 + 《主链路用户手册》 | 黑盒用户无指导跑通并放行 |
| B11(batch-221) 知识管线 | 版本沉淀 + **AI 任务探索新知识** 双输入；复用建议自动带出 | 第二版本建任务自动带出上版建议 |
| B12(batch-222) 智能回归+缺陷闭环 | 影响面默认接入；缺陷一键同步通知/缺陷库 | 建任务即给推荐回归集；业务缺陷一键转缺陷 |
| B13(batch-223) 对比+指标 | 跨版本对比页 + 运营指标看板（回归人天/提测→放行周期/漏测/周活跃） | 指标看板上线，owner 可人工记录 |
| B14(batch-224) D 级模型收敛 | TestPlan 数据归档、Dataset/Fixtures 合并、环境/报告/缺陷/任务入口收敛为单一事实源 | 双写清零；旧页面降级视图/历史 |
| B15(batch-225) 新业务接入 | 4 步接入向导 + 业务基线（试点 basketball-service/camel-mimo） | 30 分钟跑出业务基线 |

## 3. 里程碑 go/no-go

- M0 出口（B1–B5 合入）：登录第一眼即「我的待办」；C 级入口已下架；死代码已清；
- M1 出口（B6–B10）：黑盒用户无指导跑通一个真实版本验收闭环；
- M2 出口（B11–B13）：第二版本 AI 复用建议可用、回归量下降、指标看板在线；
- M3 出口（B14–B15）：双写清零；新业务 30 分钟出基线。

## 4. 最终验收（B15 合入后，另开新会话执行）

1. 审计 B1–B15 全部内容：逐条核对本路线图出口标准，登记遗漏/未完成事项；
2. 模拟黑盒用户，在浏览器上验收重构后测试平台全部功能是否符合预期（登录→我的待办→版本验收→执行→缺陷→放行→知识复用→资产库可达）；
3. 输出交付文档：
   - 交付文档 / 功能使用文档（面向黑盒测试工程师，业务语言）；
   - 代码实现文档（架构、主链路模型、菜单/权限、知识管线、清理记录）。

## 5. 交接区（每批结束更新）

| 批次 | 状态 | 完成摘要 | 未完成事项（移交下一批） |
|------|------|---------|--------------------------|
| B1(batch-211) | ✅ 已合入 main | 基线方案落盘（定位/ABCD 白名单/术语/傻瓜化规范/路线图，PR #391） | 无（文档批） |
| B2(batch-212) | ✅ 已合入 main | 入口收敛：tester 默认 5 一级入口（工作台/版本验收/结果与缺陷/知识中心/资产与更多，后者按 资产/更多/专家/系统 分桶）；C 级下架（用例服务 Playground Tab、知识中心专家 Tab 收维护权限、README special/perftest 宣称）；旧测试计划独立入口删除（menu:testplan 下架，/testplan、/testplan/:id 重定向 /testcase 不 404）；命令面板/访客目录/权限三处对账 | 移交：知识中心普通视图 3 Tab 命名与「版本记录/复用建议」Tab 随 B11 定稿；/testplan、playground 页面文件与 special/perftest 冻结代码随 batch-215 清理；TestPlan 数据只读归档随 batch-224；R211-3（B15 后终审+黑盒验收+交付文档）保持 Open |
| B3(batch-213) | ✅ 已合入 main (PR #393) | 首页我的待办：工作台改「我的待办」（待审/在跑/失败/待放行聚合）+ `/api/v1/dashboard/todo`；登录首页 `/` → `/workbench`；后端全量回归 2362 passed + 1 个非本批基线失败，前端 612 vitest | 移交：待放行完整验收状态机随 B9；VersionTask 统一事实源随 B6 |

| B4(batch-214) | 🟦 进行中 | 傻瓜化组件层：PageIntro/TermTip/EmptyStateGuide/StepWizard/AskAi MVP + 全局「问我」入口 + 我的待办页 Intro/TermTip/StepWizard 演示；前端 lint/typecheck/build/vitest 617 绿 | 移交：全站列表页空态教学分批补齐；AskAi 真 LLM 随 B11/DSH；StepWizard 完整数据流随 B6/B7 |
> 状态图例：🟦 进行中 / ✅ 已合入 main / ⏳ 未完成移交 / ❌ 阻塞