# Batch 163 — C162-1/2 修复 QA 报告

> **QA (🔍)** | Date: 2026-08-12 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 4（C162-1 后端 2 + C162-2 前端 + 门禁） | 4 | 0 | 0 |

## 可执行门禁
- ruff F821 ✅ | pytest 全量 **1389 passed / 0 failed / 3 skipped** ✅ | alembic 单头 ✅
- 前端 typecheck ✅ build ✅ vitest **460/460** ✅

## 逐条件
### C162-1 调度触发异步化
- `schedule_service.trigger_schedule`：先建 running run → 后台线程执行 `scheduler._execute_schedule(schedule_id, run_id)` → 立即返回 `{triggered, run_id, status:started}`。
- `scheduler._execute_schedule` 支持可选 run_id（APScheduler 定时路径兼容）。
- 重复触发保护：已有 running run → `already_running`。
- 测试：trigger <5s 返回 run_id + run 落库；重复触发 already_running ✅。

### C162-2 调度页环境名
- `useEffect(() => { loadEnvironments() }, [])` 挂载即加载 → 列表「执行环境」显示真实名称。
- 前端 460 测试全绿。

## 发布建议
状态: READY ✅（生产复验：触发 15.0.0 调度应 <2s 返回 run_id；页面环境名显示真实名称）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 0.5d vs 0.5d | 0/0/0/0 | 1（测试 import 修正） | 测试导入路径 | 新测试先确认 model 归属模块 |

## 生产复验（2026-08-12，合入+部署后）
- C162-1：15.0.0 调度触发 **476ms** 返回（此前 133s+502）；16.0.0 调度触发 **651ms** 返回 {triggered:true, run_id:10, status:started}，后台线程完成 405 skip ✅
- C162-2：调度页「执行环境」列显示 **体育平台-Test5**（此前「环境#3」回退）✅
- 新发现：15.0.0 run#9 自 14:46 起卡 running 超 1h（execute_all 长计划未在异常时更新 run）→ 登记 C163-1（stale run 回收/heartbeat）。
