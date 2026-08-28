# C-内网执行器 — 纯内网 API 的执行方案

> Batch 206 / C-内网执行器。解决「测试平台（公网部署）无法直达纯内网 API」的通用问题。

## 1. 问题

平台服务器（如 swiftbugs.cn，公网部署）**不可直达纯内网 API**（如 `camel-api-gateway05.svc.elelive.cn`，解析到 `192.168.50.170`，仅 VPN 可达）。此时在平台「调试模式/用例执行」会**静默 30s 超时**（平台服务器到内网无路由）。

## 2. 方案：internal 环境 → runner 执行

平台不再直连内网，改为**创建执行任务派发给「内网执行器（runner）」**，runner 跑在能连内网的机器（VPN 机上），实际执行 + 回传结果。

```
平台(公网) --派发--> 内网Runner(VPN机) --HTTP--> 内网API
                        └──────── 回传结果 ────────┘
```

## 3. 改动

- **环境表** 新增 3 字段（`20060828_b206` 迁移）：
  - `access_type`：`public`（平台可直达）/ `internal`（纯内网，需 runner）
  - `execution_mode`：`on_platform`（平台直连）/ `runner`（派发内网执行器）
  - `runner_key`：负责该环境的执行器标识（空=任意 runner 可认领）
- **执行引擎** `_do_execute`：`internal` + `execution_mode=runner` 时**不发起网络请求**，返回明确 `error_type=NEEDS_RUNNER`（引导配置 runner），替代静默超时。
- **执行任务表** `runner_execution_task` + 服务 + API：
  - `POST /api/v1/apitest/runner/tasks` 平台创建派发任务
  - `POST /api/v1/apitest/runner/claim` runner 认领（`FOR UPDATE SKIP LOCKED` 原子）
  - `POST /api/v1/apitest/runner/report` runner 回传结果
- **内网执行器脚本** `backend/scripts/executor/api_runner.py`（在 VPN 机运行）。

## 4. 使用

**4.1 策略**：internal + runner 环境 → 平台返回 `NEEDS_RUNNER`，不超时。

示例（debug 模式选 internal+runner 环境）返回：
```json
{"status":"error","error_type":"NEEDS_RUNNER",
 "error":"内网接口需执行器（runner）执行：环境 #7「...」为 internal，execution_mode=runner..."}
```

**4.2 跑内网执行器**（在能连内网的机器上）：
```bash
export PLATFORM_URL=https://swiftbugs.cn
export API_USERNAME=sportsadmin
export API_PASSWORD=xxx
export RUNNER_KEY=test5-internal-01
export PROJECT_ID=1
export RUNNER_BASE_URL=http://camel-api-gateway05.svc.elelive.cn   # 该内网网关
python backend/scripts/executor/api_runner.py        # 循环认领执行
python backend/scripts/executor/api_runner.py --once # 认领一条后退出
```

**4.3 平台侧**：把 `Test5-接口` 环境设为 `access_type=internal, execution_mode=runner, runner_key=test5-internal-01`，即可由 runner 执行其用例；不再由平台直连。

## 5. 通用性

任何项目只要是「纯内网 API」，只需：① 该环境的 runner 跑在能连其内网的机器；② 环境标 `internal + execution_mode=runner + runner_key`。平台主链路无需改动。

## 6. 待做（前端）

环境表单可暴露 `access_type / execution_mode / runner_key` 三个字段（当前后端 schema/服务已支持，前端表单补输入控件即可）。
