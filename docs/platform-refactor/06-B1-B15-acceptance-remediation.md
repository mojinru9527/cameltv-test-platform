---
title: "B1–B15 黑盒验收：整改任务清单（PRD）"
owner: "qa-team"
last_reviewed: "2026-09-02"
status: "draft"
expires: "2027-03-02"
tags: ["platform-refactor", "b1-b15", "blackbox", "acceptance", "remediation"]
related:
  - "docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md"
  - "docs/platform-refactor/01-platform-positioning-and-mainline.md"
  - "docs/platform-refactor/02-function-abc-whitelist.md"
---

# B1–B15 黑盒验收：整改任务清单（PRD）

> **状态：** 本清单（F-01…F-09）已在 `feature/b15-acceptance-remediation` 一次修复（后端服务 + Alembic 迁移 + 前端导航/权限/知识 Tab），并于本地回归（ruff F821 + pytest + tsc + vite build）通过。

> 依据 `docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md` §4 最终验收要求，
> 以黑盒测试工程师（`tester` 角色）在最新 `origin/main`（`5d892947`，B15= batch-225）上实际走查。
> 本文档为**整改任务清单**，按优先级给出：问题 → 证据 → 建议方案 → 验收标准。

## 0. 验收方法

- 本地最新 main 实例：后端 `:8888`、前端 `:5555`；`tester` 账号 + 默认项目 `CamelTv 体育平台`。
- 走查链路：登录 → 我的待办 → 版本验收 → 执行 → 缺陷 → 放行 → 知识复用 → 资产库。
- 叠加代码审计（后端 service/api + 前端 page/nav-config）交叉印证。

## 1. 总体结论

| 维度 | 结论 |
|------|------|
| 结构/壳（B2/B3/B4 入口收敛、首页待办、傻瓜化组件、导航模型、版本任务 CRUD 页、指标页、接入向导） | ✅ 基本落地，符合预期 |
| 主链路「AI 价值」三步（AI 生成方案 / 一键执行 / 放行证据） | ❌ 硬编码 + 模拟 stub，未接真 AI、未真执行 |
| 主链路可达性 | ❌ `/version-tasks` 主页面被从导航孤立，首页「创建版本任务」只是演示弹窗 |
| 目标用户（tester）可用性 | ❌ 「生成方案」返回 403（`mission:generate` 未授予 tester） |

**一句话**：B1–B15 把「壳」做好了，但把「AI 生成 + 真实执行」做成了 stub/模拟；并在导航上把核心主链路藏了起来。这不满足路线图 M1「黑盒用户无指导跑通一个真实版本验收闭环」。

## 2. 整改任务清单（按优先级）

> 每条含：严重度 / 现状证据 / 建议方案 / 验收标准。建议作为独立轻量批次领办。

### F-01（P0）版本任务「AI 生成验收方案」为硬编码 stub

- **证据**：`frontend/src/pages/version-tasks/index.tsx:49-53`
  ```ts
  const generated = scopeModules.flatMap((m, i) => [
    { item_type:'functional', title:`${m} 主流程`, description:`验证 ${m} 正常链路`, confidence:80 - i*5 },
    { item_type:'api', title:`${m} 接口契约`, description:`校验 ${m} 相关接口返回`, confidence:70 - i*5 },
  ])
  ```
  页面文案「AI 会基于需求产出可审条目」，实现却本地写死 `80 - i*5` 置信度与 `${m} 主流程` 标题。未调用任何 LLM。
- **影响**：「审方案」环节没有真实、可执行的验收点，退化为模板占位。
- **建议**：新增后端 AI 方案生成接口（经 `ai_config_service.resolve(db, project_id)` 调 DeepSeek，提示词复用 AITDE `intelligence/prompts/scenario_design_v1.txt` 思路），产出含真实 `when`/断言 的可执行方案；前面板 `handleGeneratePlan` 改为调后端。
- **验收标准**：给定业务需求/变更模块，生成侧返回可执行的功能/接口/场景条目（真实断言），非固定模板；无 AI 配置时给出可读提示而非假条目。

### F-02（P0）版本任务「一键运行」产生模拟 PASS/FAIL

- **证据**：`backend/app/services/version_task_service.py:298-369`（含 `:324` 注释 `# 末条固定失败（保证失败分类可演示）`）
  - `is_fail = idx == last_idx or ((idx * 17 + item.id) % 20 == 3)` → 造通过/失败；
  - 证据 URL 为假 `/evidence/{run.id}/{item.id}`；
  - 失败信息为假 `"{item.title} 断言失败"`。
- **影响**：B9「放行结论」的通过率/风险**不对应任何真实执行**——即路线图 §1.5 明令禁止的「假成功」。
- **建议**：`start_run` 挂真实执行（API Runner / UI Runner / mission-scenario），回写真实步骤 + 真实请求/响应/截图证据；失败分类基于真实断言结果。
- **验收标准**：点「一键运行」后，PASS/FAIL 能溯源到真实证据（REQ/RESP/SCREENSHOT 物理可用）；无真实执行的条目标记为 `INCONCLUSIVE/ENV` 而非臆造 PASS/FAIL。

### F-03（P1）版本验收主链路 `/version-tasks` 从导航被孤立

