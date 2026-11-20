# V1.6 E2E 覆盖与阻塞清单（V16-017）

> **重要纠正**：此前把 test5 登录/浏览/详情误标为 TC-001、把两节点 DAG 误标为 TC-003。
> 按 merged spec 的真实 TC 定义，二者仅是 **TC-002 的支撑证据**，不能计为 TC-001/TC-003 PASS。
> 当前 **3/10 TC 完全 VERIFIED（TC-003/TC-005/TC-006）**；TC-001/002/004/007 PARTIAL，其余 BLOCKED。

## 真实 TC 状态（merged spec §TC-AIQE）

| TC | 规格标题 | 当前状态 | 证据 / 缺口 |
|---|---|---|---|
| TC-001 | 需求契约冻结 + 需求变更影响 | **PARTIAL** | 只有 test5 连通性；未导入收藏 PRD、未做契约冻结/变更影响 |
| TC-002 | API → Admin UI → Public API → DB 的统一 Run | **PARTIAL** | test5 前端 4 步 + 后台 uu 登录/只读/退出 + MySQL 断言；另有 2 节点 API DAG；但**不是同一个 AIQE Run**，缺 Playwright/DB Driver 统一编排 |
| TC-003 | API 首次失败 + 重试成功 → 不得掩盖失败 | **VERIFIED** | fault proxy 注入一次 503；attempt1 FAILED/attempt2 PASSED 均保留；Run PASS（`test5-retry/report.json`） |
| TC-004 | 广告/其他功能浮层交叉干扰 | **PARTIAL** | test5 Core 登录弹层 PASS；注入浮层后 Integration 被拦截并分类 CROSS_FEATURE_DEFECT；未接入 AIQE 两个正式 Run/Defect Draft |
| TC-005 | 并发数据污染 | **VERIFIED** | 同一赛事 resource key 的两个 Run 由 scheduler 锁串行；A finish <= B start，无重叠（`test5-concurrency/report.json`） |
| TC-006 | 上游第三方故障 | **VERIFIED** | 504 stub → Node BLOCKED/UPSTREAM_5XX；Assertion BLOCKED；未创建 Bug（`test5-upstream/report.json`） |
| TC-007 | UI Runner 自身故障 | **PARTIAL** | 有真实 Chromium 流程；未强制 kill 浏览器验证 Runner 故障归因 |
| TC-008 | 开发修复后点击回归 | **BLOCKED** | 无 TC-004 缺陷草稿/人工确认/修复 commit SHA |
| TC-009 | 多端 AC 对照 | **BLOCKED** | 无 Android Chrome 模拟器/真机 |
| TC-010 | 学习候选发布 | **BLOCKED** | 缺陷/回归产品链路未完成，无法进入学习发布 |

## 平台链路 E2E（本地确定性 SUT，9 passed）

`tests/e2e/aiqe/test_v16_017_platform_chain.py` 覆盖 HTTP/DB/SSRF/fencing/回归/Secret/Noise/Agent 平台链路。
它是**平台能力证据**，不等同任何真实产品 TC；不得用它把 TC-001~010 标成 VERIFIED。

## test5 产品证据（TC-002 支撑）

- 前端：+86 登录、首页浏览、搜索 Arsenal、赛事详情 **PASS**
- 后台：`uu` 登录 → 直播管理/LIVE房直播记录只读 → `/logout` 退出 **PASS**
- MySQL：只读事务查询 `camel_account.user_info` / `camel_studio.sports_favorite` **PASS**
- DAG：`aiqe_test5_dag_e2e.py` 两节点（general → getCountryCode）、4 断言、4 Artifact、Run PASS
- 报告：
  - `work-logs/evidence/aiqe-v16/test5/report.json`
  - `test-platform-v2/backend/work-logs/evidence/aiqe-v16/test5-dag/report.json`（gitignore）

## 结论

- 产品级 TC：**3/10 完全 VERIFIED（TC-003/TC-005/TC-006）**；TC-001/002/004/007 PARTIAL；其余 BLOCKED。
- `V16-017-R2` 仍 BLOCKED；不得宣称 10/10 或 GA。
- 旧 `test_tc_aiqe_001_010.py` 已删除，不再有 body 断言/整文件 skip 假入口。
