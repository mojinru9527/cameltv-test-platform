# CamelTv 测试用例索引

> 双维度索引：按版本 + 按模块。P0 用例已显式打标供 UI 自动化复用。

---

## 一、按版本

### 用户端

| 版本范围 | 用例文件 | P0 数 | P1 数 | P2 数 |
| --- | --- | --- | --- | --- |
| 1.0.0~14.0.0 (基线) | [functional/BASELINE-用户端-基线功能.md](functional/BASELINE-用户端-基线功能.md) | 75 | 174 | 41 |
| 14.0.0 (UGC核心) | [体育平台最新版本-测试用例.md](体育平台最新版本-测试用例.md) | 28 | 63 | 5 |
| 14.0.0 | [functional/P0-REFUND-首单退币.md](functional/P0-REFUND-首单退币.md) | 8 | 6 | 1 |
| 14.0.0 | [functional/P0-BONUS-充值赠送.md](functional/P0-BONUS-充值赠送.md) | 3 | 2 | 1 |
| 14.0.0 | [functional/P0-LIST-预测列表.md](functional/P0-LIST-预测列表.md) | 5 | 30 | 2 |
| 14.0.0 | [functional/P0-DETAIL-UGC详情.md](functional/P0-DETAIL-UGC详情.md) | 10 | 23 | 2 |
| 14.0.0 | [functional/P0-PAY-充值支付.md](functional/P0-PAY-充值支付.md) | 8 | 10 | 1 |
| 14.0.0 | [functional/P0-HOME-首页推荐.md](functional/P0-HOME-首页推荐.md) | 2 | 5 | 0 |

### 运营后台

| 版本范围 | 用例文件 | P0 数 | P1 数 | P2 数 |
| --- | --- | --- | --- | --- |
| 1.0.0~8.2.0 (全版本) | [functional/ADMIN-运营后台-全版本.md](functional/ADMIN-运营后台-全版本.md) | 136 | 178 | 65 |

---

## 二、按模块

### 用户端功能模块

| 模块 | 功能用例 | 接口用例 |
| --- | --- | --- |
| LIVE 直播/开播 | [BASELINE §1](functional/BASELINE-用户端-基线功能.md) | API-TC-LIVE-* |
| HOME 首页 | [BASELINE §2](functional/BASELINE-用户端-基线功能.md) | — |
| AUTH 注册登录 | [BASELINE §3](functional/BASELINE-用户端-基线功能.md) | — |
| SCHEDULE 赛程 | [BASELINE §4](functional/BASELINE-用户端-基线功能.md) | — |
| MATCH 赛事详情 | [BASELINE §5](functional/BASELINE-用户端-基线功能.md) | API-TC-MATCH-* |
| NEWS 资讯 | [BASELINE §6](functional/BASELINE-用户端-基线功能.md) | — |
| LEAGUE 联赛/球队 | [BASELINE §7](functional/BASELINE-用户端-基线功能.md) | — |
| PROFILE 个人中心 | [BASELINE §8](functional/BASELINE-用户端-基线功能.md) | — |
| SILVER 银钻 | [BASELINE §9](functional/BASELINE-用户端-基线功能.md) | — |
| SHOP 商城 | [BASELINE §10](functional/BASELINE-用户端-基线功能.md) | — |
| PREDICTION 预测 | [BASELINE §11](functional/BASELINE-用户端-基线功能.md) | — |
| SEARCH 搜索 | [BASELINE §12](functional/BASELINE-用户端-基线功能.md) | — |
| CHAT 聊天室 | [BASELINE §13](functional/BASELINE-用户端-基线功能.md) | — |
| ADS 广告 | [BASELINE §14](functional/BASELINE-用户端-基线功能.md) | — |
| PLAYER 球员 | [BASELINE §15](functional/BASELINE-用户端-基线功能.md) | — |
| MOBILE APP端 | [BASELINE §16](functional/BASELINE-用户端-基线功能.md) | — |
| FAQ | [BASELINE §17](functional/BASELINE-用户端-基线功能.md) | — |
| PUSH 推送 | [BASELINE §18](functional/BASELINE-用户端-基线功能.md) | — |
| REFUND 首单退币 | [functional/P0-REFUND-首单退币.md](functional/P0-REFUND-首单退币.md) | [API-TC-REFUND-*](../api-testing/collections/) |
| BONUS 充值赠送 | [functional/P0-BONUS-充值赠送.md](functional/P0-BONUS-充值赠送.md) | — |
| LIST 预测列表 | [functional/P0-LIST-预测列表.md](functional/P0-LIST-预测列表.md) | [API-TC-LIST-*](../api-testing/collections/) |
| DETAIL UGC详情 | [functional/P0-DETAIL-UGC详情.md](functional/P0-DETAIL-UGC详情.md) | [API-TC-DETAIL-*](../api-testing/collections/) |
| PAY 充值 | [functional/P0-PAY-充值支付.md](functional/P0-PAY-充值支付.md) | [API-TC-PKG-*](../api-testing/collections/) + [API-TC-ORDER-*](../api-testing/collections/) |
| HOME 首页推荐 | [functional/P0-HOME-首页推荐.md](functional/P0-HOME-首页推荐.md) | [API-TC-REC-*](../api-testing/collections/) |
| FOLLOW 关注 | (含在 DETAIL) | [API-TC-FOLLOW-*](../api-testing/collections/) |
| WALLET 钱包 | (含在 PAY) | [API-TC-WALLET-*](../api-testing/collections/) |

