# Test5 OpenVPN、接口增改查与钉钉通知实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用用户提供的 OpenVPN 配置恢复测试5网络，通过 DEV 测试平台 Web 导入六组 API 并只执行新增、修改、查询，同时确认钉钉机器人通知可复用于其他项目。

**Architecture:** OpenVPN Connect 只负责把测试5域名路由到内部网络，测试资产的导入、用例生成、环境绑定和执行全部从 `http://localhost:5173` 的 DEV Web 前端完成。接口执行采用“新增→按标识查询→修改→再次查询”的可追溯闭环，并通过方法、路径和业务语义三层过滤排除删除及高副作用接口；钉钉通知复用项目级通知通道和任务生命周期事件。

**Tech Stack:** OpenVPN Connect 3.x、React Web、FastAPI、Playwright、Knife4j/OpenAPI、pytest、钉钉自定义机器人 Webhook。

---

### Task 1: 建立并验证测试5 VPN 连接

**Files:**
- Read only: `C:/Users/26029/Desktop/elevpn.ovpn`
- Evidence: `F:/tmp/test5-vpn-connect.log`

- [ ] **Step 1: 安全检查配置**

  只输出 `remote`、`proto`、`dev`、`route` 等非密钥指令，确认目标为 `router-2f.elelive.cn:1194/udp`，不复制 CA 内容。

- [ ] **Step 2: 使用 OpenVPN Connect Connector 加载配置**

  执行 `ovpnconnector set-config profile C:\Users\26029\Desktop\elevpn.ovpn` 后启动连接，日志写入 `F:\tmp\test5-vpn-connect.log`。若配置要求用户名密码且系统未保存凭据，停止在鉴权阶段并向用户索取测试 VPN 凭据，不猜测体育站点密码。

- [ ] **Step 3: 验证目标路由和 HTTP 可达性**

  分别访问测试5项目页及六个 `doc.html#/home` 地址；成功标准为不再出现 `ERR_CONNECTION_CLOSED`/空响应，并能发现 Knife4j 的 `/swagger-resources` 或 OpenAPI JSON 地址。

### Task 2: 通过 DEV Web 导入六组 OpenAPI 资产

**Files:**
- Temporary browser script: `F:/tmp/playwright-test5-import.js`
- Runtime evidence: `F:/tmp/test5-openapi-import-results.json`

- [ ] **Step 1: 在可见浏览器登录 DEV**

  使用现有 DEV 账号登录 `http://localhost:5173`，选择当前体育项目，进入“接口自动化”。

- [ ] **Step 2: 逐个预览六组文档**

  对 camel-service、live-platform、payment-service、studio-service、konfi-service、account-service 的实际 OpenAPI JSON 地址逐个点击“预览”，记录版本、接口总数、新增数和已存在数；预览失败时不确认导入。

- [ ] **Step 3: 确认导入并核对服务分类**

  仅对预览成功的文档点击“确认导入”，在资产列表核对服务名、路径、请求方式和参数结构，并把导入结果保存为执行证据。

### Task 3: 设计安全的增改查接口用例

**Files:**
- Create: `F:/CamelTv/tests/api/test5/README.md`
- Create after OpenAPI discovery: `F:/CamelTv/tests/api/test5/test5-crud-cases.md`

- [ ] **Step 1: 建立接口功能点清单**

  从实际 OpenAPI 中列出 POST 新增、GET 查询、PUT/PATCH 修改接口的请求方式、URL、必填参数和响应字段；排除 DELETE，以及名称包含 pay、transfer、refund、withdraw、ban、publish、settlement、batch-delete 等高副作用动作的接口。

- [ ] **Step 2: 为每个被执行功能点设计正面和负面用例**

  正面用例验证状态码、业务成功标志、生成标识和查询字段一致性；负面用例覆盖必填为空、非法类型、越界或查询不存在标识，并确认没有产生或修改数据。

- [ ] **Step 3: 在 Web 用例库核对生成结果**

  用例编号采用 `TEST5-<SERVICE>-<序号>`，P0 覆盖增查改主链路，P1 覆盖参数及异常流；每条用例包含明确输入和可验证预期结果。

### Task 4: 从 Web 执行增改查闭环

**Files:**
- Runtime evidence: `F:/tmp/test5-crud-execution-results.json`

- [ ] **Step 1: 绑定测试5环境和鉴权变量**

  在 Web 调试页选择“CamelTv 体育测试5环境”，通过已有加密变量或实际登录接口获取鉴权；日志与证据中不输出密码和完整 Token。

- [ ] **Step 2: 执行唯一前缀测试数据闭环**

  使用 `codex-dev-20260715` 前缀创建测试记录，读取响应生成标识，按标识查询，修改一个无副作用字段，再次查询并验证字段更新。

- [ ] **Step 3: 输出执行结果**

  汇总每个服务的通过、失败、阻塞数量和响应摘要。全程不调用 DELETE，也不调用支付扣款、转账、退款、封禁、发布或结算接口。

### Task 5: 验证钉钉通知通用能力

**Files:**
- Modify only if response判定缺陷需要修复: `F:/CamelTv/test-platform-v2/backend/app/services/notify_service.py`
- Test: `F:/CamelTv/test-platform-v2/backend/tests/test_task_lifecycle_notifications.py`
- Update: `F:/CamelTv/test-platform-v2/docs/DEV-Test5-使用与授权清单.md`

- [ ] **Step 1: 核对钉钉消息协议**

  平台选择提供商“钉钉”时发送 `msgtype=markdown`、`markdown.title`、`markdown.text`；订阅 `task_started`、`task_finished`、`test_result`。

- [ ] **Step 2: 配置真实群机器人后测试**

  用户从钉钉群“机器人管理→自定义机器人”复制 Webhook，在 DEV Web 通知中心新增项目级通道并点击测试。若采用关键词安全模式，关键词设为“测试”；若采用加签模式，则先补充独立 Secret 的加密配置再发送。

- [ ] **Step 3: 验证跨项目隔离**

  通知通道按 `project_id` 隔离，其他项目可分别配置各自机器人；验证一个项目触发任务不会发送到未订阅的另一个项目。

### Task 6: 回归与交付

**Files:**
- Update: `F:/CamelTv/test-platform-v2/docs/DEV-Test5-使用与授权清单.md`

- [ ] **Step 1: 运行后端通知与接口执行测试**

  运行通知生命周期、API worker 和执行器定向测试；成功标准为全部通过。

- [ ] **Step 2: 运行前端生产构建**

  运行 TypeScript 检查与 Vite 构建；成功标准为退出码 0。

- [ ] **Step 3: 更新交付记录**

  写明 VPN 是否成功、六组服务导入数量、增改查执行结果、钉钉配置状态和仍需用户提供的信息，不记录密码、证书或完整 Token。
