# AIQE 使用与项目接入指南

> 版本：release-m15（2026-11-14）· 适用：`https://swiftbugs.cn`（生产）与 Test 实例
> 目标读者：平台管理员、项目 QA、接入新项目的负责人

---

## 0. 先看结论（TL;DR）

- AIQE 已具备：**项目/权限、Workflow、Execution Profile、Run/Attempt、质量门禁、噪音规则、缺陷回归、学习候选/BugPattern、平台能力矩阵**；
- 生产已启用 **http 节点真实执行**（`PROD-AIQE-c8edbcba` 实测 PASS）；
- **UI/真机节点**需要外部 runner（生产暂未部署）；IoT 目前为**模拟 broker 契约验证**；
- 新项目接入需要提供 **§9 的 5 类资料**；平台方按 **§10 的 7 个步骤**初始化后，即可产出第一条真实 Run。

---

## 1. 能力总览（当前真实状态）

| 能力 | 生产 | Test | 说明 |
|------|:----:|:----:|------|
| Console 菜单/权限 | ✅ | ✅ | `menu:aiqe_runs` 门禁 |
| Workflow 创建/校验/审批 | ✅ | ✅ | 审批后 graph/checksum 冻结 |
| Execution Profile | ✅ | ✅ | 审批后冻结，变更需新 version |
| Run / Attempt / 事件 / Artifact 查询 | ✅ | ✅ | 含 SSE 断线补拉 |
| http 节点真实执行 | ✅ | ✅ | 生产进程内执行器已开启 |
| Playwright（UI）执行 | ⏳ | ✅（本机 runner） | 需带 Chromium 的 runner |
| Android 真机（Appium） | ⏳ | ✅（本机设备） | 需 runner + 设备 |
| 质量门禁 / 噪音规则 | ✅ | ✅ | P0 门禁、90 天强制复核 |
| 缺陷修复回归（Regression） | ✅ | ✅ | 生成 verification Run 记录 |
| 学习候选 / BugPattern | ✅ | ✅ | 误报率 >20% 拒绝批准 |
| 平台能力矩阵 | ✅ 1/1 | ✅ | 有 evidence 才计 available |
| IoT（MQTT） | ⏳ 模拟 | ⏳ 模拟 | 真机待硬件 |

---

## 2. 角色与权限

| 权限点 | 用途 | 默认 |
|--------|------|------|
| `menu:aiqe_runs` | AIQE Console 入口（所有页面）+ 执行任务查看 | 管理员 |
| `defect:list` / `defect:update` | 读/写 Workflow、Profile、噪音规则、学习候选、回归 | 测试角色 |
| `aiqe:workflow:approve` | 审批 Workflow（独立于人审） | 管理员 |
| `aiqe:learning:approve` | 批准/激活学习候选 | 管理员 |
| `apitest:execute` | 注册执行节点（签发节点 token） | 测试/管理员 |
| `execution:manage` | 执行任务管理（创建/回收） | 管理员 |

> 所有 AIQE 接口都需要 `X-Project-Id` 指定项目上下文（登录 token 之外的第二个隔离维度）。

---

## 3. 核心概念与数据流

```text
Project（项目，数据隔离）
  └─ Requirement（需求文档）→ TestCase（用例）
  └─ Workflow（DAG 定义：nodes 依赖/驱动/断言/重试）──审批冻结（checksum）
  └─ ExecutionProfile（隔离/集成/外部 三类执行配置）
  └─ Run（一次执行）→ NodeRun（节点）→ StepAttempt（尝试时间线）
        └─ Artifact（证据） / Event（SSE 事件）
  └─ Defect（缺陷）→ Regression（修复回归）→ verification Run
  └─ LearningCandidate（学习候选）→ BugPattern（误报规则）
  └─ NodeCapabilityManifest（执行节点能力）→ Platform Matrix（能力×平台）
  └─ QualityGate（P0 判定） / NoiseRule（噪音抑制）
```

状态语义：

- Run：`QUEUED → RUNNING → COMPLETED`（`outcome: PASS/FAIL/INCOMPLETE`）；
- 节点：`READY → RUNNING → PASSED / FAILED / BLOCKED`；
- BLOCKED 表示**环境/驱动不可用**，不是失败，不计入通过；
- 失败默认不自动重试；只有 `retry_policy.max_attempts > 1` 且写操作满足幂等约束才重试。

