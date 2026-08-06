# 运营后台生产只读勘察（Batch 110）

> 登录：https://admcamel.camel1.tv/login（账号 mojinru + 图形验证码 + 短信验证码）
> 只读原则：仅 GET/HEAD 采集页面与菜单；**系统管理模块按要求跳过，不做任何操作**。

## 登录链路（生产实测）

```text
GET  /captcha/generate?uuid={uuid}&random={rand}   # 图形验证码（4 位，区分大小写）
POST /captcha/check   form: userCode&imageVerifyCode&uuid   → success=true 后发送短信
POST /login           form: smsCode&userCode                 → success=true，Set-Cookie ELELIVE_JSESSIONID
GET  /nav             （需 Referer=/main + Accept: application/json）→ 完整菜单树 JSON
```

## 15 个顶级模块（生产菜单，nav.json）

| # | 模块 | 页面（href） | 说明 |
|---|------|-------------|------|
| 1 | 直播管理 | 在播管理 `/router/livevideo/playing`、直播间封面审核、OBS断流白名单、录制配置、主播公告管理、LIVE房直播记录、赛程白名单、开播记录 | 直播视频流/主播管理 |
| 2 | 消息管理 | 推送消息 `/ee/msg_management/PushMsg/index` | 推送配置 |
| 3 | UGC管理 | 订阅记录、文章购买记录、文章统计、创作者统计、文章列表、文章分类、创作者列表 | UGC 内容 |
| 4 | 内容管理 | 资讯分类、资讯列表、FAQ管理、推流活动 | 资讯/FAQ |
| 5 | 联赛及球队管理 | 屏蔽赛事视频、热门联赛 | 联赛/球队 |
| 6 | 商城 | 购买记录、商品管理 | 商城 |
| 7 | 体育直播 | 敏感词管理、禁言管理、运营用户配置、弹幕白名单、Banner展位管理、赛事推流记录、热门搜索、昵称敏感词管理、自动封禁敏感词管理 | 运营配置组 |
| 8 | 装扮管理 | 勋章、头像框 | 装扮 |
| 9 | 赛事预测 | 赛事预测列表、用户参与记录、奖励发放记录、赛事预测风控设置、用户统计、每日统计 | 预测玩法 |
| 10 | 广告管理 | 广告位管理、广告素材管理、广告活动管理 | 广告 |
| 11 | 银钻任务 | 任务内容、邀请好友记录、任务完成记录 | 银钻任务 |
| 12 | 财务管理 | 充值订单管理、充值渠道管理、骆驼币流水、绿钻流水、银钻流水、用户账户 | 财务/资产 |
| 13 | 用户管理 | 举报记录、屏蔽记录、用户列表、意见反馈 | 用户治理 |
| 14 | 风控管理 | 聊天文案白名单 | 风控 |
| 15 | 系统管理 | 日志/账号/角色/菜单/版本更新（**按要求跳过**） | 系统 |

## 证据

- `nav.json`：完整菜单树（生产 API `/nav` 返回）
- `admin-login-result.json` / `login-api-log.json`：登录链路与接口契约
- 页面级 API 采集受会话时长限制为部分（留存 `pages/` 样例）
