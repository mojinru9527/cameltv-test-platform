# Batch 228 — QA 报告

> QA | Date: 2026-09-03 | Verdict: PASS（代码与本地链路）

## 测试总览

| 条件数 | 通过 | 失败 | 外部阻塞 |
|--------|------|------|----------|
| 9 | 9 | 0 | 3 |

外部阻塞不影响本批代码验收，但生产 Durable Runtime 仍需要真实 Temporal、Worker 进程、Control Plane 网络与注册 Token。当前没有执行生产部署，不能把本地 PASS 表述为生产已恢复。

## 可执行门禁

| 检查 | 退出码/结果 |
|------|-------------|
| 前端依赖 | `npm ci` → 0 |
| 前端定向 | 5 files / 10 tests passed |
| 前端全量 | 137 files / 622 tests passed |
| 前端类型、lint、构建 | 全部 0；构建 3666 modules transformed |
| Worker heartbeat + registry | 16 tests passed |
| 后端全量 | 0；2414 passed / 49 skipped / 1 xfailed / 0 failed |
| 后端静态 | app import、Ruff F821 均为 0 |
| Alembic | 单一 head；revision/single-head 8 tests passed |
| G0-G2 | exit 2；`PASS_WITH_WARN`，0 HARD / 330 全仓 WARN，4 route guards passed |
| C 条件审计 | exit 0；0 hard / 0 warning |
| 浏览器 | 12 张三视口截图；0 console error；Scope/Scenario 各 1 次 GET |

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

## 代码实现逻辑审计与防假成功

- Worker 能力来自 `worker_capabilities` 一次批量 SQL，并由两个 Worker 的真实 SQLite 数据与查询计数断言验证，不是前端 mock 拼接。
- 心跳测试使用真实异步循环和 `httpx.MockTransport` 验证 HTTP 请求、失败重试与停止事件；启动脚本不再用一次性 `curl` 冒充常驻心跳。
- 浏览器走查使用本地 FastAPI + SQLite，Runtime 离线记录、Mission 和接口响应都由真实后端提供；只对本地 AITDE 功能开关做进程级临时启用。
- Scope/Scenario 请求次数由后端访问日志计数，页面稳定后没有额外 GET，未用静态代码目测代替执行。

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|--------|------|------|
| B228-P1-01 | P1 | `loading` 同时参与 effect 依赖和被 effect 写入，范围/场景持续请求并闪烁 | 已修复并补 10 项前端定向回归 |
| B228-P1-02 | P1 | Worker 启动仅发送一次心跳，超过 180 秒必然离线 | 已修复为默认 60 秒持续心跳 |
| B228-P1-03 | P1 | Worker 列表漏返回 capability，页面错误显示“无” | 已修复为单次批量查询 |
| B228-P1-04 | P1 | 启动脚本切到仓库根目录，按 Runbook 执行时 Python 找不到后端 `app` 包 | 已改为切到 `test-platform-v2/backend`，并加入启动器路径契约测试 |
| B228-P2-01 | P2 | 离线 Worker 操作列为空，缺少恢复说明和检查入口 | 已修复并完成三视口走查 |
| B228-P2-02 | P2 | 接入页把可选耐久能力误解为整体接入阻断 | 已修正文案与状态层级 |

## 发布建议

状态：READY FOR DRAFT PR。代码可进入 required checks；生产恢复必须在发布火车部署后，连续观察真实 Worker 心跳超过 180 秒，并复验生产 Network 与 Runtime 页面。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4.5h / 实际约 1.2h | 0/4/2/0 | 2 | 技术债 + 生命周期契约缺口 | Worker 上线验收必须从 Runbook 入口启动，并覆盖模块导入、持续心跳时间窗与列表能力查询数 |

**技能使用**：cameltv-agent-team、cameltv-bug-guard、cameltv-ui-conventions、Playwright CLI；结论均以命令、请求日志和截图为准。