---

## 4. Console 使用

入口：登录后左侧「执行中心」，或直接访问：

| 页面 | 路径 | 用途 |
|------|------|------|
| 执行记录 | `/runs` | Run 列表/详情、attempt、事件、Artifact |
| Execution Profiles | `/aiqe/profiles` | 创建/审批执行配置（审批后冻结） |
| Workflow 审批 | `/aiqe/workflows` | 创建 Workflow、提交审批、按状态筛选 |
| 质量门禁 | `/aiqe/quality-gate` | 输入 P0 统计，判定是否 PASS |
| 噪音规则 | `/aiqe/noise-rules` | suppress/hint/quarantine，最长 90 天 |
| 平台矩阵 | `/aiqe/platform-matrix` | 节点能力×平台，只有带 evidence 的节点算 available |

典型操作：

1. Profile：`新建 Profile` → 填名称/purpose/config → 提交 → 审批（需 `aiqe:workflow:approve`？Profile 用 `defect:update`）→ 冻结；
2. Workflow：`新建 Workflow`（或 API 提交 graph）→ 提交审批 → 审批人通过 → 冻结；
3. 质量门禁：填 P0 总数/通过/失败/未知/未执行 → 判定门禁；
4. 噪音规则：pattern + action + 有效期（quarantine 必须到期时间）。

---

## 5. Workflow Graph 规范

### 5.1 顶层

```json
{
  "schema_version": "1.0",
  "nodes": [ ... ],
  "edges": []
}
```

### 5.2 节点字段

| 字段 | 必填 | 说明 |
|------|:----:|------|
| `key` | ✅ | 节点唯一标识（英文/数字/-/_） |
| `driver` | ✅ | `http` / `playwright` / `db` / `event` / `mobile` / `miniapp` / `device` / `external_e2e` |
| `capability` | 建议 | `api.http` / `browser.chromium` / `device.android` / `mobile.app` / `db.readonly` 等（未注册会被拒） |
| `depends_on` | | 前置节点 key 数组（形成 DAG） |
| `input` | | 驱动参数（http：url/method/headers/params/json/expected_status；playwright：url/click_text/click_mode/expect_text/inject_overlay） |
| `assertions` | | 断言数组；每项需 `expected` 或 `expected_ref`；建议带 `oracle_layer`（REQ/STD/PATTERN） |
| `retry_policy.max_attempts` | | 1..5；**写操作**（POST/PUT/PATCH/DELETE/cleanup）>1 时必须提供 `idempotency_key_expr` 或 `compensation_node` |
| `type` | | `cleanup` 表示清理节点 |

### 5.3 最小可执行示例（http 健康检查）

```json
{
  "schema_version": "1.0",
  "nodes": [
    {
      "key": "health",
      "driver": "http",
      "capability": "api.http",
      "input": {
        "url": "https://swiftbugs.cn/api/v1/open/health",
        "method": "GET",
        "expected_status": 200,
        "timeout_ms": 15000
      },
      "assertions": [
        {"key": "status", "type": "status", "expected": 200, "oracle_layer": "REQ"}
      ]
    }
  ],
  "edges": []
}
```

### 5.4 校验规则（提交时即拒绝）

- 循环依赖、悬空 `depends_on`、重复 `key`；
- 未注册 driver/capability；
- 变量引用 `${nodes.<key>.outputs.<name>}` 必须来自祖先节点；
- 断言缺 `expected`/`expected_ref`（exploratory 除外）；
- 写操作 + 重试却无幂等/补偿。

---

## 6. Execution Profile

| purpose | 含义 | 典型用途 |
|---------|------|----------|
| `core_isolated` | Run 级隔离，核心用例 | P0 回归、可重复验证 |
| `integration` | 跨系统集成 | 多服务/端到端 |
| `external_live` | 外部真实环境 | 生产只读冒烟、第三方依赖 |

创建：`POST /api/v1/aiqe/admin/profiles`，body：`{"name":"...","purpose":"core_isolated","config":{...}}`；
审批通过后 config 冻结，变更需新建版本。

---

## 7. 执行与观测

### 7.1 执行器（谁真正执行）

