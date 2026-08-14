# Batch 181 — 架构专项：TaskQueue 六队列统一 / 软删三套语义统一 / 路由大文件拆分

> **mode: full**（重构/架构类完整批次，按 pipeline-modes.md 判定：引入新的核心组件 `TaskQueue` 基类与 Schema 变更，须六部门工件）
> **来源**：FIX-173-P2-06 / P2-08 / P2-10（`docs/batch-173-issue-landing.md`），用户确认按此前评估以**独立专项批次**承接
> **执行**：DeepSeek Harness（workflow=direct，executor=DeepSeek_Harness）
> **日期**：2026-08-16

---

## 1. 问题陈述

Batch 173 四视角深度对抗审查确认三类架构债（`_review_tools/b173/report-arch-backend.md`），Batch 174–179 已消化 P0 执行引擎、统计口径、请求层、P2 体验与部分架构收敛（权限码 CI、重复端点、PG 超时、UI 执行入口、死代码）。**以下三项属「大工程量架构改造」，此前评估为独立专项批次承接，本次交付**：

1. **P2-06 TaskQueue 六队列统一**：API 批量任务 / AI 任务 / DSH 任务 / 蓝湖证据包 / Agent 队列 / UI run 六套认领式队列各自为政——认领方式 3 种（skip_locked、UPDATE-rowcount、**非原子 SELECT→改→commit**）、锁字段 3 套（locked_by/locked_at、locked_at、started_at 兼作锁）、失联回收仅 2 套具备（API/证据包），Agent 队列无任何回收，UI run 无 stale 回收。`agent_queue._process_queue_once`（:227-231）为**跨进程 TOCTOU**：SELECT pending → 内存改 status → commit，多副本部署下两个进程可同时认领同一队列项。
2. **P2-08 软删三套语义并存**：`is_deleted`（用例/域/模块）vs `status=deprecated`（knowledge_source/knowledge_chunk，含保鲜衰减自动废弃 source_service.py:186-228）vs 硬删（需求/缺陷/计划等）。知识域查询层对「删除」的过滤散落 `status.notin_(("deprecated","superseded"))` / `status == "active"` / 计数统计 3+ 种写法；用例侧 `is_deleted == False` 风格 15 处与 `.is_(False)` 混用。
3. **P2-10 路由大文件拆分 + 路由层禁 ORM**：9 个路由文件 >20KB（knowledge 66.8KB/1668 行最大），knowledge.py 路由内直连 ORM（`select(KnowledgeEntity)` 等 ~25 处）；`report-arch-backend.md §5.2` 明确「按域拆分 + 路由层禁 ORM」并点名 knowledge.py:675-693 为反例。

## 2. 成功指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 认领实现样式 | 3 种并存 + 1 处非原子 | 全部走统一 `TaskQueue` 基类原子认领（UPDATE 条件 + rowcount 校验，SQLite/PG 均安全） |
| 锁字段 | 3 套（locked_by/locked_at、locked_at、started_at） | 六表统一 `locked_by` + `locked_at`（证据包保留 heartbeat_at 作活性信号） |
| 失联回收 | 2/6 队列具备 | 6/6 队列具备（AI/DSH/Agent/UI 补齐） |
| 软删机制 | 2 套（is_deleted / status=deprecated） | 知识域并入 `is_deleted`；`is_deleted == False` 写法清零 |
| >20KB 路由文件 | 9 个 | 0 个 |
| 路由层直连 ORM（knowledge 域） | ~25 处 | 0 处（模型 import 清零） |
| 全量 pytest / OpenAPI 路径集 | 基线 | 无新增失败；路由路径与请求方法零变化 |

## 3. 用户故事与验收标准

### US-1（P2-06）统一认领与失联回收
> 作为运维/执行工程师，我希望六类后台任务使用同一套「原子认领 + 失联回收」机制，这样任何 worker 崩溃或网络抖动都不会让任务永久卡 running。

- **Given** 六张队列表（api_execution_task / ai_task / dsh_task / lanhu_evidence_job / agent_queue_item / ui_test_run）各有一条 pending 任务，且系统存在两个 worker 进程
- **When** 两个 worker 同时认领
- **Then** 同一条任务只被一个 worker 认领（rowcount 校验），执行者持有 locked_by/locked_at 锁
- **And** 模拟执行器失联（锁超时）后，下一次认领或周期回收将该任务置 failed 并释放锁，可被重新提交
- **And** 六队列的 claim/execute/finish 路径均经由 `app/core/task_queue.py` 的统一原语实现

### US-2（P2-08）删除语义唯一化
> 作为知识中心用户，我希望「删除/废弃」只有一种语义，这样任何列表、统计与检索对已删知识源的行为一致。

- **Given** 知识源 A 被废弃（含保鲜衰减自动废弃、用户手动废弃、级联清理三入口）
- **When** 查询知识源列表 / 概览统计 / 变更检测 / 快照对比 / 用例入图
- **Then** 均通过统一的 `is_deleted` 判定，行为与现状完全一致（默认隐藏、管理视图可查、检索口径不变）
- **And** 存量 deprecated/superseded 数据经迁移回填为 `is_deleted=True`，迁移幂等、Alembic 单头

