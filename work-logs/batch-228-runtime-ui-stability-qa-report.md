# Batch 228 — QA 报告

> QA | Date: 2026-09-04 | Verdict: PASS（代码与本地链路）

## 测试总览

| 条件数 | 通过 | 失败 | 外部阻塞 |
|--------|------|------|----------|
| 13 | 13 | 0 | 3 |

外部阻塞不影响本批代码验收，但生产 Durable Runtime 仍需要真实 Temporal、Worker 进程、Control Plane 网络与注册 Token。当前页面和 Runbook 没有提供注册 Token 的可发现获取路径，真实 Worker 按文档启动会因缺少 Token 得到 401；该 P1 已登记为下一批必须修复的问题。当前没有执行生产部署，不能把本地 PASS 表述为生产已恢复。

## 可执行门禁

| 检查 | 退出码/结果 |
|------|-------------|
| 前端依赖 | `npm ci` → 0 |
| 前端定向 | 5 files / 10 tests passed |
| 前端全量 | 137 files / 622 tests passed |
| 前端类型、lint、构建 | 全部 0；构建 3666 modules transformed |
| Worker heartbeat + registry | 23 tests passed |
| 后端全量 | 0；2421 passed / 49 skipped / 1 xfailed / 0 failed |
| 后端静态 | app import、Ruff F821 均为 0 |
| Alembic | 单一 head；revision/single-head 8 tests passed |
| G0-G2 | exit 1；`PASS_WITH_WARN`，0 HARD / 330 全仓 WARN，4 route guards passed |
| C 条件审计 | exit 0；0 hard / 0 warning |
| 浏览器 | 12 张三视口截图；0 console error；Scope/Scenario 各 1 次 GET；Runtime 每轮 5 个 GET 各 1 次 |

完整命令摘要与异常复核见 `work-logs/evidence/batch-228-runtime-ui-stability/regression/test-results.md`。

## 逐条件验证

| 条件 | 结果 | 证据 |
|------|------|------|
| 范围页首次加载只请求一次 | PASS | `scope.tsx:48-62`；E228-03/E228-05 |
| 场景页首次加载只请求一次 | PASS | `scenarios.tsx:54-65`；E228-04/E228-05 |
| 两页 GET 使用 AbortSignal | PASS | `api/scope.ts:45-49`、`api/scenarios.ts:56-58`；定向 Vitest |
| 成功分析/评审后仅单次刷新 | PASS | 独立 `reloadVersion` + 10 项前端定向测试 |
| Worker 列表返回真实能力且无 N+1 | PASS | `repository.py:70-85`、`service.py:71-90`；registry 查询数断言 |
| Worker 默认持续心跳且失败重试 | PASS | `worker_heartbeat.py:112-145`；heartbeat tests |
| Worker 与 gateway 同生命周期清理 | PASS | `start-worker.sh:31-67`；启动脚本契约测试 |
| Runtime 离线态可诊断、可重新检查 | PASS | `WorkerHealthTable.tsx:43-67/90-103`；E228-02/E228-05 |
| 可选耐久未就绪不再误导接入失败 | PASS | `onboarding/index.tsx:300-315`；E228-01 |
| 列表和路由在使用前淘汰过期 Worker | PASS | `service.py`、`router.py`；stale worker 回归与真实浏览器离线态 |
| 心跳不覆盖排空/禁用，离线可恢复在线 | PASS | `repository.py`；管理员状态与恢复回归 |
| 路由批量读取能力，无 Worker N+1 | PASS | `router.py`；SQL 查询数断言 |
| 心跳响应携带 UTC 时区，浏览器显示本地时间 | PASS | `service.py:109-125`；UTC 响应契约与浏览器 20:13 显示 |

## 代码实现逻辑审计与防假成功

