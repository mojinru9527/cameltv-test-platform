# Batch 218 — 版本任务执行与证据（B8）
> **Product (🟦)** | Date: 2026-09-05 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 路线图: `docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md` §2 B8(batch-218) 完整·前后端
- 主链路: `docs/platform-refactor/01-platform-positioning-and-mainline.md` §4「看执行」
- 前置: B6/B7 已有 VersionTask + 方案条目 + 状态机（C217-1：执行记录挂 version_task_execution 并回写 coverage）
- B8 出口标准: `一键跑完；失败四分类正确；证据可回放`

## 1. 问题陈述
方案已审（B7）但缺「执行」这一环：测试员不知道任务跑没跑、跑到哪、失败在哪、怎么回放。需要给 VersionTask 加「一键运行」入口，跑完后有进度/覆盖/证据/失败分类，并支持失败一键转缺陷草稿。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 一键运行 | 无 | POST /version-tasks/{id}/run | 本批 |
| 运行记录 + 进度 | 无 | version_task_run 表 + 进度/覆盖 | 本批 |
| 证据回放 | 无 | run.evidence 列表 | 本批 |
| 失败四分类（业务/脚本/数据/环境） | 无 | run.failures kind 正确 | 本批 |
| 失败→缺陷草稿 | 无 | POST .../defect/{idx} | 本批 |
| 前后端 gate | — | 全绿 + 后端无新增失败 | 本批 |

## 3. 非目标（本次不做）
- **不做放行页/证据包**（B9）、**知识沉淀**（B11）——后续批次。
- **不改执行引擎**：本批用可复现的合成运行（基于已采纳方案条目），真实 AITDE 场景执行随系列后续接入；但运行记录/覆盖/证据/分类接口即真实事实源。
- **不引入新依赖**。

## 4. 用户故事 + 验收标准
- As a 测试员, I want 点一下就把版本任务跑完并看到进度/覆盖, so that 不用手动逐条执行。
  - 验收：Given 任务有已采纳方案 / When POST run / Then 返回 run（progress=100，passed/failed/skipped/blocked 计数），任务状态→executed，coverage 回写。
- As a 测试员, I want 看失败分类并一键转缺陷草稿, so that 业务失败不用手工抄录。
  - 验收：Given run.failures 含 kind / When POST .../defect/{idx} / Then 生成 Defect(open) 并挂 version_task_defect。
- As a 测试员, I want 回放执行证据, so that 失败可复现。
  - 验收：Given run.evidence 非空 / When GET run / Then 返回证据列表。

## 5. 技术考量
- 后端：`version_task_run` 表 + `start_run/list_runs/get_run/create_defect_draft`；coverage 回写 task（C217-1）。
- 失败分类 kind：business / script / data / environment（FAILURE_KIND_LABEL）。
- 前端：`/version-tasks/:taskId` 详情页（运行按钮 + Progress + 覆盖 + 证据 + 失败转缺陷）。
- 语义 token：详情页不引入固定色板（batch54 守卫）。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台 | 前后端 gate 绿 + CI 全绿 |
| M1 里程碑 | 平台 | B6–B10 合入 → 黑盒跑通版本验收闭环 |

## 7. 技能使用
- `cameltv-agent-team` → 六部门工件
- `cameltv-ui-conventions` → Badge tone/variant 语义
- `cameltv-bug-guard` → 语义色板守卫、路由守卫
