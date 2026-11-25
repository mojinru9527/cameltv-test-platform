# AIQE 本地隔离 Test 环境（rehearsal）

> **边界先说清楚**：这是**平台自测演练环境**，不是产品验收环境。
> 它能验证“启动 → 登录 → API → Workflow → Run → Worker → Assertion → 证据”链路，
> 但没有 CamelTv 业务 API/后台 UI/前台 UI/MySQL/真机/Benchmark 数据集。
> 产品级 TC-AIQE-001..010 的正式验收仍必须在隔离 Test 业务环境执行，
> 结果写入 `docs/aiqe/v1.6/e2e/product-results.json`；本地演练结果只进
> `work-logs/evidence/aiqe-v16/local-test/product-results-local.json`。

## 1. 启动 / 停止 / 状态

```powershell
# 启动（默认 8101，独立 SQLite + 独立 SECRET_KEY + 自动生成管理员密码）
python scripts/aiqe/local_test_env.py start

# 查看生成的环境变量文件
python scripts/aiqe/local_test_env.py env

# 健康检查
python scripts/aiqe/local_test_env.py status

# 停止
python scripts/aiqe/local_test_env.py stop
```

启动脚本会完成：

1. 创建 `work-logs/evidence/aiqe-v16/local-test/platform.db`（独立 SQLite）；
2. 以 `ENVIRONMENT=development` + 独立 `SECRET_KEY` 启动 `uvicorn`（detached，日志
   `backend.log`）；
3. 开启进程内 Worker（`AIQE_INPROCESS_EXECUTOR_ENABLED=true`）；
4. 注册 HTTP/DB 能力 manifest（`local-http` / `local-db`）；
5. 创建项目 `AIQE-LOCAL`、环境 `local-isolated`、target policy（仅允许 127.0.0.1）；
6. 写入环境文件：

```
AIQE_TEST_BASE_URL=http://127.0.0.1:8101
AIQE_TEST_ADMIN_URL=http://127.0.0.1:8101      # 后端 API；后台 UI 需另行起前端 dev server
AIQE_TEST_DB_READONLY_DSN=sqlite:///...platform.db?mode=ro&uri=true
AIQE_TEST_ADMIN_USER=admin
AIQE_TEST_ADMIN_PASSWORD=<random, 存在 work-logs/evidence/.../local-test-env.env>
AIQE_TEST_PROJECT_ID=2
AIQE_TEST_ENVIRONMENT_ID=1
```

> `AIQE_TEST_DB_READONLY_DSN` 在本环境是 **SQLite 只读 URI**，只用于演练；
> 生产/Test 必须是 PostgreSQL 只读 role（见 `scripts/aiqe/check_pg_readonly_role.py`）。

## 2. per-TC runner 路径

本地 rehearsal 统一 runner：

```
scripts/aiqe/per_tc/product_tc_local_runner.py --tc <TC-AIQE-00X>
```

它实现：

- **TC-001**：Contract API 全流程（draft → approve AC → REVIEW_REQUIRED → APPROVED →
  FROZEN → V2 draft），校验 V1 checksum 不变、V2 checksum 不同；
- **TC-002**：Workflow（HTTP 节点 → 本地 `/health`）→ 审批 → Run → Worker →
  Assertion；返回真实 Run/NodeRun/Artifact ID；
- **其余 TC**：探测本地环境可达后输出 BLOCKED，并写明缺失的业务前置
  （业务 API/UI/MySQL/真机/数据集）。

**所有 TC 在本地环境一律输出 BLOCKED**（附真实探测结果），不会把平台演练冒充产品验收。

## 3. 运行本地 rehearsal

```powershell
# 载入本环境变量（PowerShell）
Get-Content work-logs/evidence/aiqe-v16/local-test/local-test-env.env |
  ForEach-Object { if ($_ -match '^(AIQE_TEST_[^=]+)=(.*)$') { Set-Item "env:$($matches[1])" $matches[2] } }

# 校验本地配置结构
python scripts/aiqe/run_product_tc.py --check-config `
  --config docs/aiqe/v1.6/e2e/product-tc-config.local.yaml

# 执行 10 个 TC（本地结果写到 work-logs，不进官方 product-results.json）
python scripts/aiqe/run_product_tc.py --run `
  --config docs/aiqe/v1.6/e2e/product-tc-config.local.yaml `
  --output work-logs/evidence/aiqe-v16/local-test/product-results-local.json `
  --allow-blocked
```

预期输出：`{"PASS": 0, "FAIL": 0, "BLOCKED": 10, "NOT_RUN": 0, "total": 10}`。
其中 TC-002 会带有真实的 Run ID / NodeRun ID / Artifact ID。

## 4. 与正式产品验收的差异

| 项 | 本地 rehearsal | 正式产品验收（required） |
|---|---|---|
| 业务 API | 无（只有平台自身 /health） | CamelTv 业务 API + Admin/Public UI |
| 数据库 | SQLite 文件 | MySQL/PostgreSQL 只读账号 |
| 前端 | 未启动（可选起 dev server） | 后台 + 前台真实页面 |
| 设备 | 无 | Android 模拟器/真机（TC-009） |
| Benchmark | 无数据集 | 已关闭缺陷标注集 + Gate + 人工批准 |
| 产物位置 | `work-logs/evidence/.../local-test/` | `docs/aiqe/v1.6/e2e/product-results.json` |

## 5. 安全与清洁

- `local-test/` 目录包含生成的 admin 密码与 SQLite 文件，已加入 `.gitignore`，**不会提交**；
- 服务只监听 `127.0.0.1`，target policy 只允许 127.0.0.1；
- 演练结束请执行 `python scripts/aiqe/local_test_env.py stop`。