| 节点类型 | 执行方 | 开关/条件 |
|----------|--------|-----------|
| http / api | 控制面进程内消费者 | `AIQE_INPROCESS_EXECUTOR_ENABLED=true`（生产已开） |
| playwright / ui | 外部 runner（Chromium） | `scripts/qa/aiqe_local_runner.py` + 节点 token |
| appium / device | 外部 runner + 真机 | 同上 + Appium |
| iot | 模拟/真实 MQTT transport | `scripts/qa/mqtt_sim_verify.py`（模拟） |

进程内消费者**只认领 http**；playwright/appium 任务保持 pending，等待 runner。

### 7.2 观测

| 接口 | 用途 |
|------|------|
| `GET /api/v1/aiqe/runs` | Run 列表（project 隔离） |
| `GET /api/v1/aiqe/runs/{id}` | 详情（nodes/outcome） |
| `GET /api/v1/aiqe/runs/{id}/attempts` | 节点重试时间线（PASSED/FAILED/BLOCKED） |
| `GET /api/v1/aiqe/runs/{id}/artifacts` | 证据列表 |
| `GET /api/v1/aiqe/runs/{id}/events` | 事件（断线补拉） |
| `GET /api/v1/aiqe/runs/{id}/events/stream` | SSE 实时事件（`id:`/`retry:`，终态自动关闭） |

---

## 8. 质量与学习

### 8.1 质量门禁

`POST /api/v1/aiqe/admin/quality-gate`，body：

```json
{"p0_total": 10, "p0_passed": 10, "p0_failed": 0, "p0_unknown": 0, "p0_not_run": 0}
```

判定：P0 **全部通过**且无未知/未执行才 PASS；否则不得显示 PASS。

### 8.2 噪音规则

`POST /api/v1/aiqe/admin/noise-rules`：`{"pattern":"...","action":"suppress|hint|quarantine","scope":"run","expires_at":"..."}`

- 最长 90 天强制复核；quarantine 必须有到期时间；
- 支持 PATCH 更新与 `/renew` 续期。

### 8.3 缺陷回归

`POST /api/v1/aiqe/regressions`：

```json
{"defect_id": 123, "fixed_sha": "abcdef1", "previous_run_id": "旧RunID", "environment_snapshot": {"env": "test"}}
```

生成 `source_type=regression` 的 verification Run（`retest_of`/`commit_sha`），旧 Run 只读。

### 8.4 学习候选 / BugPattern

| 操作 | 接口 | 权限 |
|------|------|------|
| 列表/创建 | `GET/POST /api/v1/aiqe/learning/candidates` | `defect:list/update` |
| 评估 | `POST .../{id}/evaluate` `{false_positive_rate, sample_size}` | `defect:update` |
| 批准 | `POST .../{id}/approve` | `aiqe:learning:approve` |
| 激活 | `POST .../{id}/activate` | `aiqe:learning:approve` |
| 规则查询 | `GET /api/v1/aiqe/learning/bug-patterns` | `defect:list` |

误报率 >20% 拒绝批准；未 benchmark 不能批准；重复候选需 `duplicate_of`。

---

## 9. 新项目接入：需要提供什么

> 把下表填好交给平台管理员即可。标 ✅ 为**必填**，其余按能力勾选。

### A. 项目基本信息

| 项 | 必填 | 示例 | 说明 |
|----|:----:|------|------|
| 项目 code | ✅ | `camel1-tv` | 唯一、kebab-case、不可改 |
| 项目名称 | ✅ | `Camel1 TV（真实业务）` | 展示名 |
| 项目描述 | ✅ | 被测系统/范围 | |
| 项目 owner | ✅ | `sportsadmin` | 平台用户名 |
| 成员及角色 | ✅ | `qa01: tester` | 用户名 + 角色（role_id 由平台提供） |

### B. 被测系统（环境）

| 项 | 必填 | 示例 | 说明 |
|----|:----:|------|------|
| 系统类型 | ✅ | Web / API / App / 小程序 / IoT | 决定 driver/capability |
| 环境名称 | ✅ | `test` / `staging` / `prod-readonly` | |
| 访问地址 | ✅ | `https://www.camel1.tv/` | UI 用 URL；API 用 base URL |
| OpenAPI/Swagger | 建议 | `https://.../openapi.json` | 生成接口用例 |
| 测试账号 | ✅（需登录时） | 专用账号，勿用个人号 | 需登录态用例必填 |
| 数据范围 | ✅ | 只读 / 可写测试数据（说明边界） | 写操作需幂等/清理方案 |
| 网络要求 | 建议 | 出口 IP、WAF 白名单、VPN | 反爬/内网系统必填 |
| 证书/代理 | 建议 | 自签证书、代理地址 | |

