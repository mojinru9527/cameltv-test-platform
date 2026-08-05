# Batch 98 — Design Spec（CI 迁移 + V1 工具删除）

> **Design (🎨)** | Date: 2026-08-05 | Status: 就绪

## 1. CI 迁移设计

### 1.1 新脚本 `scripts/ci/api-regression.ps1`（stdlib PowerShell）

| 子命令 | 参数 | 行为 |
|--------|------|------|
| `health` | `-BaseUrls "u1,u2"` | 逐个 `Invoke-WebRequest`，任一失败 exit 1（替代 `tp envcheck`） |
| `run` | `-BaseUrl -AuthToken [-Grep] [-Proxy] [-ReportDir]` | 在 `test-platform/tests/api-testing/generated` 执行 `npx playwright test`，注入 `CAMELTV_BASE_URL/AUTH_TOKEN/HTTP_PROXY/JUNIT_OUTPUT/JSON_OUTPUT`；Playwright 失败即非 0（替代 `tp api run`） |
| `collect-elk` | `-JunitPath -ElasticUrl [-KibanaUrl]` | 解析 JUnit 失败用例 → 正则提取 `traceId`（`traceId[:=]\s*[\w-]{8,}`）→ 输出 ELK/Kibana 查询链接（替代 `tp logagg batch`） |

约束：只使用 PowerShell 内建 cmdlet 与正则；不引入 Python 依赖；`run` 前自动 `npm ci`（幂等）。

### 1.2 `api-regression.yml`（目标环境 test/prod）

checkout → setup-node → `npm ci`（generated 目录）→ token 刷新（保留 `fetch-auth-token.cjs`）→
`health`（test: `camelive-g3-test5.elelive.cn` 等；prod: `www.camel1.tv` + `api.cameltv.live`）→
`run`（JUnit → `$GITHUB_WORKSPACE/artifacts/`）→ `upload-artifact`（替代 `tp report ingest`）→
失败时 `collect-elk`（`ELASTIC_API_KEY` 注入）。

### 1.3 `prod-smoke-test.yml`（prod，VPN）

checkout → VPN 探测（`VPN_TUN_ADDR` + base URL 200 检查，替代 `tp config show`）→ setup-node →
`npm ci` → prod token 刷新 → `run`（**移除 `--grep smoke` 空跑**，执行 6 个只读 spec）→ JUnit artifact →
失败时 `collect-elk`。生产只读约束：全部为 GET；不引入写请求。

## 2. V1 清理设计

| 项 | 处理 |
|----|------|
| `test-platform/tools/{api_tester,api_diff,av_checker,data_factory,env_check,load_tester,log_aggregator,mock_server,project_init,report_dashboard,traffic_monitor}` | `git rm -r` |
| `test-platform/cli/tp.py` | 保留 `config show/sites`（仅依赖 `core.config_loader`）；移除 capture/apidiff/mock/envcheck/datafactory/logagg/report/api/init-project 命令注册 |
| `test-platform/server/main.py` | 移除 `include_router(envcheck/api_test/datafactory)` |
| `test-platform/server/routes/{envcheck,api_test,datafactory}.py` | 删除 |
| `repo-boundaries.json` `deprecated-v1.rules` | 更新：11 工具已移除；web-ui/server 仍待覆盖矩阵（Batch 99） |

## 3. 文档与条件更新

- `C-CONDITIONS.md`：C64-3 关闭（prod 无法提供，以 test 为准）；C96-1 拆分（V1 删除 ✅ / C27 四项 Open）。
- `docs/production-delivery/生产环境交付清单.md`：D1/C64-3 行更新为「prod 无法提供，验收以 test 为准」。
- `docs/生产级验收现状与体育平台承接规划.md`：§6.1 标记 CI 迁移 + 工具删除完成；§8 决策 2 更新。

## 4. 设计签核

结论：**通过**。风险控制：先迁移后删除；生产只读边界由工作流显式约束（仅 GET）；`rg` 0 引用为删除出口标准。
