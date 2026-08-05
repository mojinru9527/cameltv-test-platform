# 响应式回归常驻 CI（Batch 93）

## 触发方式

- **每日定时**：01:30 UTC（09:30 北京时间）自动执行 `.github/workflows/responsive-e2e.yml`
- **手动**：仓库 Actions → 响应式回归 E2E → Run workflow

## 执行链路

```text
ubuntu runner
  → 后端（隔离 SQLite，种子固定 admin/tester 凭据）uvicorn:8000
  → 前端 vite dev:5173 + Playwright chromium
  → npx playwright test e2e/batch89-responsive.spec.ts（768×1024 / 390×844 × 8 页面）
  → 上传 evidence/batch-89/responsive/ + test-results/ 工件
```

## 失败处理

- 失败时查看 artifact（截图 + trace）定位溢出/不可点/console 报错
- 修复后提交；若为 spec 断言过严（如 ±1px 容差），调整 spec 并说明理由

## 扩展指引

- 新增页面/视口：编辑 `e2e/batch89-responsive.spec.ts` 的 `PAGES` / `VIEWPORTS` 数组
- 需要其他登录角色：在 workflow `env` 改 `E2E_USERNAME/E2E_PASSWORD` 并保证对应种子密码一致
- 若接入 PR 门禁（当前刻意不接，避免与 main-quality-gate 重复）：去掉 `on:` 的 schedule，加 `pull_request: paths: [test-platform-v2/frontend/**]`