### C. 测试资产

| 项 | 必填 | 示例 |
|----|:----:|------|
| 需求文档 | 建议 | docx/pdf/md（上传到平台「需求文档」） |
| 已有用例 | 可选 | Excel/Markdown（可导入） |
| Domain Pack | 建议 | `ecommerce` / `saas` / `iot`（无匹配可自定义） |
| P0 清单/验收标准 | ✅ | 哪些必须通过、判定口径 |

### D. 执行资源

| 项 | 必填 | 示例 |
|----|:----:|------|
| 能力需求 | ✅ | `api.http`、`browser.chromium`、`device.android`、`mobile.app` |
| runner 位置 | ✅ | 生产 / 内网 / 本地（决定网络可达性） |
| 并发 | 可选 | 默认 1 |
| Android 设备 | 如需真机 | 型号/系统/包名（如 `ONEPLUS A6010 / Android 11 / com.camelrn`） |
| IoT | 如需 IoT | MQTT host/port/topic/只读账号，或选择模拟 broker |

### E. 策略

| 项 | 必填 | 示例 |
|----|:----:|------|
| 质量门禁口径 | ✅ | P0 全通过才 PASS |
| 噪音规则 | 可选 | pattern + action + 有效期（≤90 天） |
| 证据保留期 | 可选 | 默认 30 天（Artifact GC） |
| 审批人 | ✅ | Workflow 审批、学习候选批准人 |

---

## 10. 接入步骤（平台方 7 步）

前置：管理员登录，`Authorization: Bearer <token>`，后续请求带 `X-Project-Id: <新项目ID>`。

### 步骤 1：创建项目

```bash
curl -X POST https://swiftbugs.cn/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"code":"camel1-tv","name":"Camel1 TV","description":"第二项目"}'
```

### 步骤 2：添加成员

```bash
curl -X POST https://swiftbugs.cn/api/v1/projects/2/members \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"user_id":4,"role_id":2}'
```

### 步骤 3：导入需求/用例（可选）

- 需求：`POST /api/v1/requirements/upload`（multipart 文件）→ 抽取（需要 AI Key）；
- 手工用例：`POST /api/v1/test-cases`：`{"project_id":2,"title":"...","module":"...","case_type":"ui","priority":"P1"}`。

### 步骤 4：注册执行节点能力（运维）

- http：生产已注册 `prod-aiqe-inprocess`（`aiqe:http`/`aiqe:api`）；
- UI/设备：用 `/api/v1/ai/agents/register` 签发节点 token（`apitest:execute`），
  再在具备 Chromium/Appium 的机器上运行 runner（见 §11）；
- 能力矩阵要有 evidence 才显示 available。

### 步骤 5：创建并审批 Workflow

```bash
curl -X POST https://swiftbugs.cn/api/v1/aiqe/workflows \
  -H "Authorization: Bearer $TOKEN" -H "X-Project-Id: 2" -H "Content-Type: application/json" \
  -d @graph.json
# 返回 id 后审批（需 aiqe:workflow:approve）
curl -X POST https://swiftbugs.cn/api/v1/aiqe/workflows/<id>/approve \
  -H "Authorization: Bearer $TOKEN" -H "X-Project-Id: 2"
```

### 步骤 6：创建并审批 Execution Profile

```bash
curl -X POST https://swiftbugs.cn/api/v1/aiqe/admin/profiles \
  -H "Authorization: Bearer $TOKEN" -H "X-Project-Id: 2" -H "Content-Type: application/json" \
  -d '{"name":"core-p0","purpose":"core_isolated","config":{}}'
```

### 步骤 7：创建首条 Run

当前**没有公开的 Run 创建 API**，使用平台自带引导脚本（在 backend 容器内执行）：

```bash
docker cp scripts/qa/aiqe_bootstrap_run.py <backend容器>:/tmp/
docker cp graph.json <backend容器>:/tmp/
docker exec -e PYTHONPATH=/app -w /app <backend容器> \
  python /tmp/aiqe_bootstrap_run.py --project-code camel1-tv --graph /tmp/graph.json
```

输出 run_id/job_id；http 节点会被进程内执行器认领执行。

---

