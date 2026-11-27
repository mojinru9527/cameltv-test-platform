# TC-AIQE 001–010 数据包与执行映射（2026-11-27）

## 已具备的数据源

| 数据源 | 路径/入口 | 用途 |
|---|---|---|
| 需求 V1–V5 | `C:\Users\26029\Desktop\未来娃娃\未来娃屿软件需求规格说明V{1,2,4,5}.0*.pdf` | TC-001 契约冻结/变更影响 |
| 权威手工验收表 483 条 | `未来娃屿V5.0_用例整理与问题登记_20261117 的手工验收(1)(1)(1)(1)(1).xlsx`（01-功能用例 200 + 补充用例） | TC-001/008 的权威用例与 26 条待复测 |
| 功能用例 1505 条（历史参考） | `未来娃屿V5.0_全量用例明细_含步骤_20261112_全部可见.xlsx` | 仅作历史参考，不再作为验收口径 |
| 接口用例 5165 条 | 同上 `02-接口用例5165`；`未来娃屿V4.0接口用例_V9_20261108.xlsx`（535 接口清单） | TC-003/005/006 API 选择 |
| 缺陷 11 条 | `未来娃屿V5.0_缺陷单_禅道_20261111.xlsx` | TC-008/010 |
| 账号 | tester-launcher/operator/auditor/clerk，密码 123456 | UI/API |
| 后台 | `https://xinyuwadao.com` | Admin UI |
| 接口文档 | `https://s.apifox.cn/78e54676-ebfd-4e55-ab9d-c8ae813c5ed0` | 契约/参数 |
| 服务器/日志 | `43.136.119.131` root；`/data/hz/logs/`、`/data/hz/ruoyi.log` | 故障定位 |
| Redis | `43.136.119.131:6377` | 验证码/缓存注入 |
| 设备 | OnePlus6T `9f0564ba`；微信小程序（本地） | TC-009 |

## 逐条映射

### TC-AIQE-001 需求契约冻结 ✅ PASS
- 输入：V4.0/V5.0 PDF + 用例库
- 产物：`evidence/product/TC-AIQE-001/requirements-diff-v4-v5.{json,md}`
- 结论：V5.0 为基线；53 个新增/变化标题；68 条“变更验证”用例

### TC-AIQE-002 API→Admin UI→Public API→DB ✅ PASS
- 自建 banner 链：`create→DB→Admin UI→Public API→update→delete`
- 证据：`evidence/futurewayu-aiqe-product-chain.json`

### TC-AIQE-003 API 首次失败 + 重试成功
- 现成用例：
  - `TC-V5-MP-60-01` 付款信息失败重试与微信商品名
  - `TC-ADM-01-W` 后台登录弱网/超时与重试恢复
- 需选接口：
  - 小程序下单/支付：`/client/order/**`（Apifox 或接口用例 sheet 可查）
  - 后台登录：`/auth/login`
- 数据：一次可控失败（错 token/注入 503）+ 立即重试成功
- 缺口：503 注入规则；可在本地 Stub 或 Nginx 注入（允许模拟接口）

### TC-AIQE-004 广告/浮层交叉干扰 — **WAIVED（已确认）**
- 用户 2026-11-27 确认：广告模块**不属于未来娃屿项目**
- 权威手工验收表 483 条中无广告/浮层模块
- 处置：`docs/aiqe/v1.6/e2e/TC-AIQE-004-Waiver.md`，状态 OUT_OF_SCOPE / WAIVED

### TC-AIQE-005 并发数据污染
- 现成用例：`TC-SEC-04-C/D/N/P`（幂等与并发）
- 可执行：并发创建/更新自建 banner（N=10），校验唯一性与 DB 行数
- 数据：自建前缀、N、清理规则；已具备

### TC-AIQE-006 上游第三方故障
- 现成用例：`TC-V5-DEV-34-01/04`（换装图片 10s 超时）、`TC-ADM-01-W`（弱网）
- 上游：OSS/有赞/微信支付
- 数据：故障响应样例（504/超时）+ 注入方式（本地 Stub / Playwright route abort / Redis）
- 缺口：注入配置；接口契约可从 Apifox 获取

### TC-AIQE-007 UI Runner 自身故障
- 无需业务数据；本机 runner + 任一页面
- 执行：登录后 kill 浏览器，期望 ERROR/BLOCKED，产出 trace/截图
- 现状：可立即执行

### TC-AIQE-008 开发修复后点击回归 — **复测中，暂 BLOCKED**
- 权威问题表 `03-待复测（26条）`；首个 `WWY-V5-001`
- 2026-11-27 复测：运营 `POST /prod-api/system/device` 空体仍返回 `code=500`，期望 `403`
- 结论：**修复未生效/未部署**；详见 `TC-AIQE-008-Retest-20261127.md`
- 需要：开发修复提交 + 部署后再复测 26 条

### TC-AIQE-009 多端 AC 对照
- 现成用例：`TC-PK-07-P/R/S/X`（多端一致）、89 条跨端用例
- 设备：桌面 Chrome、OnePlus6T（Appium）、微信小程序（半自动）
- 数据：三端页面 URL/账号/AC 表（V5 用例预期结果可直接作 AC）
- 缺口：小程序开发者模式（无权限）→ 只能用半自动截图

### TC-AIQE-010 学习候选发布
- 现成：11 条 V5 缺陷 + 400+ 轮执行结果
- 需要：缺陷标注（确认/关闭）、Benchmark 数据集、baseline、阈值、发布批准人
- 缺口：标注与批准；AIQE learning curator 本地可跑但需数据集

## 建议顺序

1. TC-007（立即可跑）
2. TC-005（自建数据并发）
3. TC-003（Stub 注入 503）
4. TC-004 走 WAIVED（需产品确认）
5. TC-009（桌面+安卓；小程序半自动）
6. TC-006（Stub/路由注入）
7. TC-008（等修复部署）
8. TC-010（等标注/批准）