### US-3（P2-10）路由按域拆分且不直连 ORM
> 作为后端开发者，我希望大路由文件按域拆分、路由层不出现 ORM 查询，这样定位端点与维护成本更低、分层边界可被静态校验。

- **Given** 9 个 >20KB 路由文件
- **When** 按域拆分为多个 `APIRouter` 文件并在 `router.py` 聚合
- **Then** 全部路径与 HTTP 方法不变（OpenAPI 路径集合零变化），`/api/v1` 前缀语义不变
- **And** knowledge 域路由文件不再 import 任何模型、不出现 `select(`/`db.query(`（ORM 查询收敛到 services）
- **And** 新增路由文件遵循「路由层禁 ORM」约定（pytest 静态守卫）

## 4. 非目标（明确不做）

| 项 | 说明 | 承接 |
|----|------|------|
| P3-03 追溯轴标签中英混排 | 前端打磨，随迭代自然消化（用户已确认） | 后续迭代 |
| P3-04 域命名体系不统一 | 前端+数据回填，随迭代自然消化 | 后续迭代 |
| P3-09 >800 行页面拆分（AiResultModal 1424 行等 5 个前端页面） | 前端重构，随迭代自然消化 | 后续迭代 |
| P1-06 执行状态机 4 套取值统一（pass/passed/done/completed） | 属执行事实源收敛工程，与本批队列机制解耦；TaskQueue 基类不强制统一各表状态词表 | 后续专项 |
| 硬删表（需求/缺陷/计划/UI 任务等）转软删 | 行为变更需产品决策（恢复能力/审计口径），本批仅固化约定：软删统一 `is_deleted`，硬删为显式审计删除 | 后续决策 |
| wiki_raw_source/wiki_page/ui_test_script 的 status 词表（superseded/deprecated 等生命周期值） | 属实体生命周期状态而非删除语义，不在本批迁移 | — |
| DSH 沙箱加固（C172-1/C172-2） | 安全专项，与本批队列机制无关 | C172 追踪 |
| 蓝湖证据包 job_runner 心跳机制本体 | 已具备并生产验证，仅认领原语统一，心跳线程保留 | — |

## 5. C 条件承接核对（C-CONDITIONS.md）

- **C75-1 批次模式**：本批为重构+Schema → **mode: full** ✅（本文件头部已记录）
- **C75-3 audit-cconditions**：合入前运行 `audit-cconditions.ps1 -RequireLatestBatch` ✅（QA/合入门禁）
- **C76-2 scan-common-bugs**：提交前运行，HARD>0 处理或注明豁免 ✅（Dev 门禁）
- **C78-1 模块 pytest**：受影响模块（队列/知识/路由/计划/用例）执行并记录退出码 ✅（QA 门禁）
- **C86-1 双 404 约定**：新增测试断言遵循 assert_guard_404 / HTTP 200+code 404 ✅
- **C104-5 worktree 写入核验**：本批全部写入位于 `F:\CamelTv-worktrees\DeepSeek_Harness-batch-181-taskqueue-route-softdelete`（git status 已核对）✅
- **C63-3 引用 C63 条件**：C63 外部阻塞项（C63-2 等）与本批无关，不新增豁免；本批不触碰外部依赖
- **C172-1/2（DSH 沙箱）**：豁免——与本批队列机制正交；dsh_task_service 仅认领原语调整，不改变执行沙箱
- **C122-2/C123-*/C124-3/C134-1 等**：外部/其他域条件，与本批无交集，保持原状态

## 6. 风险与缓解

| 风险 | 等级 | 缓解 |
|------|:----:|------|
| 队列机制改动影响生产执行链（API/AI/UI 在产线使用中） | 高 | 认领/回收语义与现状逐项对齐（原 API 行为为基准）；新增单测覆盖原子性与回收；全量 pytest 回归 |
| Alembic 迁移在生产 PG 上执行 | 高 | 单头迁移 + 幂等回填（UPDATE 条件 where 限定存量值）；`alembic upgrade head` 本地+空库双验证 |
| 路由拆分引发 import 环或路径冲突 | 中 | 保持各子文件独立 APIRouter + 相同 prefix；router.py 显式 include；OpenAPI 路径集基线测试比对；逐文件拆分即跑相关测试 |
| ORM 收敛到 services 引入事务语义漂移 | 中 | 仅移动查询不改变 commit 归属（沿用调用方 get_db 会话）；services 函数签名显式收 db 参数 |
| 软删语义转换后检索口径漂移 | 中 | 逐调用点 before/after 对照（附录 A 表），行为保持原则：原过滤=新过滤，原不过滤=新不过滤 |

## 7. 交付物

- 代码：`app/core/task_queue.py`、六队列模块改造、5 张表锁字段迁移、知识域软删迁移、9 个路由文件拆分、路由层 ORM 收敛（knowledge 域）、静态守卫测试、OpenAPI 路径集基线测试
- 工件：PRD / PM / Design / 看板 / QA 报告 / Leader 判决（本批次六件）
- 文档：backend/CLAUDE.md 增补「删除语义约定」与「路由层禁 ORM 约定」
