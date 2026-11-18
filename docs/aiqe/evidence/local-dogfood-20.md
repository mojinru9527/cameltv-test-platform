# AIQE 环境证据 — 本地现有环境 20 次连续执行

- 生成时间：2026-11-18T17:09:00.601303+00:00
- 目标环境：http://127.0.0.1:7778（本地运行中的平台后端 + SQLite）
- 结果：**20/20 PASS**，每次 Run 3 节点 / 5 断言
- 证据 JSON：`docs/aiqe/evidence/local-dogfood-20.json`（digest `f2423a5e193f1cec…`）

| # | Run ID | Run Key | 结果 | 节点 | 断言 |
|---|---|---|---|---|---|
| 1 | `28487c2c-9c9f-4993-969f-6ef9e519fb95` | EVID-LOCAL-20261118T170842Z-01 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 2 | `9f34c3a1-098a-416d-a656-7cf23b494bfe` | EVID-LOCAL-20261118T170842Z-02 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 3 | `cf2ff1cb-d52b-4258-83b7-87d39283d8c8` | EVID-LOCAL-20261118T170842Z-03 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 4 | `c99db08a-2dd0-4d6e-9ed5-57b3074d61a9` | EVID-LOCAL-20261118T170842Z-04 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 5 | `4aa846cc-7ede-496d-9c43-48ea315636ff` | EVID-LOCAL-20261118T170842Z-05 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 6 | `63c8005d-9560-41ea-9af9-52e183014803` | EVID-LOCAL-20261118T170842Z-06 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 7 | `247a9da4-bb04-4d19-b357-f25d26e5633a` | EVID-LOCAL-20261118T170842Z-07 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 8 | `e3c1aa73-6d94-42b0-80a5-b45c52ac2602` | EVID-LOCAL-20261118T170842Z-08 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 9 | `dd8a8d59-6e58-4b3b-86a8-89ac0f9d5bf7` | EVID-LOCAL-20261118T170842Z-09 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 10 | `62b24795-eeb7-4368-8211-d2424a6b3d33` | EVID-LOCAL-20261118T170842Z-10 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 11 | `7406e0b6-bf56-443e-8f10-04e2fb82ff69` | EVID-LOCAL-20261118T170842Z-11 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 12 | `2f6f53e8-689f-42d9-a632-a0d5fdb6aa3b` | EVID-LOCAL-20261118T170842Z-12 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 13 | `38b043b3-e43b-4fc6-96a0-e8ca58f28546` | EVID-LOCAL-20261118T170842Z-13 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 14 | `596afcca-0b6f-4981-a107-a12cd5f0b0ce` | EVID-LOCAL-20261118T170842Z-14 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 15 | `b620cb53-89f9-43b8-802f-793966158577` | EVID-LOCAL-20261118T170842Z-15 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 16 | `46c2db17-cc5b-4b41-9350-d6c991666cc9` | EVID-LOCAL-20261118T170842Z-16 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 17 | `5faae541-9a3a-4854-8442-661ed2ab64ca` | EVID-LOCAL-20261118T170842Z-17 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 18 | `bf59a97f-338a-4340-acca-4efa8821ab8c` | EVID-LOCAL-20261118T170842Z-18 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 19 | `847e7069-c55b-495d-828b-6683e6ad6ce9` | EVID-LOCAL-20261118T170842Z-19 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |
| 20 | `555ccc67-7521-4f90-a604-d2a1f1ced335` | EVID-LOCAL-20261118T170842Z-20 | COMPLETED/PASS | health:PASSED / login:PASSED / verify_db_readonly:PASSED | 5 |

## 执行链路

1. `health`：真实 HTTP GET 本地后端 `/api/v1/open/health`，断言 200 与 `$.data.status=ok`；
2. `login`：真实 HTTP POST `/api/v1/auth/login`（密码经 `${secrets.ADMIN_PASSWORD}` 注入，不落库），
   断言 200 与 access_token 存在；
3. `verify_db_readonly`：AUD-002 登记查询读取只读 SQLite（`sys_project`），断言首行存在。

## 说明与限制（按用户确认）

- 平台以本地现有环境（SQLite + uvicorn）执行；未连接 Test/Prod 内网环境（当前网关 502、内网地址不可达、
  test5 SSL 不可用），因此不涉及生产数据。
- 24h soak / 100 并发：按用户指示**跳过**。
- 真实 iOS/Android/小程序设备：本机无 adb/设备实验室，无法产出 VERIFIED 记录；AUD-020 的能力状态与
  Preflight BLOCKED 逻辑已由单测覆盖，设备验收需设备实验室。
- Runner 出口防火墙：本地环境无独立出口，未做外网 egress 实测。
- 人工复核：用户已回复“复核通过”。