- **证据**：
  - `backend/app/seed.py` `_MENUS` **无** `menu:versiontask`；
  - `frontend/src/layouts/nav-config.ts:27` 「版本验收」组仅 `['menu:missions','menu:versionmission']`；
  - 真实页面注册于 `frontend/src/router/index.tsx:271-272`（`/version-tasks`、`/version-tasks/:taskId`）；
  - `frontend/src/pages/workbench/index.tsx:140,172` 首页「创建版本任务」打开「新建版本任务（**演示**）」弹窗，未导航到真实页。
- **影响**：黑盒用户无法从侧边栏发现/进入版本验收主链路，只能输 URL `/version-tasks`。
- **建议**：新增 `menu:versiontask`（→ `/version-tasks`）并入「版本验收」组；首页「创建版本任务」改为 `navigate('/version-tasks')`。
- **验收标准**：`tester` 侧边栏「版本验收」组可点击进入 `/version-tasks`；首页按钮直达真实页。

### F-04（P1）tester 在「生成方案」步 403

- **证据**：`backend/app/api/v1/version_task.py:197` `require_permission("mission:generate")`；`backend/app/seed.py:215-216` `_TESTER_ACTIONS` 未含 `mission:generate`（注释「AI 生成留给管理员」）。
- **影响**：版本验收主链路对目标用户（黑盒测试员）在第 2 步即断。
- **建议**：把 `mission:generate` 授予 tester 角色；或重构为「方案生成」属主链路必要能力，无需管理员。
- **验收标准**：`tester` 建任务后可正常生成方案（不再 403）。

### F-05（P1）B13 指标页 / B15 接入页同样未被导航

- **证据**：`/metrics`、`/onboarding` 均在 `router/index.tsx:273-274` 注册，但无对应 `menu:*` 与 `nav-config.ts` 分桶。
- **影响**：同 F-03，需直连 URL。
- **建议**：纳入「版本验收」组或「资产与更多」分桶；随 F-03 一并处理。

### F-06（P2）B13 指标「回归人天」为硬编码 proxy

- **证据**：`backend/app/services/version_task_service.py:590` `regression_person_days = round(len(released) * 0.5, 1)`（注释「以任务数为 proxy」）。
- **影响**：运营指标「回归人天」非真实人天，不能用于度量。
- **建议**：接真实人天录入/工时来源；或明确标注为「近似值」并隐藏。
- **验收标准**：指标口径可解释、可溯源；或明确为 proxy 并在 UI 标注。

### F-07（P2）B13 跨版本对比依赖 B11 知识记录，当前 `exists=false`

- **证据**：`version_task_service.py:614-633` 读 `VersionKnowledgeRecord`；运行实测两版本均返回 `exists:false`。
- **影响**：B13 「跨版本对比」在知识记录未沉淀前不可用。
- **建议**：与 B11 知识管线联动；对比也可回退到 VersionTask coverage 中真实数据。
- **验收标准**：放行后二版可对比（有真实覆盖/缺陷/结论）。

### F-08（P2）B15 接入「接基线/生成方案/跑基线」为 stub

- **证据**：`backend/app/services/onboarding_service.py`
  - 第 2 步 `complete_step` 仅 `ob.step = step`（无真实基线导入）；
  - 第 3 步 `generate_plan` 写死 `[{f"{ob.name}-核心流程", confidence:75}, ...]`；
  - 第 4 步 `start_run`（即 F-02 的 mock）。
- **影响**：「30 分钟跑出业务基线」不成立——没有真实契约快照/基线。
- **建议**：第 2 步真正接入 `api_spec_url` 导入 OAS 资产；第 3 步走 F-01 的 AI 方案；第 4 步走 F-02 真实执行。
- **验收标准**：接入向导跑完后产生可复核的业务基线（契约快照 + 真实 P0 冒烟结果）。

### F-09（P2）B11 知识中心未按定稿落地「版本记录/复用建议」

- **证据**：知识中心普通视图仅「项目知识 / 平台研发 / 检索」；未见 B11 定稿的「版本记录 / 复用建议」Tab（B2 交接区也标注「随 B11 定稿」）。
- **影响**：知识闭环「下版复用建议自动带出」未在 UI 体现。
- **建议**：补「版本记录 / 复用建议」Tab，接入 `VersionKnowledgeRecord` + 复用建议带出。
- **验收标准**：第二版建任务时自动带出上版建议。

## 3. 建议执行顺序

1. F-01 + F-02（把「AI 生成」与「执行」从 stub 换成真实现）—— 决定主链路是否可信；
2. F-03 + F-04（让黑盒用户能发现并用起来）—— 决定主链路是否可达；
3. F-05/06/07/08（指标、对比、接入、知识补齐）—— 决定 M2/M3 扩展能力；
4. F-09（知识闭环 UI 补齐）。

## 4. 备注

- 涉及「AI 生成」「真实执行」的任务建议优先对齐现有 `ai_config_service`（项目级 DeepSeek 提供方）与 AITDE Runner / oracle_engine，避免再造一套骨架。
- 本清单基于黑盒 + 代码双重印证；如需可回滚验证，请以 `docs/` 单测与真实业务 mock 数据为主，防止「假成功」复现。
