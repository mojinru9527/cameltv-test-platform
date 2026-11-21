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


## 6. TC-003 产品级重试与失败证据

运行器：`scripts/qa/aiqe_test5_retry_e2e.py`；报告：`test-platform-v2/backend/work-logs/evidence/aiqe-v16/test5-retry/report.json`

- test-side fault proxy：第 1 次返回 503，第 2 次转发真实 test5 `general` API；
- DAG `retry.max_attempts=2`；
- Run `ef8c0d14`，outcome=PASS；
- **attempt 1 = FAILED（STATUS_MISMATCH，503）**；**attempt 2 = PASSED（200）**；
- `proxy_hits=2`，两条 attempt ID 均在证据中；
- 结论：**TC-003 VERIFIED**，首次失败未被最终 PASS 掩盖。


## 7. TC-006 上游第三方 504

运行器：`scripts/qa/aiqe_test5_upstream_e2e.py`；报告：`test-platform-v2/backend/work-logs/evidence/aiqe-v16/test5-upstream/report.json`

- test-side 504 stub（模拟赛程第三方依赖故障）；
- 节点输入 `upstream_dependency: true`；
- Run `fb913d5c`，outcome=INCOMPLETE；
- Node **BLOCKED / UPSTREAM_5XX**；
- 业务 Assertion **BLOCKED**（未执行）、**未创建 Bug**；
- 结论：**TC-006 VERIFIED**。


## 8. TC-004 浮层交叉干扰（PARTIAL）

运行器：`scripts/qa/aiqe_test5_overlay_e2e.py`

- Core：关闭 test5 原有引导层 → 点击直播页 Login CTA → 登录弹层出现（2 个输入）**PASS**；
- Integration：注入全屏 `aiqe-cross-feature-overlay` → 同一 CTA 点击被拦截 **FAIL（预期）**；
- `elementFromPoint` 命中 overlay；分类 **CROSS_FEATURE_DEFECT**；
- 未接入 AIQE Core/Integration 两个正式 Run，未创建 Defect Draft → **TC-004 PARTIAL**。


## 9. TC-005 并发串行（test5 赛事 resource key）

运行器：`scripts/qa/aiqe_test5_concurrency_e2e.py`

- 真实 test5 API 经 1.5s 延迟代理，确保锁被持有；
- 两个 Run 使用同一 `resource_keys=["match:l7oqdehg7gkgr51"]`；
- Run A `d1984e6f`：09:23:50 start → 09:23:53 finish；
- Run B `1572eb74`：09:23:53 start → 09:23:56 finish；
- **B start >= A finish**，无重叠，`serialized=true`，两 Run 均 PASS；
- 同时修复 `resource_lock.release` 后 owner 为空仍阻塞的缺陷，并加回归测试；
- 结论：**TC-005 VERIFIED**。


## 10. TC-002 统一 Run（PARTIAL）

本地 AIQE API + 本地 Playwright Runner + in-process HTTP/DB worker：

- Run `19525865-fbc0-4710-a425-a9880a59c289`，outcome=PASS；
- Node `api_general`（HTTP）PASSED；
- Node `browser_live`（Playwright，test5 直播页）PASSED，标题已采集；
- Node `db_user`（DB-RO，SQLite fixture）PASSED；
- 同时修复外部 Runner 上报顺序缺陷：先 fenced 收口，再落 Job 终态；否则 Node 永久 READY；
- **仍为 PARTIAL**：没有 API 创建 match_id、后台配置直播源/发布、Public API 状态查询、Cleanup；DB 是 fixture 而非 test5 DB-RO。


## 11. TC-007 UI Runner 强杀（VERIFIED）

- 本地 AIQE API + Playwright Runner 执行 test5 直播页；
- 测试侧 kill `chrome-headless-shell` 主进程；
- Runner 捕获 `TargetClosedError`，上报 `AUTOMATION/WORKER_FAILURE`；
- Run `82036730`：outcome=FAIL，Node=ERROR/AUTOMATION/WORKER_FAILURE，attempts=1，**未无限 RUNNING**；
- 断言 `page_has_camel` = **NOT_EVALUATED**（业务断言未执行）；结论：**TC-007 VERIFIED**。


## 12. TC-009 多端 AC 对照（VERIFIED，Quark 替代）

- PC：Playwright Chromium 打开 test5 直播赛事页，标题 PASS；
- Android：OnePlus6T / Android 11，OpenVPN 已连接，Quark 打开同一 URL，标题 PASS；
- 报告：`work-logs/evidence/aiqe-v16/test5-multidevice/report.json`；
- **deviation**：设备无 Android Chrome，经用户批准以 Quark 替代；不声称 Android Chrome 已验证。


## 13. TC-001 契约冻结与变更影响（VERIFIED）

- A1 LLM 真实调用：V1 提取 4 条 AC，V2 提取 6 条 AC；
- 用户人工确认“实时同步”SLA = **≤5 秒**；
- Contract V1 冻结，checksum `sha256:...`；V2 创建后 V1 checksum **不变**，V2 checksum 不同；
- 关联用例 `CASE-FAV-001` 置 `DRAFT`（需复审）；
- 报告：`work-logs/evidence/aiqe-v16/test5-contract/report.json`。


## 14. TC-004 补充：REGISTER/Login 登录方式区分（PARTIAL）

运行器：`scripts/qa/aiqe_test5_register_login_e2e.py`

- 点击 `REGISTER` 打开 Register 弹窗；
- EMAIL 模式输入：`email / password / smsVerifyCode`；
- PHONE NUMBER 模式输入：`mobile / password / smsVerifyCode`；
- 点击 `Log in` 进入 Login 弹窗；
- Login EMAIL：`email / password`；Login PHONE：`mobile / password`；
- 8 项互斥检查全部 PASS；
- **仍为 PARTIAL**：原始“广告/其他功能浮层交叉干扰 + Defect Draft”未执行，本次只验证登录方式区分。


## 15. TC-002 运营后台资讯发布 → 前端查看（VERIFIED，用户批准简化口径）

- 运营后台 `内容管理 → 资讯列表 → 新增`；
- 文章 ID：`aiqe-news-1795265608`；groupId：`1781182573699923987`；
- 封面、球类、分类、标题、关键词、描述、正文均写入；
- 审核通过，是否上线=是；
- 前端列表出现标题；详情页：
  `https://camelive-g3-test5.elelive.cn/news/detail/aiqe-news-1795265608?entry_way=news`
- 详情页标题/正文可见，无 “Something went wrong”；
- 运行器：`scripts/qa/aiqe_test5_news_front.py`，4/4 checks PASS；
- 边界：这是用户批准的“资讯发布→前端查看”简化口径，不是原始 match_id/直播源/DB-RO 统一 Run。
