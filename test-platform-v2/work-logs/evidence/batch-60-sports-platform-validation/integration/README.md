# TC-B60-FP-INT-001：集成配置与凭据保留验收

执行日期：2026-07-30
入口：`/integration`
视口：`1440×900`

## 范围与数据

当前没有获授权的 Jira/TAPD 非生产端点，因此未伪造连接成功或同步成功。使用 `https://jira.example.invalid` 和明确标记的本地 M 凭据只验证平台自身的表单、加密存储、编辑保留和删除行为；截图不包含凭据。

## 缺陷修复与结果

原问题 `B60-P1-018`：只修改名称时，前端会提交空 Email/Token，覆盖已加密凭据。

修复后：

- 编辑留空时不发送 `auth_json`。
- 只修改 Project Key 等显式字段时，后端与已加密 JSON 合并；空字段表示保持原值。
- API 响应继续只返回 `********`。
- 真实本地 SQLite 解密复核只输出布尔结论：Email、Token、Project Key 均为 `true`，未输出值。
- 坏 URL 在前端拒绝且 POST 数为 0；临时配置经确认后删除。

回归：前端 3 条通过；后端新增 2 条及 Batch 59 管理验收 5 条通过；前端 typecheck 通过。

快照：`../pc-usage-snapshots/FP-INT-001-01-integration-config-PARTIAL.png`。

真实连接、单双向同步、日志和缺陷推拉仍为 `BLOCKED`，需提供 R2 测试项目与最小权限凭据。
