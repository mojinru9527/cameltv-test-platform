---
title: "Batch 61 体育 UI R2 生产级验收用例"
owner: "qa-team"
created: "2026-08-01"
status: "blocked"
tags: ["batch-61", "sports", "ui", "playwright", "test5", "r2"]
---

# Batch 61 体育 UI R2 生产级验收用例

## 1. 基线与通用规则

| 项目 | 固定值 |
| --- | --- |
| 历史基线 | Batch 60 UI `9/23 PASS`；Batch 61 不继承历史 PASS |
| 目标 | 获授权 Test5 真实数据 R2；production 仅独立白名单内只读观测 |
| 浏览器/视口 | 约定支持的 Chromium 矩阵；PC `1440x900`、平板 `768x1024`、移动 `390x844` |
| 自动化入口 | `tests/automation/ui`；环境、URL、run level、allowlist、账号和数据清单均显式注入 |
| 正向 oracle | 可见业务结果 + 对应成功 API + 稳定数据 key；订单/运营核对另含后台/数据 oracle |
| 写链 | 关注、解锁、支付、退款、赠送仅在 `write-authorized` 与独立书面授权全部满足时执行 |
| 证据 | 截图、trace、traffic JSON、控制台和网络记录全部脱敏/canary 扫描；AI 不接收凭据、PII 或原始响应 |
| 结果词汇 | `PASS` / `FAIL` / `BLOCKED` / `NOT RUN`；skip 只允许固定浏览器不兼容 issue ID |

## 2. 功能点覆盖矩阵

| 功能点 ID | 功能点 | 正面用例 | 负面用例 | 必需真实数据/API oracle |
| --- | --- | --- | --- | --- |
| FP-B61-UI-01 | 显式目标和数据 preflight | TC-B61-UI-001 | TC-B61-UI-002 | 环境、URL、allowlist、run level、Secret 引用、数据 manifest |
| FP-B61-UI-02 | 登录与会话恢复 | TC-B61-UI-003 | TC-B61-UI-004 | 当前用户/session API、登录后标识 |
| FP-B61-UI-03 | 首页推荐 | TC-B61-UI-005 | TC-B61-UI-006 | recommended_author、Yield 顺序、成功首页 API |
| FP-B61-UI-04 | 文章列表/筛选/分页 | TC-B61-UI-007 | TC-B61-UI-008 | category、pinned/free/paid article、列表 API |
| FP-B61-UI-05 | 文章详情/媒体/错误恢复 | TC-B61-UI-009 | TC-B61-UI-010 | free/paid article、详情/媒体 API |
| FP-B61-UI-06 | 权益显示与关注/解锁 | TC-B61-UI-011 | TC-B61-UI-012 | locked/unlocked prediction、用户权益 API |
| FP-B61-UI-07 | 用户订单只读查询 | TC-B61-UI-013 | TC-B61-UI-014 | readonly_order、订单 API |
| FP-B61-UI-08 | 运营内容/订单只读核对 | TC-B61-UI-015 | TC-B61-UI-016 | operations-readonly、内容/订单后台 API |
| FP-B61-UI-09 | 充值/支付闭环 | TC-B61-UI-017 | TC-B61-UI-023 | 专用账号、套餐、限额、幂等、订单/账本/审计/cleanup |
| FP-B61-UI-10 | 首单保护/退款闭环 | TC-B61-UI-018 | TC-B61-UI-023 | first-purchase/used-eligibility、Win/Loss、退款/账本/审计 |
| FP-B61-UI-11 | Camel Coin Bonus 闭环 | TC-B61-UI-019 | TC-B61-UI-023 | Bonus/非 Bonus 套餐、余额/账本/审计 |
| FP-B61-UI-12 | 响应式、键盘、控制台和网络质量 | TC-B61-UI-020 | TC-B61-UI-021 | 三视口、键盘流、console、失败/重复请求清单 |
| FP-B61-UI-13 | 证据持久化与敏感信息防泄漏 | TC-B61-UI-022 | TC-B61-UI-023 | canary、截图/trace/traffic/HTML/JSON 扫描 |

13/13 功能点均映射正面和负面用例，设计覆盖率 `100%`。TC-B61-UI-023 是所有未授权写链和敏感证据的共享 fail-closed 门禁，不代表三条写正向用例已执行。

## 3. UI 用例

