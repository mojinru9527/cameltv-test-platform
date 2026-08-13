# Batch 170 — PM Plan
> **PM (🟨)** | Date: 2026-08-13

## 开发任务
### [ ] Task 1: UI storageState 注入
**验收**: UI 环境变量 UI_STORAGE_STATE_JSON 存在时执行结果 `storage_state=true` 且 Playwright 使用该状态；不存在时 false 不报错。
**文件**: backend/app/services/test_plan_service.py、backend/tests/playwright/playwright.config.ts

### [ ] Task 2: 登录态刷新脚本
**验收**: `SPORTS_PROD_MOBILE/SPORTS_PROD_PASSWORD` 注入后脚本输出 storageState JSON；缺凭据报错 fail closed。
**文件**: scripts/sports/refresh-sports-prod-storage-state.py

## 质量要求
- [x] 后端 pytest 全量 + ruff F821  - [x] 前端 typecheck/lint/build/vitest
- [x] 凭据不入库  - [x] 无 console 报错
