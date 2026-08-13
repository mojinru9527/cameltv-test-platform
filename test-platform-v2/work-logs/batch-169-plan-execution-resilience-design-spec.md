# Batch 169 — Design Spec
> **Design (🎨)** | Date: 2026-08-13 | Status: 就绪

## 后端行为
| 项 | 规范 |
|----|------|
| ExecuteAllBody | environment_id / auto_ui / ui_environment_id / async_mode(bool=false) |
| async_mode=true | 路由返回 `{"async": true, "message": "..."}`；BackgroundTasks 在新 Session 执行 execute_all_cases |
| UI 超时 | settings.ui_run_timeout_seconds（默认 90，可 env 覆盖）；TimeoutExpired 文案含秒数 |
| 编译提示词 | 禁 networkidle；`page.setDefaultNavigationTimeout(30000)`、`page.setDefaultTimeout(15000)`；等待用 waitForSelector/getByText 带 timeout |

## 前端
| 组件 | 规范 |
|------|------|
| PlanDetail 执行弹窗 | 确认执行后 toast「已在后台执行，完成后自动刷新」；4s 轮询 stats.pending，归零后 loadExecutions |
| 锚点 | PlanDetail.tsx doExecuteAll / execScopeOpen 弹窗 |

## 状态设计
| 场景 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 后台执行 | 「执行中...」+ 轮询 | 无 | 失败 toast | async_mode=false 时同步 |
