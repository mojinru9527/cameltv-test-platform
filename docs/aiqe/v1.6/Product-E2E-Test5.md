# CamelTv test5 产品连通性证据（TC-002 支撑，不是 TC-001/003 PASS）

> 本文件只证明 test5 环境与关键链路可达；它**不能**替代 merged spec 的 TC-001（契约冻结/变更影响）
> 或 TC-003（503 首次失败+重试）。当前真实 TC 状态见 `E2E-Coverage-and-Blockers.md`。

## 1. 实测结果（2026-11-20）

| 步骤 | 状态 | 证据 |
|---|---|---|
| 前端 +86 登录 | **PASS** | `auth` Cookie `userId=11025728` |
| 首页浏览 | **PASS** | 448 个赛事节点 |
| 搜索 “Arsenal” | **PASS** | 搜索结果出现 Arsenal |
| 赛事详情页 | **PASS** | 真实 match 页面标题/Kick Off/Prediction 正常 |
| 后台 `uu` 登录 | **PASS** | `/main` |
| 后台只读页面 | **PASS** | 直播管理 → LIVE房直播记录 |
| 后台退出 | **PASS** | `/logout` → `/login`，uu 会话释放 |
| MySQL 只读断言 | **PASS** | `camel_account.user_info` user_id=11025728；`sports_favorite` 15 条 |

- 运行器：`scripts/qa/aiqe_test5_e2e.py`
- 报告：`work-logs/evidence/aiqe-v16/test5/report.json`
- 所有 DB 查询在 `START TRANSACTION READ ONLY` 后 `ROLLBACK`；未写业务数据。
- uu 已正常退出；ii/pp/ll 可能仍被锁（历史测试遗留）。

## 2. test5 两节点 API DAG（平台执行证据）

`scripts/qa/aiqe_test5_dag_e2e.py`：

- 目标：`general` → `getCountryCode`
- 2 节点 / 4 断言 / 4 Artifact，Run `f1b779e2` outcome=PASS
- 报告：`test-platform-v2/backend/work-logs/evidence/aiqe-v16/test5-dag/report.json`

## 3. 它为什么不是 TC-001/003

- TC-001 要求“收藏赛事 PRD 导入 + 契约冻结 + 需求变更影响”，本次未执行；
- TC-003 要求“API 首次 503 + 重试成功 + 不得掩盖失败”，本次未注入 503；
- TC-002 要求一个统一 Run 同时使用 API/Playwright/DB-RO Driver，本次是独立脚本步骤 + API-only DAG，未组成统一 Run。
- 因此 TC-002 记 **PARTIAL**；TC-001/TC-003 不能记 PASS。

## 4. 使用方式

```powershell
$env:AIQE_TEST5_FRONTEND_URL="https://camelive-g3-test5.elelive.cn/"
$env:AIQE_TEST5_ADMIN_URL="https://camel-admintest5.elelive.cn"
$env:AIQE_TEST5_PHONE="+8618476944071"
$env:AIQE_TEST5_PASSWORD="<从密钥系统注入>"
$env:AIQE_TEST5_ADMIN_USER="uu"
$env:AIQE_TEST5_ADMIN_SMS="1234"
$env:AIQE_TEST5_MYSQL_HOST="testdata5.elelive.cn"
$env:AIQE_TEST5_MYSQL_PORT="13356"
$env:AIQE_TEST5_MYSQL_USER="<readonly>"
$env:AIQE_TEST5_MYSQL_PASSWORD="<从密钥系统注入>"
$env:AIQE_TEST5_MYSQL_DATABASE="camel_account"
python scripts/qa/aiqe_test5_e2e.py --out work-logs/evidence/aiqe-v16/test5
```

退出码：`0=PASS`、`2=BLOCKED`、`1=FAIL`。HAR/Trace 已 gitignore。