- Worker 能力来自 `worker_capabilities` 一次批量 SQL，并由两个 Worker 的真实 SQLite 数据与查询计数断言验证，不是前端 mock 拼接。
- 心跳测试使用真实异步循环和 `httpx.MockTransport` 验证 HTTP 请求、失败重试与停止事件；启动脚本不再用一次性 `curl` 冒充常驻心跳。
- 浏览器走查使用本地 FastAPI + SQLite，Runtime 离线记录、Mission 和接口响应都由真实后端提供；只对本地 AITDE 功能开关做进程级临时启用。
- Scope/Scenario 请求次数由后端访问日志计数，页面稳定后没有额外 GET，未用静态代码目测代替执行。
- Runtime 增量复验先通过页面禁用在线 Worker，再验证刷新后保持“已禁用”；随后只把临时测试记录的心跳回拨 10 分钟，页面真实 GET 自动淘汰并显示“离线”。
- 后端内部使用 SQLite 兼容的 naive UTC，API 响应边界补为 timezone-aware UTC；浏览器由错误的 12:14 修正为本地 20:14。

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|--------|------|------|
| B228-P1-01 | P1 | `loading` 同时参与 effect 依赖和被 effect 写入，范围/场景持续请求并闪烁 | 已修复并补 10 项前端定向回归 |
| B228-P1-02 | P1 | Worker 启动仅发送一次心跳，超过 180 秒必然离线 | 已修复为默认 60 秒持续心跳 |
| B228-P1-03 | P1 | Worker 列表漏返回 capability，页面错误显示“无” | 已修复为单次批量查询 |
| B228-P1-04 | P1 | 启动脚本切到仓库根目录，按 Runbook 执行时 Python 找不到后端 `app` 包 | 已改为切到 `test-platform-v2/backend`，并加入启动器路径契约测试 |
| B228-P1-05 | P1 | 列表和任务路由使用前不淘汰过期 Worker，可能显示假在线或把任务路由给失联节点 | 已修复并补列表/路由回归 |
| B228-P1-06 | P1 | 后续心跳会覆盖管理员设置的 DRAINING/DISABLED 状态 | 已修复；仅 OFFLINE 在心跳后恢复 ONLINE |
| B228-P1-07 | P1 | 心跳写本地时间而离线判断使用 UTC，非 UTC 主机可能长时间显示假在线 | 已统一为 naive UTC 存储与比较 |
| B228-P2-01 | P2 | 离线 Worker 操作列为空，缺少恢复说明和检查入口 | 已修复并完成三视口走查 |
| B228-P2-02 | P2 | 接入页把可选耐久能力误解为整体接入阻断 | 已修正文案与状态层级 |
| B228-P2-03 | P2 | TaskQueue 路由逐 Worker 查询能力，形成 N+1 | 已改为一次批量查询并固定 SQL 次数 |
| B228-P2-04 | P2 | naive UTC 响应缺少时区标记，浏览器把心跳时间少显示 8 小时 | 已在响应边界补 UTC 标记并完成浏览器复验 |
| B228-P3-01 | P3 | Batch 148 网络失败用例依赖本机网络策略，结果不稳定 | 已改为确定性 ConnectError 注入 |
| NEXT-P1-01 | P1 | 黑盒管理员无法从页面或 Runbook 获得 Worker 注册 Token，真实 Worker 启动返回 401 | 未关闭；按批次生命周期在本批合入后从最新 main 开下一批修复 |

## 发布建议

状态：READY FOR DRAFT PR。代码可进入 required checks；生产恢复必须在发布火车部署后，连续观察真实 Worker 心跳超过 180 秒，并复验生产 Network 与 Runtime 页面。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4.5h / 实际约 2.0h | 0/7/4/1 | 4 | 技术债 + 生命周期/时间契约缺口 | Worker 上线验收必须从 Runbook 入口启动，并覆盖鉴权获取、模块导入、持续心跳、状态机、UTC 响应和查询数 |

**技能使用**：cameltv-agent-team、cameltv-bug-guard、cameltv-ui-conventions、Playwright CLI；结论均以命令、请求日志和截图为准。
