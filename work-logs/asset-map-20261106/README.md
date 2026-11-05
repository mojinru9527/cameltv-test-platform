# 测试资产底图 · 2026-11-06 执行证据

## 1. CI static job 干净检出验证
- git clone 到临时目录后执行：13 项单测、双项目底图、域候选、34 条链路规格、golden 门禁
- 结果：单测 13/13 通过；golden 门禁 **PASS（exit 0）**；artifact 路径全部存在
- 过程中发现并修复：uturewayu.endpoints.json 被 gitignore → 干净检出失败；已入库

## 2. 全量 28 页扫描（R07/R21/R22）
| 准则 | 结果 |
|---|---|
| R07 文本溢出 | 28/28 PASS |
| R22 三档视口 | 28/28 PASS |
| R21 对比度 | 27/28 有测量值且全部 <4.5:1；最低 2.17:1，中位 2.46:1，违规元素 317 处 |

明细：R21-contrast-aggregate.md、web-sweep28.csv（聚合为 1 条缺陷）

## 3. 链路执行（6 条 ready）
| 链路 | 步骤 | 结果 |
|---|---:|---|
| CHAIN-ASSET-COMPONENT-READONLY | 5 | PASS |
| CHAIN-ORDER-C-READONLY | 5 | PASS |
| CHAIN-YOUZAN-TRADE-READONLY | 5 | PASS（只读段；资金段能力缺失） |
| CHAIN-AUTH-READONLY | 5 | PASS（非法登录 403，未发 token） |
| CHAIN-MESSAGE-READONLY | 5 | PASS（不调用会标记已读的 C 端详情） |
| CHAIN-COMMUNITY-READONLY | 5 | PASS |

## 4. 能力矩阵
- 页面：46/84 可执行（54.8%）；后台 46/46，小程序/平板/叫号屏/有赞 全阻塞
- 链路：5/34 可执行（14.7%）；28 条骨架、5 条能力缺失
- 明细：capability-matrix.json

## 5. HTTP 断言
13 条检查：7 PASS / 6 FAIL（不存在对象返 200、非法 JSON 500、缺参 200、pageNum 500、banner 500、用户信息泄露）
明细：http-assertions-20261106.csv

> 环境：xinyuwadao.com 生产（只读为主）；未执行任何资金、删除、真实用户数据操作。
