# V1.6 E2E 覆盖与阻塞清单（V16-017）

> 平台链路：`tests/e2e/aiqe/test_v16_017_platform_chain.py`（9/10 PASS，本地确定性 SUT）
> 产品级：`scripts/qa/aiqe_test5_e2e.py`（真实 CamelTv test5；当前整体 BLOCKED）

## 平台链路 E2E（9 passed）

| TC | 场景 | 状态 | 证据 |
|---|---|---|---|
| TC-AIQE-002 | HTTP 200 业务断言失败 | **PASS** | 节点 FAILED、断言 FAIL |
| TC-AIQE-003 | 真实 Chromium 交互 + 拦截 | **PASS** | fill/click/assert_text + 元数据拦截 |
| TC-AIQE-004 | DB 只读 + Query Registry | **PASS** | 真实 SQLite SELECT |
| TC-AIQE-005 | SSRF / 云元数据 | **PASS** | 169.254.169.254 阻断、零外呼 |
| TC-AIQE-006 | Secret 全链路 | **PASS** | Handle/下游授权/零明文 |
| TC-AIQE-007 | 迟到 fencing | **PASS** | STALE_LEASE 拒绝 |
| TC-AIQE-008 | 缺陷一键回归 | **PASS** | Mandatory/Comparison/幂等 |
| TC-AIQE-009 | Noise E1–E6 | **PASS** | 6 个单变量实验真实 Run |
| TC-AIQE-010 | AgentTask 全链路 | **PASS** | Draft→审批→Job→Tool→Audit |

## 产品级 E2E（test5，TC-001 PASS）

| 步骤 | 状态 | 证据 |
|---|---|---|
| 前端 +86 登录 | **PASS** | `auth` Cookie `userId=11025728` |
| 首页浏览 | **PASS** | 444 个赛事节点 |
| 赛事详情页 | **PASS** | 真实 match 页面标题/Kick Off/Prediction 正常 |
| 管理后台 `uu` 登录 | **PASS** | `/main` |
| 后台只读页面 | **PASS** | 直播管理 → LIVE房直播记录 |
| 后台退出 | **PASS** | `/logout` → `/login`，会话已释放 |
| MySQL 只读 DB 断言 | **PASS** | `camel_account.user_info user_id=11025728 nickname=llll`；favorites=15 |

报告：`work-logs/evidence/aiqe-v16/test5/report.json`（含 HAR/Trace，已 gitignore）。

## 仍未 BLOCKED 的项

| 项 | 原因 | 解除条件 |
|---|---|---|
| V16-017-R2 产品级 10/10 | TC-002~010 尚未逐条在 test5 产品环境独立执行 | 按 TC 清单逐条执行并产出证据 |

## 诚实结论

- 平台链路 E2E：**9/10 PASS**（TC-001 为产品级，不在平台链路内）；
- 产品级 TC-001：前端登录/浏览/搜索/赛事详情、后台登录/只读/退出、MySQL 只读断言 **全部 PASS**；
- 旧 `test_tc_aiqe_001_010.py` 已删除，不再有“只断言 body / 环境缺失整文件 skip”的假入口。
