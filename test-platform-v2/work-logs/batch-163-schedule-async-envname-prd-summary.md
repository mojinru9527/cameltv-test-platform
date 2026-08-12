# Batch 163 — C162-1/2 修复（PRD-lite）

> **Product (🟦)** | Date: 2026-08-12 | Status: Draft | Mode: light

mode: light
豁免理由: 纯修复（无新接口/无 Schema/无新配置）：调度触发异步化 + 前端环境名挂载加载。
非目标: 不改调度执行引擎语义；不做部署 CI 改造。

## 1. 问题陈述
- C162-1（P2）：`POST /schedules/{id}/trigger` 同步执行 `_execute_schedule`，长计划（如 15.0.0 含 16 条 API 用例）触发时 HTTP 超网关返回 502（服务端继续执行 run#9）；应后台执行并立即返回 run_id。
- C162-2（P3）：调度列表「执行环境」名称仅在打开表单时加载 environments，页面挂载时列表显示「环境#N」回退。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 调度触发响应 | 长计划 502 | 立即返回 {run_id, status:started}（<2s） |
| 调度页执行环境列 | 显示「环境#N」 | 显示环境名（如 体育平台-Test5） |

## 3. 非目标
- 不改变 APScheduler 定时触发路径（保持同步后台执行）。
- 不做执行取消/重跑（沿用现有 run 记录）。

## 4. 用户故事 + 验收
- As 测试人员, I want 手动触发调度立即返回, so that 不因长计划卡住页面。验收：触发 15.0.0 调度 <2s 返回 run_id；run 记录执行中。
- As 测试人员, I want 调度列表显示环境名, so that 一眼可见绑定关系。验收：页面挂载后「执行环境」列显示真实环境名。

## 5. 技术考量
- 后端：schedule_service.trigger_schedule 改为先建 running run → 后台线程执行 `scheduler._execute_schedule(schedule_id, run_id)` → 立即返回；`_execute_schedule` 支持可选 run_id（APScheduler 路径兼容）。
- 前端：SchedulePage 挂载时 `loadEnvironments()`。
- 测试：trigger 立即返回 started + run_id；重复触发 already_running；调度列表环境名（前端挂载）。

## 6. 上线计划
合入 + 部署 → 生产复验：触发 15.0.0 调度 <2s 返回；页面环境名列正常。

## 7. 技能使用
cameltv-bug-guard（线程/事务）、cameltv-ui-conventions
