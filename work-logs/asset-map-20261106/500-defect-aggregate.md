# 缺陷聚合：缺少必填参数 / 内部异常统一返回 500 兜底

- 来源：31 条只读链路批量执行（`chains-all3`），**8 条链路因该缺陷失败**
- 命中接口：**8 个**

| 接口 | 链路 | 现象 |
|---|---|---|
| `/system/youzan/store/goods/channel/batches` | CHAIN-DOM-有赞-店铺 | ['code=500!in [200, 403]'] |
| `/system/pickupOrder/station/screen` | CHAIN-DOM-订单-后台 | ['code=500!in [200, 403]'] |
| `/system/pickupOrder/station/orders` | CHAIN-DOM-订单-后台 | ['code=500!in [200, 403]'] |
| `/client/bannerActivity/enabledList` | CHAIN-DOM-营销-轮播 | ['code=500!in [200]'] |
| `/client/appVersion/latest` | CHAIN-DOM-发版 | ['code=500!in [200]'] |
| `/client/oss/user-image/audit-status` | CHAIN-DOM-文件 | ['code=500!in [200]'] |
| `/system/youzan/goods/alert/detail` | CHAIN-DOM-有赞-商品 | ['code=500!in [200, 403]'] |
| `/client/search` | CHAIN-DOM-搜索 | ['code=500!in [200]'] |

## 结论

1. 这些接口在**缺少必填查询参数/路径参数**时，返回 `code=500` + 「出了点问题，请稍后再试（编号 XXXX）」，而不是 400 + 具体字段提示。
2. 与既有登记 `WWY-20261106-05`（非法 JSON/类型错误 500）属**同一缺陷族**，建议合并为一条产品缺陷、附本表接口清单。
3. 影响：用户无法自助纠正；错误率指标被污染；链路用例在上游一处缺参即整链失败，掩盖后续业务断言。
4. 复现：按表中接口原样 GET（不带参数）即可稳定复现；全部为只读，无数据副作用。
5. 关闭标准：上述接口在缺参时返回 400/422 且 msg 指明缺失字段；`run_all_chains.py` 复跑 31/31 PASS。