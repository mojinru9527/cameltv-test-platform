# Batch 120 — Leader Verdict（多 worker + 采集对接 + 缺口前端 + 外部探测）

> **Leader (🎯)** | Date: 2026-08-07 | Decision: **APPROVED（待用户一次总确认）**

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | C117-2/C119-1/C119-2 全部落地；外部项按实际探测登记（C106-2 按用户指令跳过） |
| 实现质量 | PASS | 后端 67 pytest 全绿（含迁移单头）；前端 typecheck/build + 24 vitest；scan HARD=0；audit-cconditions 0 硬错 |
| 证据 | PASS | 外部探测证据 JSON + 追踪器解除条件更新（iOS usbmux 拒绝连接、Test5 VPN 未连通） |

## 关键决策（已批准）

1. **C117-2 用 DB 队列而非外部队列**：新增 `ai_task` 表 + 原子认领（select 最早 pending + status 条件 UPDATE 守卫），每进程 worker 均可认领，避免引入 Redis 等外部依赖；`submit_ai_task` 参数化（document_id + task_type），跨 worker 由 worker 从 DB 重建作业。
2. **C119-1 直接消费采集任务 pages**：面板加载 `/ui-tests/capture/{id}` 的 pages → 生产清单，替代手动粘贴。
3. **C119-2 前端代表边**：内置 8 条模块级代表边（取自 batch-113 证据），后端加载平台交互用例计算缺口；完整 3172 边入库转下批。
4. **外部项如实登记**：iOS 设备虽就绪，宿主缺 Apple Mobile Device Service（usbmux 拒绝连接）；Test5 VPN 未连通 + konfi 密码待提供——保持 Deferred 并更新解除条件，不虚报解锁。

## 抽检通过

- ✅ `backend/app/services/ai_tasks.py` — 认领守卫/写回/生命周期
- ✅ `backend/alembic/versions/20260807_batch120_ai_task.py` — 幂等建表 + 单头
- ✅ `frontend/src/pages/requirement/components/InteractionGapPanel.tsx` — 四态 + 中文
- ✅ `C-CONDITIONS.md` Batch 120 关闭表 + 外部项解除条件
- ✅ CI 分层：backend + frontend + docs → PR 双端全量回归

## 判决

**APPROVED**：QA 硬门禁全绿。待用户一次总确认（推送 + Draft PR + required checks 通过后合入 main）。

## 下一批次 Leader 条件

- **外部项（保持 Deferred）**：iOS（CP-C2/C84-1/C95-2）——宿主装 Apple Mobile Device Service/usbmuxd 后重试；Test5（C74-2/C95-1/C111-4）——VPN 连通 + konfi 密码落位后执行。
- C106-2（P2）：邀请链接观察（用户已跳过，保持 Open）。
- C120-1（P3）：3172 边完整拓扑入库，缺口面板全量计算（当前 8 条代表边）。
- C120-2（P3）：多 worker 部署后验证（Railway 多副本时任务可跨实例认领）。
- C99-1、C96-1：大项 Epic 保持 Open。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| C 条件写入判决未同步 Open 表（复发） | QA 记录 B120-1；本批 Closed 表补录 | C-CONDITIONS.md |
| SQLAlchemy update 无 order_by | 改用 select + status 条件 UPDATE 守卫 | ai_tasks.py claim_next_task |
| iOS 设备就绪但宿主无 usbmux 服务 | 探测证据 + 解除条件更新 | external-probe-summary.json |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 2d / 实际 0.75d | 0/0/0/2 | 2 | 工具链 | 新 C 条件写入判决即同步 Open 表；外部项以实测登记不臆断 |

**技能使用**: `cameltv-agent-team`、`cameltv-bug-guard`、`cameltv-ui-conventions`。
