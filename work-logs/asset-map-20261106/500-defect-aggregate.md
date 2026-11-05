# 缺陷聚合：缺少必填参数 / 内部异常统一返回 500 兜底

- 来源：31 条只读链路批量执行（`chains-all3`），**8 条链路失败**
- 命中接口：**11 个**（另有 2 行来自「无凭证注入」步骤，命中的是同一批接口）

| 接口 | 链路 | 现象 |
|---|---|---|
| `/client/appVersion/latest` | CHAIN-DOM-发版 | http=200 code=500 131ms |
| `/client/search` | CHAIN-DOM-搜索 | http=200 code=500 113ms |
| `/client/oss/user-image/audit-status` | CHAIN-DOM-文件 | http=200 code=500 115ms |
| `/system/youzan/goods/alert/detail` | CHAIN-DOM-有赞-商品 | http=200 code=500 124ms |
| `/system/youzan/store/goods/channel/batches` | CHAIN-DOM-有赞-店铺 | http=200 code=500 112ms |
| `/client/wx/subscription/templates` | CHAIN-DOM-用户-C端 | http=200 code=500 119ms |
| `/client/wx/subscription/statuses` | CHAIN-DOM-用户-C端 | http=200 code=500 90ms |
| `/client/wx/subscription/status` | CHAIN-DOM-用户-C端 | http=200 code=500 104ms |
| `/client/bannerActivity/enabledList` | CHAIN-DOM-营销-轮播 | http=200 code=500 108ms |
| `/system/pickupOrder/station/screen` | CHAIN-DOM-订单-后台 | http=200 code=500 110ms |
| `/system/pickupOrder/station/orders` | CHAIN-DOM-订单-后台 | http=200 code=500 90ms |

## 结论

1. 这些接口在**缺少必填查询参数/路径参数**时返回 `code=500` + 「出了点问题，请稍后再试（编号 XXXX）」，而不是 400 + 具体字段提示。
2. 与既有登记 `WWY-20261106-05`（非法 JSON/类型错误 500）属**同一缺陷族**，建议合并为一条产品缺陷并附本表。
3. 影响：用户无法自助纠正；错误率指标被污染；链路用例在上游一处缺参即整链失败，掩盖后续业务断言。
4. 复现：按表中接口原样 GET（不带参数）即可稳定复现；全部只读，无数据副作用。
5. 关闭标准：缺参返回 400/422 且 msg 指明字段；`run_all_chains.py --statuses ready,ready-readonly` 复跑 31/31 PASS。