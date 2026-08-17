# Batch 191 — Leader 判决：/dsh-tasks 支持 AgentTeams 团队模式

> **Leader (🎯)** | Date: 2026-08-17 | Decision: **APPROVED（有条件）** — C191-1/C191-2 确认登记，R-1 冒烟运维跟进

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 高 | B1 方案落地完整：dsh_task mode/team_json 列、双运行时路由（node agent-team profile / python-sdk team.cordis.yml）、execute_task 团队分支 + 独立短 SessionLocal 轮询线程、前端模式选择 + 团队进度树；QA 复验 PASS |
| 风险 | 中 | R-1 真实冒烟 deferred（agent-team profile 未安装、平台 DSH 未启用）——非代码缺陷，登记 C191-1 运维跟进；C191-2 running 取消延后 |
| 覆盖 | 高 | 六部门全流程：PRD（7 用户故事/9 指标）→ PM（13 任务）→ Design（541 行规范含 2 处事实修正）→ Dev（6 提交）→ QA（NEEDS WORK → PASS 复验） |

## 关键决策（已批准）

1. **C191-1 确认登记**（python-sdk bundled runtime 加载 npm bundle 插件未实测）：node 先交付（`--profile agent-team`），python-sdk 团队模式 deferred；US-7 无静默 fallback 有代码+测试双证。解除条件=SDK 环境实测插件加载。
2. **C191-2 确认登记**（running 团队任务取消延后）：现状仅 pending 可取消，下批实现执行中终止。
3. **R-1 冒烟运维跟进**：真实 node 团队冒烟需安装 `$DSH_HOME/profiles/agent-team`（`dsh plugin --profile agent-team add @nanmicoder/dsh-agent-teams`）+ 平台 `DSH_ENABLED=true` + 凭据——部署决策，不阻塞本批代码合入。
4. **双运行时**：runner 团队分支按 `DSH_RUNTIME` 路由，node 优先实现，python-sdk 路径代码就绪待实测。

## 抽检通过（本批实测证据）

- ✅ 后端：专项 pytest 56 passed exit 0；全量 1606 passed/5 failed（5 失败=lanhu-mcp 子模块未初始化×2 + main 基线复现×3，**本批 0 新增失败**）；ruff F821 exit 0；Alembic 单头 + upgrade head exit 0
- ✅ 前端：dsh-tasks vitest 9/9（首轮 8 失败→0）；全量 488/488 exit 0；typecheck/build exit 0（QA 复验 V1-V4 实跑）
- ✅ QA 全流程：NEEDS WORK（3 必修复 + P3×2）→ dev 修复 02253b9 → QA 复验 PASS（5 项缺陷闭环，diff + 测试双证）
- ✅ 提交完整性：6 个开发提交（db13ee6/f190f14/89d1c09/242f31a/9946059/02253b9）+ 工件提交（8e2355e/34483e7/bf5cf92/b47bd4b/34420c7）；diff-classifier-baseline.json 基线漂移已 revert 无夹带；worktree 干净
- ✅ CI 分层：backend+frontend 代码 → 双端 required 全量（AGENTS.md §4.2）
- ✅ 文档：ADR-0018 团队模式补充、README/CLAUDE.md 同步、C-CONDITIONS 登记 C191-1/C191-2

## 判决

**APPROVED（有条件）**。QA PASS（必修复 0），六部门工件齐全。C191-1/C191-2 已登记 C-CONDITIONS.md。
合入指令：待用户一次总确认（推送 feature/batch-191-dsh-tasks-agent-teams + 创建 Draft PR + required checks 通过后合入 main）；合入前跑 `audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness` 基础审计，checks 全绿后 `-RequireSuccessfulChecks` 最终审计，squash 合入并清理 worktree。
运维跟进：部署环境按 C191-1 解除条件实测 python-sdk 团队模式；test 环境启用 DSH 后跑 R-1 真实冒烟。

## 下一批次 Leader 条件（如有）

- C191-1（Open）：python-sdk 团队模式实测（解除条件=SDK bundled runtime 可加载 npm bundle 插件并完成团队组合冒烟）
- C191-2（Open）：running 团队任务取消（解除条件=下批实现执行中终止）

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| 插件 team.json 语义：task.assignee=成员名、member.id=session id（非 id 匹配） | Dev 修复按 name 匹配 + 船长手册补充该语义说明 | 本批 team-progress.tsx（02253b9）+ docs/agent-team/dsh-agent-teams.md |
| `diff-classifier-baseline.json` 被测试运行漂移（非本批范围） | 两次 revert，QA 报告记录 | 本判决 + QA 报告 |
| agent-team profile 安装位=$DSH_HOME/profiles/（CLI bin.js 语义） | Design 开工核实修正 PM 假设 | 设计规范 §7 + team.cordis.yml 资产 |
| 成员完成工作但漏更新任务状态（t4/t5 各一次） | 船长以工件落盘为准代确认 | 本判决 + 船长手册常见坑 |
| `audit-ai-pr.ps1` 无 BOM + LF-only，PowerShell 引擎按 ANSI(GBK) 解码 UTF-8 → 解析失败（4 处） | 临时以 UTF-8 BOM 修复后审计通过（batch-190 审计时该文件可正常解析，损坏系历史批次引入并已随 main 传播）；需独立 fix 批次合入（仓库级阻塞，所有后续 PR 审计受影响） | 本判决 + 流程回写 |
| CI 前端 lint（`eslint --max-warnings=0`）首轮 FAIL：index.tsx:123 exhaustive-deps missing 'detail' | 本地自检只跑了 vitest/typecheck/build 漏 lint；已修复 12d5aa1（effect 外解构字段），自检清单补 `npm run lint` | 本判决 + 复盘卡 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 完整批次 1 轮 vs 实际 1 轮 + 1 修复轮 | 0/1/2/2（P1 assignee 语义、P2×2 mock/治理、P3×2）+ CI lint 1 条（exhaustive-deps，QA 漏跑 lint） | 2（QA 打回→修复→复验；CI lint 打回→修复） | 需求语义（插件数据模型未对齐）+ 测试基建 + 自检清单缺 lint | 实现前先读插件 snapshot.js 数据语义（assignee 存 name）；前端测试 mock 遵循仓库既有范式；本地自检必须含 `npm run lint` |

**技能使用**: cameltv-agent-team（DEPARTMENTS 模板/批次判定）；AgentTeams 插件（本批六部门流水线全流程实战，模式②首次完整批次自举）
