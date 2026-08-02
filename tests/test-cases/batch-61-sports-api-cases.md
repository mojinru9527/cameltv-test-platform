---
title: "Batch 61 体育 API R2 生产级验收用例"
owner: "qa-team"
created: "2026-08-01"
status: "blocked"
tags: ["batch-61", "sports", "api", "test5", "r2"]
---

# Batch 61 体育 API R2 生产级验收用例

## 1. 基线与执行约束

| 项目 | 固定值 |
| --- | --- |
| 需求来源 | Batch 61 计划 Task 8、R2 PRD/PM/Design、生产级模块验收规则 |
| 历史基线 | Batch 60 API `5/16 PASS`；历史结果只用于选例，不继承为 Batch 61 结果 |
| 目标环境 | 获授权的 `test5`；production 只允许另行白名单内 `GET/HEAD` |
| 当前合同 | camel/live/payment/studio/konfi/account 六份带 SHA-256、导出时间、版本和网关路由的 OpenAPI；当前均未提供 |
| 默认权限 | 只读；Live 写入、Payment/退款/赠送写入均需独立书面授权、专用账号、限额、幂等和清理责任人 |
| 凭据 | 只允许 `secret://` 引用；明文密码、Token、Cookie、私钥不得进入 Markdown、命令、日志或证据 |
| 结果词汇 | `PASS` / `FAIL` / `BLOCKED` / `NOT RUN`；缺条件统一为 `B61-BLOCKED:<KEY>` |

合同未冻结前，本文不把 2026-07-15 历史路由复制成当前 method/path。每条用例的“合同绑定点”必须在执行前由当前 OpenAPI 唯一解析，并把 service、operationId、method、path 和合同 SHA 写入平台执行记录。

## 2. 功能点覆盖矩阵

| 功能点 ID | 功能点 | 主流程 | 负面/异常流 | 正面用例 | 负面用例 | 服务 | 历史风险 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FP-B61-API-01 | 首页推荐与热门内容 | 稳定用户读取推荐作者/置顶内容 | 非法分页、重复参数或不存在业务 key | TC-B61-API-001 | TC-B61-API-002 | camel | Batch 60 仅历史只读结果 |
| FP-B61-API-02 | 文章/预测列表与详情 | 按稳定 key 读取免费/付费、锁定/已解锁内容 | 跨用户权益、非法 ID、越权读取 | TC-B61-API-003 | TC-B61-API-004 | live | 旧合同不可证明当前行为 |
| FP-B61-API-03 | 商品与订单只读查询 | 读取 Bonus/非 Bonus 套餐和只读订单 | 非法 currency/订单归属 | TC-B61-API-005 | TC-B61-API-006 | payment | 写交易默认禁止 |
| FP-B61-API-04 | 运营内容只读核对 | 运营只读账号按业务 key 核对文章/预测 | 普通用户或错误角色访问运营资源 | TC-B61-API-007 | TC-B61-API-008 | studio | 后台权限边界待当前合同确认 |
| FP-B61-API-05 | 公共配置读取 | 按稳定配置 key 读取体育配置 | 不存在 key、特殊字符、错误类型 | TC-B61-API-009 | TC-B61-API-010 | konfi | 历史 Konfi 业务 400 |
| FP-B61-API-06 | 会话与用户权益 | 正常用户读取身份、余额和资格摘要 | 缺失/过期 Token、用户 ID 不匹配 | TC-B61-API-011 | TC-B61-API-012 | account | 敏感字段泄露风险 |
| FP-B61-API-07 | 跨服务鉴权与隔离 | 同一身份在六服务获得一致授权语义 | 错角色、跨用户/跨项目资源、限流 | TC-B61-API-013 | TC-B61-API-014 | six-service | A05/A07 强制门禁 |
| FP-B61-API-08 | 测试平台合同执行与持久化 | 导入当前合同并经统一引擎执行、落库、审计导出一致 | 合同漂移、重复执行、生产写方法被拒绝 | TC-B61-API-015 | TC-B61-API-016 | platform | Batch 60 假绿与多入口语义风险 |

覆盖结论：8/8 功能点均有正面与负面用例，功能点设计覆盖率 `100%`；执行覆盖率见结果报告，不能由本文推导为通过。

## 3. API 用例

