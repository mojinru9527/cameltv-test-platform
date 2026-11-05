# 链路执行报告（只读批量）

- 链路：**23/31 通过**
- 步骤：**87/98 通过（88.8%）**
- 失败归因：{'product-500': 8}

## 按链路

| 链路 | 优先级 | 结果 | 步骤 | 失败归因 |
|---|---|---|---:|---|
| CHAIN-ASSET-COMPONENT-READONLY | P0 | PASS | 4/4 | - |
| CHAIN-ORDER-C-READONLY | P0 | PASS | 4/4 | - |
| CHAIN-YOUZAN-TRADE-READONLY | P0 | PASS | 4/4 | - |
| CHAIN-DOM-系统-用户角色 | P1 | PASS | 6/6 | - |
| CHAIN-DOM-资产-AI-精修 | P1 | PASS | 6/6 | - |
| CHAIN-DOM-系统-配置 | P1 | PASS | 6/6 | - |
| CHAIN-AUTH-READONLY | P1 | PASS | 4/4 | - |
| CHAIN-DOM-用户-C端 | P1 | FAIL | 1/4 | - |
| CHAIN-DOM-设备 | P1 | PASS | 4/4 | - |
| CHAIN-DOM-有赞-店铺 | P1 | FAIL | 3/4 | {'product-500': 1} |
| CHAIN-DOM-监控 | P1 | PASS | 5/5 | - |
| CHAIN-COMMUNITY-READONLY | P1 | PASS | 4/4 | - |
| CHAIN-DOM-订单-后台 | P1 | FAIL | 3/5 | {'product-500': 2} |
| CHAIN-MESSAGE-READONLY | P1 | PASS | 3/3 | - |
| CHAIN-DOM-营销-轮播 | P1 | FAIL | 5/6 | {'product-500': 1} |
| CHAIN-DOM-资产-娃体 | P2 | PASS | 2/2 | - |
| CHAIN-DOM-订单-C端-其他 | P2 | PASS | 4/4 | - |
| CHAIN-DOM-日记 | P2 | PASS | 1/1 | - |
| CHAIN-DOM-资产-身份卡 | P2 | PASS | 2/2 | - |
| CHAIN-DOM-发版 | P2 | FAIL | 1/2 | {'product-500': 1} |
| CHAIN-DOM-社区-板块 | P2 | PASS | 2/2 | - |
| CHAIN-DOM-资产-背景图 | P2 | PASS | 2/2 | - |
| CHAIN-DOM-其他 | P2 | PASS | 2/2 | - |
| CHAIN-DOM-商品-C端 | P2 | PASS | 3/3 | - |
| CHAIN-DOM-社区-评论 | P2 | PASS | 1/1 | - |
| CHAIN-DOM-文件 | P2 | FAIL | 0/1 | {'product-500': 1} |
| CHAIN-DOM-资产-质检 | P2 | PASS | 1/1 | - |
| CHAIN-DOM-导购业绩 | P2 | PASS | 2/2 | - |
| CHAIN-DOM-资产-换装 | P2 | PASS | 1/1 | - |
| CHAIN-DOM-有赞-商品 | P2 | FAIL | 1/2 | {'product-500': 1} |
| CHAIN-DOM-搜索 | P2 | FAIL | 0/1 | {'product-500': 1} |

## 产品缺陷：缺参/内部异常返回 500 兜底（8）

| 链路 | 接口 | 失败原因 |
|---|---|---|
| CHAIN-DOM-有赞-店铺 | `/system/youzan/store/goods/channel/batches` | ['code=500!in [200, 403]'] |
| CHAIN-DOM-订单-后台 | `/system/pickupOrder/station/screen` | ['code=500!in [200, 403]'] |
| CHAIN-DOM-订单-后台 | `/system/pickupOrder/station/orders` | ['code=500!in [200, 403]'] |
| CHAIN-DOM-营销-轮播 | `/client/bannerActivity/enabledList` | ['code=500!in [200]'] |
| CHAIN-DOM-发版 | `/client/appVersion/latest` | ['code=500!in [200]'] |
| CHAIN-DOM-文件 | `/client/oss/user-image/audit-status` | ['code=500!in [200]'] |
| CHAIN-DOM-有赞-商品 | `/system/youzan/goods/alert/detail` | ['code=500!in [200, 403]'] |
| CHAIN-DOM-搜索 | `/client/search` | ['code=500!in [200]'] |

## 结论口径

1. `product-500` 与 `param-required` 合并计入「缺参/内部异常 500」缺陷族，需按接口清单一次性整改。
2. `capability` 不计缺陷，登记为环境能力缺口（设备令牌）。
3. `spec-or-product` 必须人工复核后才可计入缺陷，避免把规格问题算成产品问题。