## 11. 首个 Run 验收（DoD）

| 项 | 通过标准 |
|----|----------|
| Run | `COMPLETED` 且 `outcome=PASS` |
| 节点 | `PASSED` |
| Attempt | `/attempts` 返回 `PASSED`（至少 1 条） |
| Job | `completed/success` |
| 平台矩阵 | 对应能力 `available`（有 evidence） |
| Console | `/runs` 能看到该 Run，详情/事件可打开 |

> 生产参考：`PROD-AIQE-c8edbcba`、job 3、run `ef0779eb-…`。

## 12. 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 401 | token 过期/未带 `X-Project-Id` | 重新登录；补项目头 |
| 403 | 无 `menu:aiqe_runs` 或专项权限 | 分配权限/角色 |
| Run 一直 RUNNING/pending | 无消费者/无 runner | 检查执行开关、节点 token、能力是否匹配 |
| 节点 BLOCKED | driver/浏览器/设备不可用 | 装依赖/接设备；不算失败 |
| TC 点击被拦截 | 浮层/反爬/WAF | `inject_overlay` 属预期；WAF 需白名单 |
| 写操作重试被拒 | 缺少幂等/补偿 | 加 `idempotency_key_expr`/`compensation_node` |
| Profile/Workflow 改不动 | 已审批冻结 | 新建 version |

## 13. 当前边界（重要）

1. **没有公开 Run 创建 API**：需引导脚本/运维派发（步骤 7）；回归 API 只生成 verification Run 记录；
2. **没有 manifest 注册 API**：节点能力注册目前走服务层（运维）；
3. 生产 UI/设备执行需额外 runner；生产仅启用 http 进程内执行；
4. IoT 为模拟 broker 验证，真机未接；
5. M9-R1 全量镜像仍用 delta 构建（回滚位完整）。

## 14. 附录：API 速查

| 方法 | 路径 | 权限 |
|------|------|------|
| GET/POST | `/api/v1/projects` | 登录 / `project:create` |
| POST | `/api/v1/projects/{id}/members` | `project:manage` |
| GET/POST | `/api/v1/test-cases` | `case:*` / `defect:update` |
| POST | `/api/v1/requirements/upload` | 需求权限 |
| GET/POST | `/api/v1/aiqe/workflows` | `menu:aiqe_runs` + `defect:list/update` |
| PATCH | `/api/v1/aiqe/workflows/{id}` | `defect:update`（已审批 409） |
| POST | `/api/v1/aiqe/workflows/{id}/approve` | `aiqe:workflow:approve` |
| GET/POST | `/api/v1/aiqe/admin/profiles` | `menu:aiqe_runs` + `defect:*` |
| PATCH / approve | `/api/v1/aiqe/admin/profiles/{id}` | 同上 |
| GET | `/api/v1/aiqe/platform-matrix` | `menu:aiqe_runs` |
| POST | `/api/v1/aiqe/admin/quality-gate` | `defect:list` |
| GET/POST/PATCH | `/api/v1/aiqe/admin/noise-rules` | `menu:aiqe_runs` + `defect:update` |
| GET | `/api/v1/aiqe/runs[...]` | `menu:aiqe_runs` |
| POST | `/api/v1/aiqe/regressions` | `menu:aiqe_runs` + `defect:update` |
| GET/POST | `/api/v1/aiqe/learning/candidates` | `menu:aiqe_runs` + `defect:*` |
| POST | `/api/v1/aiqe/learning/candidates/{id}/approve\|activate` | `aiqe:learning:approve` |
| POST | `/api/v1/ai/agents/register` | `apitest:execute` |
| POST | `/api/v1/execution-jobs/claim\|…/report` | 节点 token |

## 15. 附件与脚本

| 脚本 | 用途 |
|------|------|
| `scripts/qa/aiqe_bootstrap_run.py` | 新项目首条 Run（manifest + graph + dispatch） |
| `scripts/qa/aiqe_local_runner.py` | UI/设备外部 runner（claim/payload/report） |
| `scripts/qa/mqtt_sim_verify.py` | 模拟 MQTT broker 契约验证 |
| `work-logs/M10-closeout-20261114.md` | 本轮交付与证据索引 |

---

**接入联系人**：平台管理员（sportsadmin）。提交 §9 资料后，按 §10 执行，通常 1 个工作日内可产出首条 Run。