### 运营后台功能模块

| 模块 | 功能用例 | 接口用例 |
| --- | --- | --- |
| ADMIN-NEWS 资讯管理 | [ADMIN §1](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-STREAM 推流管理 | [ADMIN §2](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-LEAGUE 热门球队/联赛 | [ADMIN §3](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-USER 用户管理 | [ADMIN §4](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-FEEDBACK 反馈/版本更新 | [ADMIN §5](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-SILVER 银钻/任务/商城 | [ADMIN §6](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-AVATAR 头像/勋章 | [ADMIN §7](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-PREDICTION 预测管理 | [ADMIN §8](functional/ADMIN-运营后台-全版本.md) | API-TC-ADMIN-PREDICTION-* |
| ADMIN-BANNER Banner管理 | [ADMIN §9](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-SEARCH 热门搜索 | [ADMIN §10](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-CHAT 聊天室消息 | [ADMIN §11](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-BLOCK 屏蔽/举报 | [ADMIN §12](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-AD 广告管理 | [ADMIN §13](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-TRANS 翻译管理 | [ADMIN §14](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-FAQ FAQ管理 | [ADMIN §15](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-PUSH 推送消息 | [ADMIN §16](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-UGC UGC管理 | [ADMIN §17](functional/ADMIN-运营后台-全版本.md) | API-TC-ADMIN-UGC-* |
| ADMIN-COIN 骆驼币财务 | [ADMIN §18](functional/ADMIN-运营后台-全版本.md) | API-TC-ADMIN-COIN-* |
| ADMIN-CRYPTO 数字货币 | [ADMIN §19](functional/ADMIN-运营后台-全版本.md) | — |
| ADMIN-BONUS 充值赠币活动 | [ADMIN §20](functional/ADMIN-运营后台-全版本.md) | API-TC-ADMIN-BONUS-* |
| ADMIN-GREEN 绿钻流水 | [ADMIN §21](functional/ADMIN-运营后台-全版本.md) | — |

---

## 三、总计

| 端 | 用例文件数 | 功能用例总数 | P0 数 | P1 数 | P2 数 |
| --- | --- | --- | --- | --- | --- |
| 用户端 | 9 | 568 | 111 | 247 | 48 |
| 运营后台 | 1 | 379 | 136 | 178 | 65 |
| **合计** | **10** | **947** | **247** | **425** | **113** |

## 四、UI 自动化输入源 (P0 清单)

以下 P0 用例作为 midscene.js UI 自动化输入（§5）：

### 用户端 V14 P0 (49 条)
- TC-REFUND-001, 002, 004, 005, 007
- TC-BONUS-001, 002, 003
- TC-LIST-001, 002, 004, 005, 008, 010
- TC-DETAIL-003, 005, 006, 019, 020, 023, 024, 026, 029, 031, 032
- TC-PAY-001, 004, 010, 016, 017, 018
- TC-HOME-001, 002
- API-TC-LIST-001, 002, 007
- API-TC-DETAIL-001, 002
- API-TC-UNLOCK-001, 002, 003
- API-TC-REFUND-001, 002, 004, 005, 006
- API-TC-PKG-001
- API-TC-ORDER-001, 002, 003, 004
- API-TC-FOLLOW-001, 003
- API-TC-REC-001
- API-TC-WALLET-001

### 用户端基线 P0 (75 条)
详见 [BASELINE-用户端-基线功能.md](functional/BASELINE-用户端-基线功能.md) 各模块 P0 标注

### 运营后台 P0 (136 条)
详见 [ADMIN-运营后台-全版本.md](functional/ADMIN-运营后台-全版本.md) 各模块 P0 标注
