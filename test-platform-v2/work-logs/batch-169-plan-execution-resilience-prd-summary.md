# Batch 169 — PRD Summary
> **Product (🟦)** | Date: 2026-08-13 | Status: Approved

## 1. 问题陈述
C168-1 生产复测发现：计划同步 execute-all 含多条 UI 用例时超过 Railway 网关 300s，请求被切断且无执行记录（C168-2）；LLM 生成的 spec 使用 `waitForLoadState('networkidle')`，在真实直播/动态体育站点上 180s 超时；无登录态/稳定选择器使 UI 执行覆盖难以提升（C167-1/C168-1）。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 多用例 execute-all | 网关 300s 切断 | 接口立即返回、后台执行、前端轮询直至完成 |
| UI 单条执行 | 180s 超时 | 默认 90s 可配置；编译 spec 不用 networkidle |
| UI 失败信息 | exit_code+stdout | 保持可读，新增超时秒数可配置 |

## 3. 非目标
- 不伪造登录态：真实账号注入（storageState/Cookie）本批仅登记为 C167-1 后续，除非环境已提供。
- 不改执行结果判定口径。

## 4. 用户故事
- As 测试人员, I want 一键执行不卡网关, so that 多条 UI 用例也能完成并留痕。
- As 测试人员, I want 编译出的 UI 脚本在动态站点不挂死, so that 单条执行在合理时限内返回结果。

## 5. 技术考量
- `ExecuteAllBody.async_mode`（默认 false 保旧契约）；true 时 FastAPI BackgroundTasks 后台执行，前端轮询计划 stats.pending。
- `settings.ui_run_timeout_seconds`（env `UI_RUN_TIMEOUT_SECONDS`，默认 90）。
- SYSTEM_PROMPT 禁止 networkidle、默认导航 30s/DOM 15s、等待选择器带超时。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全队 | 后端 pytest 全量 + 前端 typecheck/lint/build/vitest |
| 生产复测 | 测试负责人 | 3 条 UI 用例 execute-all async_mode 返回 <5s 且后台完成留痕 |
