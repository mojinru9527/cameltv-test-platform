# Batch 228 浏览器请求与交互证据

> Browser: Chromium via Playwright CLI | Date: 2026-09-04

## Runtime

- 本地离线 Worker 显示 `BROWSER`、`HTTP` 两项真实能力、最后心跳、恢复原因与“重新检查”。
- 操作列显示“等待恢复心跳”，没有误导性的远程启动按钮。
- 在线 Worker 通过页面点击“禁用”后，状态显示“已禁用”并在自动刷新后保持；过期测试记录在下一次真实 GET 时自动显示“离线”。
- naive UTC 响应补时区前页面显示 `12:14`，修复后同一心跳在 Asia/Shanghai 浏览器正确显示 `20:14`。
- 点击“重新检查”后，每个 Runtime GET 各出现 1 次：
  - `/api/v2/workers`
  - `/api/v2/workflows?page=1&page_size=50`
  - `/api/v2/approvals`
  - `/api/v2/secret-refs`
  - `/api/v2/policy-profiles`

## 范围与场景

- 打开 `/missions/1/scope`：后端日志仅出现 1 次 `GET /api/v2/missions/1/scope`，HTTP 200。
- 打开 `/missions/1/scenarios`：后端日志仅出现 1 次 `GET /api/v2/missions/1/scenarios`，HTTP 200。
- 两页在 Network idle 后保持稳定空态，没有再次进入 Skeleton 或重复 GET。

## 接入状态与控制台

- onboarding 同时显示“业务接入基线尚未就绪”和“可选耐久执行尚未就绪”；下方明确写明耐久能力不影响当前业务接入和同步基线。
- 所有关键页面最终浏览器检查均为 `0 console errors / 0 warnings`。
- 浏览器首次与后端全量回归并行加载时出现一次本机 `ERR_INSUFFICIENT_RESOURCES`；全量回归结束后刷新即恢复，后续全部页面和截图无控制台错误，不属于产品请求失败。
- 按 Runbook 启动真实 Worker 时，未配置注册 Token 的心跳得到 401；页面和 Runbook 均未说明黑盒管理员如何取得该 Token。此项作为 `NEXT-P1-01` 保留，未用直接数据库夹具冒充真实 Worker 已上线。
