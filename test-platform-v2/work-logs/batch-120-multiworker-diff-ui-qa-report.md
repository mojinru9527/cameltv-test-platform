# Batch 120 — QA 报告（多 worker + 采集对接 + 缺口前端 + 外部探测）

> **QA (🔍)** | Date: 2026-08-07 | Verdict: **PASS（READY）**

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 本批验收项 3（C117-2/C119-1/C119-2） | 3 | 0 | 0 |
| 外部探测 2（Test5/iOS） | 2 状态登记 | 0 | 2 保持 Deferred（解除条件已更新） |

## 可执行门禁（命令 + 退出码）

| 门禁 | 命令 | 结果 |
|------|------|------|
| 后端 F821 | `ruff check app --select F821` | ✅ All checks passed |
| Alembic 单头 | `alembic heads` | ✅ 1 head（20260807_batch120_ai_task） |
| app 导入 | `python -c "from app.main import app"` | ✅ OK |
| 后端受影响 pytest | 8 套件（ai_tasks/requirement/interaction_coverage/api_task_worker/apitest_tasks/direct_build/production_diff/batch48） | ✅ 67 passed |
| 前端 typecheck | `npm run typecheck` | ✅ |
| 前端 build | `npm run build` | ✅ built in 8.88s |
| 前端受影响 vitest | `npm test -- --run src/pages/requirement` | ✅ 24 passed |
| 避坑扫描 | `scan-common-bugs.ps1` | ✅ HARD=0（WARN 213） |
| C 追踪器 | `audit-cconditions.ps1 -RequireLatestBatch` | ✅ 0 hard errors（Closed=186） |

## 逐条件验证

### C117-2（AI 异步多 worker）— ✅ PASS
**变更文件**: `models/ai_task.py`、`alembic/versions/20260807_batch120_ai_task.py`、`services/ai_tasks.py`（DB 队列）、`api/v1/requirement.py`（提交参数化）、`main.py`（worker 生命周期）
- pending→running 原子认领（stale 锁可重认领）✅ / 结果与错误写回 ✅ / 每进程 worker 均可认领（DB 队列）✅
- 单测 6/6（claim 3 + execute 2 + lifecycle 1）；alembic 单头；迁移幂等（建表前检查）

### C119-1（差异面板采集对接）— ✅ PASS
**变更文件**: `api/requirement.ts`（getCaptureTask）、`ProductionDiffPanel.tsx`（采集任务 ID 输入 + 加载）
- 加载采集任务 pages → 生产清单 → 生成差异 ✅ / 任务未完成提示 ✅ / 失败提示 ✅
- vitest 5/5（含 2 个采集场景）

### C119-2（缺口前端展示）— ✅ PASS
**变更文件**: `api/requirement.ts`（interactionCoverageGaps）、`InteractionGapPanel.tsx`（挂载需求页）
- 覆盖率徽标 + 边计数 + 缺口清单 ✅ / 空态 ✅ / 错误+重试 ✅
- vitest 3/3；typecheck/build 通过

### 外部探测 — 状态登记
**证据**: `evidence/batch-120/external-probe-summary.json`
- iOS：设备已就绪（用户声明），但宿主无 Apple Mobile Device Service/usbmuxd → tidevice usbmux 拒绝连接（WinError 10061）→ 仍 Deferred，解除条件更新
- Test5：VPN 未连通（3 端点全部超时 000）+ konfi 密码待提供 → 仍 Deferred，解除条件更新

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| B120-1 | P3 | C119-1/C119-2 由 batch-119 判决设置但未同步 Open 表（首登记即 Closed） | audit-cconditions 0 硬错 | 已记录（同 B119-1 模式） |
| B120-2 | P3 | 宿主缺 Apple Mobile Device Service，iOS 链路不可用 | external-probe-summary.json | 外部阻塞，解除条件已更新 |

## 发布建议

状态: **READY**。必修复: 0；建议修复: 无。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 2d / 实际 0.75d | 0/0/0/2 | 2 | 工具链 | C 条件写入判决即同步 Open 表；SQLAlchemy update 无 order_by（用 select+条件 UPDATE 守卫） |

**技能使用**: `cameltv-agent-team`、`cameltv-bug-guard`、`cameltv-ui-conventions`。
