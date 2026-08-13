# Batch 170 — PRD Summary
> **Product (🟦)** | Date: 2026-08-13 | Status: Approved

## 1. 问题陈述
生产体育站点账号已可登录（POST /account-service/ee/client/demo/login 返回 userId/userSig/token，无短信验证码），但平台 UI 自动化每次以全新无登录态上下文执行，登录后模块全部「执行未覆盖」（C167-1/C168-1 未关闭）。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| UI 执行登录态注入 | 无 | UI 环境变量 UI_STORAGE_STATE_JSON 自动注入 Playwright storageState |
| 登录态刷新 | 手工 Cookie | scripts/sports 一键生成 storageState（凭据走环境变量，不入库） |
| 执行覆盖 | 1 模块 5.6% | 登录后 P0/P1 UI 用例真实执行并回写执行覆盖 |

## 3. 非目标
- 不做 UI 自愈选择器对象库（后续批次）。
- 不改 demo/login 接口；凭据不写入仓库/工件。

## 4. 用户故事
- As 测试人员, I want UI 执行自动带登录态, so that 登录后模块也能真实执行。
- As 运维, I want 一键刷新 storageState, so that 登录态过期后可自助更新。

## 5. 技术考量
- `_execute_ui_case_sync` 读取 UI 环境加密变量 `UI_STORAGE_STATE_JSON`，写临时 storageState 文件，`PLAYWRIGHT_STORAGE_STATE` env 传给 npx；playwright.config.ts `use.storageState` 读 env。
- 执行结果透出 `storage_state: true/false`。
- `scripts/sports/refresh-sports-prod-storage-state.py` 用 `SPORTS_PROD_MOBILE/SPORTS_PROD_PASSWORD` 调 demo/login 并生成 storageState。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全队 | pytest/typecheck/lint/build/vitest 全绿 |
| 生产复测 | 测试负责人 | 登录态 UI 用例真实执行 + 截图 + C167-1/C168-1 关闭 |
