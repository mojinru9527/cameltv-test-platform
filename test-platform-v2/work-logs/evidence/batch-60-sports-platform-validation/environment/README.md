# TC-B60-FP-ENV-001：体育 Test5 环境与变量 UI 验收

执行日期：2026-07-30
入口：`/environment`
视口：`1440×900`
项目：`CamelTv 体育平台`

## 真实数据与替代说明

- 环境名称：`batch60-CamelTv-Test5-G3`
- Base URL：仓库已登记的体育 Test5 G3 地址 `https://camelive-g3-test5.elelive.cn/`（R1；本次未切 VPN、未对地址发请求）。
- 明文变量：`SPORTS_FRONTEND_URL`，值为同一 R1 Test5 地址。
- 加密变量：`SPORTS_TEST_TOKEN`。当前无获授权真实 Token，因此只为验证加密存储和掩码使用明确标记的本地占位值（M），不冒充真实连通证据。

## 已执行结果

| 操作 | UI/API 结果 | 判定 |
| --- | --- | --- |
| 空环境名称提交 | 提示“请输入环境名称”，POST 请求数 0 | PASS |
| 新增 Test5 环境 | POST 成功，列表和详情回显 | PASS |
| 编辑用途说明 | PUT 成功，详情回显新描述 | PASS |
| 新增明文变量 | POST 成功，真实 Test5 地址回显 | PASS |
| 新增加密变量 | POST 成功，列表只显示 `••••••••` 和“加密”标识 | PASS |
| 删除临时环境 | 展示删除确认，DELETE 成功，临时记录从列表消失 | PASS |

快照：`../pc-usage-snapshots/FP-ENV-001-01-environment-variables-PASS.png`。

模板解析、生产保护、跨项目隔离和使用中删除尚未执行，因此模块状态仅为 `PARTIAL PASS`。
