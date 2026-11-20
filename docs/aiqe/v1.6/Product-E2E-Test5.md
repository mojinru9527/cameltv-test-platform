# V16-017 产品级 E2E：CamelTv test5 环境

> 运行器：`scripts/qa/aiqe_test5_e2e.py`（真实 Playwright，不做 fixture 替身）
> 证据目录：`work-logs/evidence/aiqe-v16/test5/`（**含 HAR/Trace，禁止提交**）

## 1. 当前实测结果（2026-11-20）

| 步骤 | 状态 | 证据 |
|---|---|---|
| 前端手机号登录（+86 18476944071） | **PASS** | `auth` Cookie 含 `userId=11025728`；`front_login.png` |
| 首页赛事浏览 | **PASS** | 444 个赛事节点；`front_browse.png` |
| 搜索 “Arsenal” | **PASS** | 搜索结果页出现 Arsenal；报告 `front_search` |
| 赛事详情页 | **PASS** | 真实导航到 `/football/match-east-bengal-fc-vs-sc-delhi/...`，标题/Kick Off/Prediction 正常；`front_match_detail.png` |
| 搜索 “Arsenal”（最近一次） | **BLOCKED** | 搜索框不可见；早先运行曾 PASS |
| 管理后台登录（uu） | **PASS** | `/main` |
| 后台只读页面 | **PASS** | 直播管理 → LIVE房直播记录 |
| 后台退出 | **PASS** | `/logout` → `/login`，会话释放 |
| MySQL 只读 DB 断言 | **PASS** | `camel_account.user_info user_id=11025728 nickname=llll`；`camel_studio.sports_favorite` 15 条（READ ONLY 事务） |

整体：**PASS（exit 0）**；后台 uu 已登录、只读访问并退出，未遗留会话。

## 2. 使用方式

```powershell
$env:AIQE_TEST5_FRONTEND_URL="https://camelive-g3-test5.elelive.cn/"
$env:AIQE_TEST5_ADMIN_URL="https://camel-admintest5.elelive.cn"
$env:AIQE_TEST5_PHONE="+8618476944071"
$env:AIQE_TEST5_PASSWORD="<从密钥系统注入，不提交>"
$env:AIQE_TEST5_ADMIN_USER="uu"
$env:AIQE_TEST5_ADMIN_SMS="1234"
$env:AIQE_TEST5_MYSQL_HOST="testdata5.elelive.cn"
$env:AIQE_TEST5_MYSQL_PORT="13356"
$env:AIQE_TEST5_MYSQL_USER="<readonly>"
$env:AIQE_TEST5_MYSQL_PASSWORD="<从密钥系统注入>"
$env:AIQE_TEST5_MYSQL_DATABASE="camel_account"
python scripts/qa/aiqe_test5_e2e.py --out work-logs/evidence/aiqe-v16/test5
```

退出码：`0=PASS`、`2=BLOCKED`、`1=FAIL`。凭据只从环境变量读取；报告只记录脱敏手机号。

## 3. 证据与安全

- `report.json`：步骤状态/原因/时间/脱敏信息；
- `front_login.png`、`front_browse.png`、`admin_login_blocked.png`；
- `network.har`、`trace.zip`：含真实请求头/Token，**只保留本地或受控制品库，禁止进 git**；
- `.gitignore` 已忽略 `work-logs/evidence/aiqe-v16/test5/`。

## 4. 解除阻塞条件

1. 如需复跑，使用未锁定的 admin 账号并在结束后 `/logout`；
2. 确认允许的测试写操作（收藏/取消收藏）及清理方式。

MySQL 只读连接已验证；MongoDB 未用于本阶段断言。

解除后运行器将补齐：管理后台只读页面、DB 状态断言、收藏/取消收藏业务闭环，并输出最终 PASS 报告。


## 5. TC-003 产品级 DAG（真实 test5）

运行器：`scripts/qa/aiqe_test5_dag_e2e.py`；报告：`work-logs/evidence/aiqe-v16/test5-dag/report.json`

| 项 | 值 |
|---|---|
| 目标 | `https://camel-test5.elelive.cn/account-service/ee/client/general` → `/getCountryCode` |
| DAG | 2 节点（general → country_code），4 条断言 |
| Run | `f1b779e2-414c-4dcf-a821-ba6e72d089f6`，outcome=PASS |
| Node | 2 个均 PASSED |
| Assertion | 4 条 PASS |
| Artifact | 4 个 |
| 执行路径 | 本地 AIQE launch → Worker → HTTP Driver → Assertion → Artifact |

报告为机器可读 JSON；HAR/Trace 未生成本阶段（API 节点）。