| 用例 ID | 优先级/类型 | 前置条件与合同绑定点 | 明确输入与步骤 | 入参断言 | 业务断言 | 响应与证据断言 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-B61-API-001 | P0/正面/只读 | camel 当前合同；normal_user、recommended_author、pinned_article；绑定首页推荐/热门查询 operationId | 1. 平台导入合同<br>2. 以只读身份按稳定 key 查询<br>3. 重复一次相同请求 | 必填参数存在；分页最小值与默认值符合合同；UTF-8 编码和可选参数组合合法 | 推荐作者、Yield 顺序、置顶内容与数据清单一致；两次查询无副作用 | HTTP/业务码成功；schema、字段类型/nullability 正确；顺序稳定；延迟在约定预算内；响应无 Secret/PII；保存脱敏请求/响应和 correlation ID |
| TC-B61-API-002 | P1/负面/参数 | camel 当前合同；绑定与 001 相同 operationId | 依次提交缺失必填、空/null、page=0/负数/超上限、错误类型、重复冲突参数、特殊字符和不存在业务 key | 每类非法输入均按合同拒绝或返回受控空集；不得静默改写为其他用户/分类 | 不存在 key 不回退到随机第一条；重复参数语义确定；无新增/修改数据 | 无 5xx；错误 code/message 可定位且不泄露内部结构；列表 count/total 与空结果一致；零写副作用 |
| TC-B61-API-003 | P0/正面/只读 | live 当前合同；free_article、paid_article、locked/unlocked/settled Win/Loss prediction；绑定列表和详情 operationId | 按类别、状态、分页读取列表，再按各稳定业务 key 读取详情 | filter/sort/page/size/ID 类型和值域符合合同；重复 GET 结果幂等 | 免费/付费与锁定/解锁权益展示符合 normal_user；详情归属、状态和列表摘要一致；Win/Loss 结算状态一致 | HTTP/业务码成功；核心字段、媒体 URL 结构、分页 total/order 正确；敏感字段缺失；每个 GET 仅一次有效请求 |
| TC-B61-API-004 | P0/负面/安全 | live 当前合同；normal_user 与不属于该用户的权益资源；绑定详情 operationId | 使用非法 ID、不存在 ID、其他用户资源 ID、错误状态组合和重复请求 | ID 格式/长度/类型严格校验；跨用户 ID 不得被参数归一化为本人资源 | 锁定内容不可泄露正文/预测结果；跨用户/跨项目返回 403/404 等无泄露语义；无关注/解锁写入 | 错误 envelope 稳定；响应不泄露名称、数量、媒体签名或内部 ID；DB/审计无写副作用 |
| TC-B61-API-005 | P0/正面/只读 | payment 当前合同；bonus_package、non_bonus_package、readonly_order；绑定商品和订单查询 operationId | 按受支持 currency 查询套餐；按稳定只读订单 key 查询详情；重复查询 | currency 枚举、订单 key、可选渠道和分页参数符合合同 | Bonus/非 Bonus 标签、币种、展示金额和只读订单状态一致；不得创建支付单或账本流水 | HTTP/业务码成功；金额使用合同规定类型和精度；响应 schema/header/缓存语义正确；订单、账本和审计计数不变 |
| TC-B61-API-006 | P0/负面/安全 | payment 当前合同；其他用户订单 key；绑定与 005 相同 operationId | 提交空/非法 currency、超长订单 key、其他用户订单、重复查询和任何未授权写 method | 枚举/长度/类型错误被拒绝；生产及默认只读上下文中的 POST/PUT/PATCH/DELETE 在发送前阻断 | 不返回他人订单、金额、支付渠道；不创建交易、退款、转账或账本记录 | 受控 4xx/业务错误且无 5xx；敏感支付字段不出现；平台记录 `B61-BLOCKED` 或真实拒绝，不得记 PASS |
| TC-B61-API-007 | P0/正面/只读 | studio 当前合同；operations-readonly 身份；free/paid article、readonly_order；绑定内容/订单后台查询 operationId | 以运营只读角色按稳定业务 key 查询内容和订单摘要，并与用户端 003/005 对账 | 搜索 key、分页、状态筛选、排序和时间边界符合合同 | 内容状态、作者、权益与订单摘要和用户端查询一致；只读身份无编辑/发布能力 | HTTP/业务码成功；total、排序、核心字段一致；审计只记录读取（若合同定义）；无内容/订单变更 |
| TC-B61-API-008 | P0/负面/RBAC | studio 当前合同；normal_user 或错误角色；绑定与 007 相同 operationId | 用普通用户、过期角色和跨项目资源 key 请求运营查询；尝试追加写 method | 角色/项目参数不可由客户端伪造；非法筛选不扩大范围 | 明确拒绝且不泄露后台字段、数量或资源存在性；写操作发送前阻断 | 401/403/404 语义与合同一致；无 2xx 假成功；DB/审计/任务无业务副作用 |
| TC-B61-API-009 | P1/正面/只读 | konfi 当前合同；稳定体育配置 key；绑定公共配置查询 operationId | 读取指定配置并重复请求；与消费方期望字段核对 | key 非空、长度/字符集合法；请求体或 query 形态严格按合同 | 返回指定体育配置，不回退其他租户/默认脏数据；重复读取一致 | HTTP/业务码成功；配置 schema、版本、字段类型正确；不含 Secret；缓存/ETag（如合同定义）一致 |
| TC-B61-API-010 | P1/负面/参数 | konfi 当前合同；绑定与 009 相同 operationId | 提交不存在 key、空/null、错误 JSON 类型、超长值、控制字符和其他项目 key | 每个非法输入有确定校验结果；特殊字符不造成解析绕过 | 不存在配置返回受控空结果或合同错误；不泄露其他项目配置；不产生配置写入 | 无 5xx；错误 code/message 与合同一致；响应无堆栈/SQL/内部地址；记录历史 Konfi 400 是否复现 |
| TC-B61-API-011 | P0/正面/只读 | account 当前合同；normal/low-balance/first-purchase/used-eligibility 用户以 Secret 引用注入；绑定 session/userInfo/entitlement operationId | 分别读取四类稳定身份的用户摘要、余额和资格；重复读取 | 用户标识格式、可选字段和 header 符合合同；Token 不进入请求证据 | 返回身份必须与会话主体一致；余额、首次资格、已使用资格互斥关系正确；无余额或资格变更 | HTTP/业务码成功；核心字段和 nullability 正确；无密码、Token、Cookie、完整 PII；所有证据 canary 扫描为 0 命中 |
| TC-B61-API-012 | P0/负面/鉴权 | account 当前合同；缺失、无效、过期 Secret 测试引用；绑定与 011 相同 operationId | 分别无凭据、错误凭据、过期凭据、用户 ID 与主体不一致发起只读查询 | 缺失/格式/过期输入均不被默认账号替代；用户 ID 不可越权覆盖主体 | 返回未认证/无权限；不得返回用户余额、资格、昵称或资源存在性；会话不被续期 | 401/403 或合同业务码明确；无 200+空数据假成功；响应及平台日志零凭据/PII；零写副作用 |
| TC-B61-API-013 | P0/正面/一致性 | 六当前合同；同一 normal_user；六服务只读 operationId 集 | 在一个授权窗口内以同一 correlation ID 依次执行 001/003/005/007/009/011 的最小查询集 | 各服务 header、租户/项目和身份参数由平台变量解析且值域一致 | 六服务对用户、项目、内容、权益和订单的身份/归属语义一致；无跨服务脏读 | 每个响应合同校验通过；correlation ID 可追踪；总请求数低于限流；报告中的环境、合同哈希、SHA 一致 |
| TC-B61-API-014 | P0/负面/隔离与限流 | 六当前合同；wrong-role/cross-user/cross-project fixtures；明确 rate limit | 执行缺/错 Token、错角色、跨资源、重复请求和受控限流边界；不发写请求 | 身份/项目/资源参数组合严格校验；第 N/N+1 次请求边界可复现 | 任一服务不得越权返回；达到阈值后只限流当前身份且恢复时间符合合同；重复读取无副作用 | 401/403/404/429 与业务错误稳定；Retry-After（如合同定义）正确；不泄露数据；未产生封禁或持久写入 |
| TC-B61-API-015 | P0/正面/平台持久化 | 六合同和完整 manifest；测试平台项目/环境归属正确；统一 API 引擎可用 | 导入合同，选取 001/003/005/007/009/011，执行并导出审计/报告；核对 DB 记录 | 导入合同 SHA/版本/网关路由不可缺失；变量只引用 Secret；重复导入/执行使用明确幂等键 | UI 结果、API 执行记录、DB 行、审计导出和证据 case ID/环境/合同哈希一致 | 平台 API 与 UI 状态同为 PASS 才可通过；结果总数准确；原始凭据/PII/未知二进制不落盘；导出可按 correlation ID 复核 |
| TC-B61-API-016 | P0/负面/平台 fail-closed | 缺一项的 manifest 变体；production 方法策略；绑定平台导入/执行入口 | 逐项移除 VPN 授权、任一合同、Secret 引用、稳定 key、清理规则或 SHA；尝试 production POST；重复提交同一执行 | 缺失字段给出精确 `B61-BLOCKED:<KEY>`；production 仅允许 GET/HEAD；重复输入不创建重复运行 | preflight 未通过时不打开外部连接、不创建执行记录/业务数据；合同漂移必须阻断而非沿用缓存 | 平台返回 BLOCKED/拒绝且 owner/解除条件明确；外部请求数 0；DB、任务、审计无业务执行副作用；不得静默 skip/PASS |

## 4. 执行与证据规则

1. 顺序固定为 preflight -> P0 只读 -> P1 只读 -> 单独批准的写链；任一敏感 canary 命中立即停止并记 `FAIL`。
2. 每条 API 证据必须包含完整代码 SHA、合同 SHA、环境、case ID、时间、脱敏 correlation ID、HTTP/业务/核心数据三层断言。
3. 写链未获授权时只能记 `BLOCKED`；若未来获批，必须新增独立用例核对 UI/API/DB/账本/审计、幂等、额度与 cleanup，不能复用上述只读 PASS。
4. 当前执行结论见 `test-platform-v2/work-logs/batch-61-sports-api-results.md`。