| 用例 ID | 优先级/类型 | 前置条件 | 操作 | 可观察预期结果与确定性 oracle | 证据 |
| --- | --- | --- | --- | --- | --- |
| TC-B61-UI-001 | P0/正面/preflight | 显式 test5 环境、HTTPS URL、host allowlist、readonly、Secret 引用、完整稳定数据 manifest | 启动指定只读 spec 的首个用例 | preflight 返回 READY 后才创建 browser context；页面请求只发往 allowlist；目标/环境可定位；无默认 URL/账号 | preflight 结果、traffic 摘要、完整 SHA |
| TC-B61-UI-002 | P0/负面/fail-closed | 分别缺环境、URL、run level、allowlist、账号、任一数据 key | 每次只移除一项并启动 suite | 在浏览器启动/网络请求前抛出精确 `B61-BLOCKED:<KEY>`；不得 skip/PASS；外部请求数 0 | 错误码、owner、网络 0 请求证明 |
| TC-B61-UI-003 | P0/正面/登录 | 可用 readonly normal_user；当前登录/session API | 登录，刷新页面，关闭并恢复会话，再访问首页 | 登录后出现稳定用户标识；session API 成功且主体一致；刷新/恢复后路由和身份不丢失；无重复登录请求 | 1440x900 登录后截图、session 响应摘要、console/network |
| TC-B61-UI-004 | P0/负面/登录 | 错误或被拒绝的测试凭据、过期会话引用 | 尝试登录；带过期 session 直达受保护页面 | 提供但被拒绝的凭据记 FAIL（非 BLOCKED/PASS）；显示可理解错误；受保护内容不可见；路由回登录；无账号信息泄露 | 错误态截图、登录/session API、零私有数据证明 |
| TC-B61-UI-005 | P0/正面/首页 | recommended_author、pinned_article、Yield 顺序 | 登录后打开首页并等待推荐 API | 推荐作者和置顶内容按 manifest 业务 key 可见；DOM 顺序与 API 核心数据一致；只有 1 次有效 GET；无永久 loading | PC 截图、DOM 摘要、API/traffic JSON |
| TC-B61-UI-006 | P1/负面/首页 | 不存在推荐 fixture 变体或受控 API 错误环境 | 打开首页并触发空数据/错误恢复 | 缺业务 fixture 是 BLOCKED/FAIL，不得以任意第一条替代；API 失败显示错误/重试；重试恢复后无重复卡片和 stale 数据 | 空/错误态截图、失败 API、恢复后 network |
| TC-B61-UI-007 | P0/正面/列表 | category、pinned/free/paid article；数据量超过一页 | 选择分类、筛选、排序，翻到下一页再返回 | 筛选/排序/分页 DOM 与列表 API/total 一致；置顶规则稳定；URL 状态可恢复；每次动作仅 1 次有效 GET | PC/平板截图、分页 API、DOM/total 对照 |
| TC-B61-UI-008 | P1/负面/列表 | 空分类、不存在筛选、越界页、受控慢/失败 API | 依次触发空结果、越界、失败和重试 | 显示明确空态/错误态；不显示旧列表；越界不崩溃；重试可恢复；无 N+1/重复 GET | 各状态截图、console、request 计数 |
| TC-B61-UI-009 | P0/正面/详情 | free_article、paid_article、可读媒体；详情 API | 从列表进入免费和付费文章详情，播放/查看媒体，返回列表 | 标题/作者/价格/权益等 DOM 与详情 API 一致；免费内容可见、付费锁定语义正确；媒体实际加载；返回后列表上下文保留 | PC 截图、详情/媒体响应、DOM 核心值 |
| TC-B61-UI-010 | P1/负面/详情 | 不存在文章、媒体 404/超时、详情 API 受控失败 | 直达非法详情并触发媒体/接口故障，执行恢复动作 | 显示 404/错误/媒体 fallback；不泄露锁定正文；无无限 spinner/页面崩溃；重试/返回可操作 | 错误态截图、失败请求、console 0 未处理异常 |
| TC-B61-UI-011 | P0/正面/权益 | locked/unlocked/settled prediction；关注/解锁另有 write-authorized | 只读检查各权益状态；若独立授权存在，再执行关注/解锁并回读 | 只读 DOM 与 entitlement API 一致；写入仅在授权下执行，按钮结果、API、后台/数据、审计一致且 cleanup 完成 | 权益截图；若写入，追加前后 API/DB/审计/cleanup 证据 |
| TC-B61-UI-012 | P0/负面/权益安全 | 其他用户权益、low-balance、无 write authorization | 尝试查看他人权益或触发关注/解锁 | 不泄露他人内容；低余额显示确定业务阻断；无授权时在 browser setup 前 `B61-BLOCKED:WRITE_AUTHORIZATION`，无请求/副作用 | 阻断码或拒绝态截图、API/零写证明 |
| TC-B61-UI-013 | P0/正面/订单只读 | readonly_order 属于当前 normal_user | 从用户入口查询订单并打开详情 | 列表和详情的订单号掩码、状态、币种、金额与 payment API 一致；无支付/退款按钮误触发；刷新状态稳定 | PC 截图、订单 API、DOM 字段对照 |
| TC-B61-UI-014 | P0/负面/订单隔离 | 其他用户/不存在订单 key | 搜索或直达订单详情 | 返回无权限/不存在且不泄露金额、状态、用户；页面无 stale 订单；网络无写 method | 错误态截图、403/404 摘要、console/network |
| TC-B61-UI-015 | P0/正面/运营只读 | operations-readonly；free/paid article、readonly_order | 登录运营后台，查询内容和订单，与用户端 009/013 核对 | 运营只读结果与用户端/API 核心字段一致；编辑/发布/退款操作不可用；无写请求 | 内容/订单 PC 截图、后台 API、跨端对照表 |
| TC-B61-UI-016 | P0/负面/RBAC | normal_user 或错误角色 | 访问运营内容/订单路由和直接 API | 路由拒绝或安全跳转；后台数据/数量/结构不可见；无闪现；直接 API 401/403/404；无写副作用 | 拒绝态截图、route/API 证据、console |
| TC-B61-UI-017 | P0/正面/支付写 | 独立书面授权、disposable first-purchase 账号、bounded package、金额上限、幂等、账本/审计/cleanup | 完成一次获批充值/支付，刷新并在用户/运营端核对，执行 cleanup | UI 成功只在支付 API、订单、余额/账本、运营记录、审计全部一致后成立；重复提交幂等；金额不超上限；cleanup 可复核 | UI/API/DB/账本/审计/cleanup 全套脱敏证据 |
| TC-B61-UI-018 | P0/正面/退款写 | 独立书面授权；first-purchase/used-eligibility、settled Win/Loss；退款限额与 cleanup | 分别验证可用和已使用资格，执行一笔获批保护退款并回读 | 资格 DOM/API 一致；仅符合规则记录退款；订单/余额/账本/审计同事务一致；重复请求幂等；cleanup 完成 | 资格/退款 UI、API、DB/账本/审计/cleanup |
| TC-B61-UI-019 | P0/正面/赠送写 | 独立书面授权；Bonus/非 Bonus package、disposable 账号、上限、幂等、cleanup | 购买获批套餐并核对 Camel Coin Bonus，再重复提交 | Bonus 与非 Bonus 规则准确；余额/账本/订单/审计一致；重复提交不重复赠送；cleanup 完成 | 套餐/余额 UI、API、DB/账本/审计/cleanup |
| TC-B61-UI-020 | P0/正面/浏览器质量 | 003/005/007/009/013/015 正常路径可执行 | 在 1440x900、768x1024、390x844 跑关键只读链，并只用键盘完成导航/主操作 | 无重叠/截断/不可操作；焦点可见、名称正确；console 无 error；每个 GET 仅 1 次有效请求；恢复提示可见 | 三视口截图、键盘记录、console/network 汇总 |
| TC-B61-UI-021 | P0/负面/浏览器质量 | 受控慢网、失败请求、窄屏、键盘-only | 在三个视口触发 loading/empty/error/retry 和长文本 | 状态不重排/遮挡；最长文本可读；焦点不丢；失败不显示成功；重试不产生并发重复请求；未处理异常为 0 | 各视口负面截图、console、失败/重复请求清单 |
| TC-B61-UI-022 | P0/正面/证据 | 注入代表 Token/PII 的 canary（非真实值）；正常只读旅程 | 生成 screenshot、trace、traffic JSON、HTML/log，再执行扫描 | 证据保留 case ID、SHA、环境、correlation ID；所有 canary 命中 0；截图中账号/订单按规则掩码；未知二进制不落盘 | 扫描摘要、证据索引、抽检截图 |
| TC-B61-UI-023 | P0/负面/写授权与泄漏 | 缺任一 write authorization 字段或构造会泄漏 canary 的证据 | 分别启动 payment/refund/bonus/follow/unlock 写 spec；向 traffic capture 提交嵌套敏感值 | 写 suite 在 browser setup 前 `B61-BLOCKED:WRITE_AUTHORIZATION`；外部请求 0；敏感 capture 抛错且文件不写入；不得 skip/PASS/Mock 成功 | 结构化阻断、文件不存在/网络 0 证明、本地安全测试 |

## 4. 执行判定

1. 23 条 R2 用例状态由逐行结果汇总，不按 Playwright 收集数、截图数或脚本退出码推导。
2. 只读关键链需在支持浏览器矩阵连续三次首次运行通过，不能依赖 retry 变绿。
3. 017/018/019 没有书面写授权时保持 BLOCKED；TC-B61-UI-023 的阻断 PASS 不能把写业务正向用例改记 PASS。
4. 当前结果见 `test-platform-v2/work-logs/batch-61-sports-ui-results.md`。
