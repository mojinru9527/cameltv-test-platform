# AIQE 环境证据 — Camel Test5 真实环境 20 次连续执行

- 生成时间：2026-11-19T02:58:30.167926+00:00
- 目标环境：`https://camel-test5.elelive.cn`（CamelTv Test5 API；页面 `https://camelive-g3-test5.elelive.cn`）
- 结果：**20/20 PASS**，每次 Run 2 节点 / 7 断言
- 证据 JSON：`docs/aiqe/evidence/camel-test5-20.json`（digest `9ae8d77cca6305d5…`）

| # | Run ID | Run Key | 结果 | 节点 | 断言 |
|---|---|---|---|---|---|
| 1 | `b7fda8a4-cdd2-4664-90a8-09090adfd8b7` | CAMEL-TEST5-20261119T025810Z-01 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 2 | `2747735a-89fb-4dd3-bb17-7468d372166d` | CAMEL-TEST5-20261119T025810Z-02 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 3 | `0bc3a600-e93e-4a96-b128-44e70c089314` | CAMEL-TEST5-20261119T025810Z-03 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 4 | `39c0f0b1-13ed-47fd-929d-0f00837ced80` | CAMEL-TEST5-20261119T025810Z-04 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 5 | `ae7bc778-0f24-4d39-8c99-16916c358671` | CAMEL-TEST5-20261119T025810Z-05 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 6 | `fc7f305c-5092-416f-8591-1e45a7ef34c1` | CAMEL-TEST5-20261119T025810Z-06 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 7 | `4efe79ba-b94f-4757-bca0-037c792fc0fa` | CAMEL-TEST5-20261119T025810Z-07 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 8 | `5abb53cc-3792-4d87-8412-d48cb23cdf09` | CAMEL-TEST5-20261119T025810Z-08 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 9 | `94130e9f-361d-43ca-94e7-d3de886e082f` | CAMEL-TEST5-20261119T025810Z-09 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 10 | `af14befb-be35-460f-850e-91fa1249e028` | CAMEL-TEST5-20261119T025810Z-10 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 11 | `719fc897-ca18-4f40-9246-b8ab50820549` | CAMEL-TEST5-20261119T025810Z-11 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 12 | `bf47cf4f-8fb6-4a17-9986-5a753ab956ce` | CAMEL-TEST5-20261119T025810Z-12 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 13 | `1b39b895-333a-434d-97c0-ba1897842980` | CAMEL-TEST5-20261119T025810Z-13 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 14 | `d03396f8-41ae-457c-8b75-c2ee6be7c6ae` | CAMEL-TEST5-20261119T025810Z-14 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 15 | `8daa944b-7f16-40cb-adf7-bc9b0df38c29` | CAMEL-TEST5-20261119T025810Z-15 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 16 | `0efc67ee-6387-4e2f-bce1-b8a97bd42c59` | CAMEL-TEST5-20261119T025810Z-16 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 17 | `7267a1e6-3d50-4b38-9c5c-21af36f52993` | CAMEL-TEST5-20261119T025810Z-17 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 18 | `cf6380c5-b6ab-4b69-9736-dbf204fe5638` | CAMEL-TEST5-20261119T025810Z-18 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 19 | `144f299d-d808-4faf-bb18-324d70c63268` | CAMEL-TEST5-20261119T025810Z-19 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |
| 20 | `4d183881-f092-4807-8e0a-be66d1fc218c` | CAMEL-TEST5-20261119T025810Z-20 | COMPLETED/PASS | home_match:PASSED / client_general:PASSED | 7 |

## 执行链路（只读，不污染测试数据）

1. `home_match`：`GET /camel-service/ee/sports_live/home_match?day=YYYYMMDD&sportType=football`，
   断言 HTTP 200、`$.status=200`、`$.data.today` 存在、`$.data.living_group` 存在；
2. `client_general`：`GET /account-service/ee/client/general`，断言 HTTP 200、`$.status=200`、`$.data.ip` 存在。

## 说明

- 浏览器实测页面可打开；此前 PowerShell 失败是本机到内网的瞬时不可达/证书握手失败，现网络已恢复；
- 全程只发 GET，不创建/修改测试数据；Target Policy 放行 `camel-test5.elelive.cn:443` 与内网 CIDR 192.168.0.0/16；
- 24h soak / 100 并发按用户指示跳过；真实设备与 Runner 出口防火墙仍不在本机能力范围。
