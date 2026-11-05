# live CI 接入说明：`ASSET_MAP_ENV_JSON` 与 self-hosted runner

> 对应工作流：`.github/workflows/asset-map-gate.yml` 的 `live-assertions` job。
> 该 job **不会**在 PR 上自动运行（`workflow_dispatch` 手动触发），避免把生产断言压到每次提交。

## 1. 它跑什么

| 步骤 | 内容 | 依赖 |
|---|---|---|
| HTTP 断言 | `fixtures/http-checks.json`（13 条：幂等/越权/参数/回调/脱敏） | 被测环境可达 + 三类凭据 |
| 链路执行 | 31 条只读链（`ready` + `ready-readonly`），含无凭证拒绝注入 | 同上 |
| 归因 | `report_chains.py` 把失败分为 product-500 / capability / authz-spec | — |
| 门禁 | 页面完整度 ≥95%、未归类 ≤5%、断言通过率 ≥90% | — |

## 2. 凭据格式：`ASSET_MAP_ENV_JSON`

一个 **JSON 对象**，字段固定四个：

| 字段 | 必填 | 示例 | 说明 |
|---|---|---|---|
| `base_url` | ✅ | `https://example.com/prod-api` | 被测接口根地址；**不要以 `/` 结尾**；生产要求 https |
| `admin_token` | ✅ | `eyJhbGciOi...` | 后台 Bearer Token（`Authorization: Bearer <token>`） |
| `client_token` | ✅ | `aVNZbGhsF0...` | C 端令牌（请求头 `token: <token>`） |
| `clientid` | 建议 | `e5cd7e48...` | RuoYi 客户端标识，后台接口需要 |

最小示例（**占位值，勿直接使用**）：

```json
{
  "base_url": "https://example.com/prod-api",
  "admin_token": "<ADMIN_JWT>",
  "client_token": "<CLIENT_TOKEN>",
  "clientid": "<CLIENT_ID>"
}
```

校验命令（不联网，只检查格式）：

```bash
python scripts/test-asset-map/refresh_env.py --check runtime/env.json
```

校验会拦掉：缺字段、`base_url` 末尾带 `/`、非本地地址用明文 http、token 明显被截断。

## 3. 两种配置方式

### 方式 A：静态令牌（最快，但有时效）

适用：临时验证、令牌有效期内的单次运行。

1. 在能访问被测环境的机器上取到 `admin_token` / `client_token`（浏览器 DevTools 或 Redis）；
2. 组装 `env.json`（见上）；
3. 写入仓库 Secret：

```bash
gh secret set ASSET_MAP_ENV_JSON --repo <owner>/<repo> < runtime/env.json
```

> 令牌失效后必须重设；JWT 通常几小时到一天过期。

### 方式 B：运行时自动刷新（推荐）

适用：self-hosted runner 长期使用。只保存**账号口令 + Redis**，令牌每次运行时现取。

需要新增的 Secret：

| Secret | 用途 |
|---|---|
| `ASSET_MAP_BASE_URL` | 被测接口根地址 |
| `ASSET_MAP_CLIENTID` | RuoYi clientId |
| `ADMIN_USER` / `ADMIN_PASSWORD` | 后台账号（建议用只读/最小权限测试账号） |
| `ASSET_MAP_CLIENT_PHONE` | C 端测试手机号（用于从 Redis 取 token） |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` / `REDIS_DB` | 读验证码答案与 C 端 token |

生成方式（脚本会走「取验证码 → Redis 读答案 → 登录」并落盘）：

```bash
python scripts/test-asset-map/refresh_env.py --out runtime/env.json
```

工作流已支持：**当 `ASSET_MAP_ENV_JSON` 为空但 `ADMIN_PASSWORD` 存在时**，自动走方式 B（见 workflow 的 `Restore runtime credentials` 步骤）。

## 4. runner 前置条件

| 项 | 要求 |
|---|---|
| runner | `runs-on: [self-hosted, linux]`，能访问被测环境与 Redis |
| 网络 | 能出网到 npm/pypi（安装 pyyaml/jsonschema），能到被测域名 |
| Python | 3.11+；`pip install pyyaml jsonschema requests` |
| Playwright | 只有 `web` 断言需要；live 默认只跑 `http` 断言与链路，无需浏览器 |
| 权限 | Secret 仅在该仓库/环境可见；建议放到 GitHub **Environment**（如 `production-test`）并加保护规则 |

## 5. 运行与验证

```bash
# 手动触发
gh workflow run asset-map-gate.yml --repo <owner>/<repo> -f min_assert_pass=0.9

# 查看结果
gh run list --workflow asset-map-gate.yml --limit 3
gh run download <run-id> -n asset-map-live   # 下载 runtime/ 证据
```

预期产物：`runtime/env.json`（**不上传**）、`runtime/http-assertions.csv`、`runtime/chains/summary.csv`、`runtime/chains/chain-report.md`、`runtime/gate-report.json`。

## 6. 安全要求

1. **只放仓库 Secret**，不要提交到 Git；`env.json` 落盘后 `chmod 600`。
2. 上传 artifact 时**排除** `env.json`（当前 workflow 只传 `runtime/`，请确认未把 tokens 写进 CSV；断言 CSV 只含路径/状态码/耗时）。
3. 使用**专用测试账号**，最小权限；C 端测试号不绑定真实支付方式。
4. 定期轮换：`ADMIN_PASSWORD` 与 `REDIS_PASSWORD` 建议 90 天轮换；令牌类 Secret（方式 A）随过期自动失效。
5. 生产断言只读：链路默认只跑 `ready`/`ready-readonly`，写操作链需单独批准后才纳入。

## 7. 排障速查

| 现象 | 原因 | 处理 |
|---|---|---|
| `缺少 ASSET_MAP_ENV_JSON` | Secret 未配或为空 | 配置方式 A 或 B |
| `取验证码失败` | base_url 不对/网关拦截 | 确认 `ASSET_MAP_BASE_URL` 指向 `/prod-api` 且网络可达 |
| `Redis 中未找到验证码答案` | `REDIS_DB` 错或前缀变更 | 默认 db 5、key `global:captcha_codes:<uuid>`；用 `redis-cli -n 5 keys 'global:captcha_codes:*'` 核对 |
| `登录失败: code=403` | 账号无权限/被停用 | 换测试账号，或确认租户/clientId 正确 |
| `Redis 中未找到该手机号的 C 端 token` | 测试号未登录或 token 被清理 | 让测试号重新登录一次 |
| `assertion_pass_rate` 低 | 被测环境有真缺陷 | 看 `chain-report.md` 的 product-500 / authz-spec 归因，不要直接放宽阈值 |
| `Gate FAIL: endpoint_assignment` | 适配器 `domain_map` 漏了新路径 | 跑 `suggest_domains.py` 生成候选并补进适配器 |

## 8. 与标准的关系

本文件是 `docs/standards/test-asset-map-standard.md` §12「CI 接入」的凭据与 runner 细则；口径、阶段门禁、覆盖率定义仍以该标准为准。
