# 未来娃屿生产环境只读验证（用户报备授权）

> 用户确认：未来娃屿**没有 Test 环境**，已报备允许在**生产环境只读**测试。
> 因此本流程只允许 GET/HEAD/OPTIONS 与只读 SQL，**不产生产品 TC PASS**；
> 产品级 TC-AIQE-001..010 需要写操作/设备/Benchmark，只读授权下仍为 BLOCKED。

## 1. 需要提供的环境信息（只读）

| 变量 | 说明 | 示例 |
|---|---|---|
| `FUTUREWAYU_BASE_URL` | C 端/公开 API 基址 | `https://<prod-domain>` |
| `FUTUREWAYU_ADMIN_URL` | 管理后台基址（RuoYi） | `https://<prod-domain>/admin` |
| `FUTUREWAYU_ADMIN_TOKEN` | **只读**管理员 Token（可选；没有则跳过 admin 探测） | `xxxx` |
| `FUTUREWAYU_DB_READONLY_DSN` | MySQL **只读**账号 DSN（可选） | `mysql://ro_user:***@host:3306/futurewayu` |

> 红线：不要提供可写账号；脚本会拒绝非 GET/HEAD/OPTIONS 请求，并对 DB 执行
> `SET SESSION TRANSACTION READ ONLY` + 写入必须被拒绝的探测。

## 2. 执行

```powershell
$env:FUTUREWAYU_BASE_URL="https://<prod-domain>"
$env:FUTUREWAYU_ADMIN_URL="https://<prod-domain>/admin"
$env:FUTUREWAYU_ADMIN_TOKEN="<readonly-token>"
$env:FUTUREWAYU_DB_READONLY_DSN="mysql://ro_user:***@host:3306/futurewayu"

python scripts/aiqe/per_tc/futurewayu_production_readonly.py `
  --output docs/aiqe/v1.6/evidence/futurewayu-production-readonly.json
```

输出状态：

- `PROBED`：至少一个端点可达（不代表产品 TC 通过）；
- `NOT_PROVEN`：未提供地址（当前状态）；
- `UNREACHABLE`：端点不可达（网络/DNS/防护）；
- `FAIL_WRITE_NOT_BLOCKED`：DB 只读账号居然能写 → 立即停止并更换账号。

## 3. 只读探测内容

- 公开 API/健康端点：`/api/health`、`/health`、`/`、`/api/system/config`；
- 管理后台首页与一条配置读取（RuoYi 风格，带只读 Token）；
- MySQL：`SELECT 1`、`SHOW TABLES`、`SHOW DATABASES`，并验证 `CREATE TABLE` 被拒绝。

## 4. 与产品 TC 的关系

只读授权下可做的只是“生产可达性 + 只读权限”证据，**不能**完成：

- TC-001（需要导入 PRD/人工确认）、TC-002（创建赛事/后台配置/清理）、
  TC-003（注入 503 的重试）、TC-004（注入浮层）、TC-005（并发写）、
  TC-006（上游故障注入）、TC-007（kill 浏览器）、TC-008（缺陷回归写入）、
  TC-009（多端设备）、TC-010（Benchmark/候选批准）。

因此 `docs/aiqe/v1.6/e2e/product-results.json` 仍保持空，GA 判定不变。
若后续获得**专用可写 Test 环境**，再按 `product-tc-config.yaml` 的 runner 接入。
