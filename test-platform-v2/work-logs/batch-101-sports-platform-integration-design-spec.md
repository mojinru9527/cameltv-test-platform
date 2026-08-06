# Batch 101 — Design Spec（体育平台承接）

> **Design (🎨)** | Date: 2026-08-06 | Status: 就绪

## 1. API 契约（平台生产）

| 步骤 | 端点 | 载荷 |
|------|------|------|
| 登录 | `POST /auth/login` | `{username, password}` → data.access_token |
| 项目 | `GET /projects` | 取首个项目 id（生产默认项目） |
| Token | `POST /tokens` | `{name:"sports-ci", scopes:["trigger","api"]}` → 明文仅本次回显 |
| 契约导入 | `POST /apitest/import/preview` → `POST /apitest/import/confirm` | `{service_name, source_type:"openapi_text", source_ref, spec_content}`；confirm 加 `create_plan:true, plan_name:"体育平台-{service}"` |
| 环境 | `POST /environments` | `{name:"体育平台-生产", env_type:"prod", base_url:"https://www.camel1.tv", is_production:true}` |
| 变量 | `POST /environments/{id}/variables` | PROD_ALLOWED_HOSTS / PROD_EXPECTED_BUSINESS_TEXT / PROD_SMOKE_OWNER / PROD_LOGIN_AUTHORIZED=false |
| UI 任务 | `POST /ui-tests` | `{name:"体育平台-生产只读冒烟", test_spec:"production-smoke.spec.ts", browser:"chromium", environment_id}` |
| AV 任务 | `POST /av-checks` | `{name:"体育平台-MatchReplays", stream_url, protocol:"HLS"}`（真实 URL 待业务提供时补全） |
| 定时 | `POST /schedules` | `{name:"体育平台-每日API回归", plan_id, cron_expression:"0 3 * * *", enabled:true}` |

## 2. 契约文件

- 导入 `test-platform-v2/tests/api-testing/specs/test5-contracts/*.openapi.json` 中 size>1KB 的 7 个真实契约
  （camel-service / payment / studio / api-gateway / camel-mimo / live-platform / account）；
  gateway-service / konfi / admin 为 no-contract（0 字节或占位），跳过并在报告中登记。

## 3. UI 冒烟（正常浏览器行为）

- `production-smoke.spec.ts`：TC-PROD-001~005（主页可访问、导航面、核心 API 资产、15s 基线、只读请求守卫）+ 授权登录用例（PROD_LOGIN_AUTHORIZED=false 时跳过）。
- 环境变量注入：BASE_URL（环境 base_url）、PROD_ALLOWED_HOSTS=`www.camel1.tv,api.cameltv.live`、
  PROD_EXPECTED_BUSINESS_TEXT=`Watch Free Football Live Streaming`、PROD_SMOKE_OWNER=`sports-integration`。

## 4. 安全

- 管理员密码仅从 `production.env` 读取并立即使用，不回显/不入库/不进日志。
- 产出 Token 明文仅打印一次（脚本输出），由用户保存到 Secret。
- 生产只读：UI 冒烟守卫禁止写请求；AV/API 均为只读。

## 5. 设计签核

结论：**通过**。风险：生产写入需用户授权（用户已确认生产环境接入）；Test5 内网部分保持 DEFERRED。
