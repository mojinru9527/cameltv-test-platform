# 项目 Profile — 未来娃屿 V4.0（当前主用例生成对象）

> 仅记录已由环境/需求/历史测试证据确认的事实。未确认项标 `unknown`，不得在用例里当作既定规则。

## 1. 产品面

| 端 | 入口 | 事实来源 |
|---|---|---|
| 管理后台 | `https://xinyuwadao.com`（Vue3 + Element Plus + RuoYi） | 环境实测 |
| 接口 | `https://xinyuwadao.com/hz-api`（HTTP 恒 200，业务码在 `body.code`） | 环境实测 |
| 微信小程序 | 体验版/正式版；PC 微信 WMPF 可运行体验版 | 历史测试记录 |
| 门店平板 App | 1.3.x（微信/支付宝/现金/扫码支付、小票、叫号） | 需求 V4.0 + 接口文档 |
| 叫号屏 | 浏览器大屏 + 店员操作页 | 接口文档分组 |
| C 端商城 | 有赞商城（商品/订单/退款/优惠券核销） | 需求 V4.0 |
| 基础设施 | MySQL（业务库 `hz`，123 表）、Redis 6377（会话 db5）、`/data/hz/ruoyi.log`、`/data/hz/logs/` | 环境实测 |

## 2. 角色模型（后台）

| 角色 | 账号 | 职责 | 可见模块（实测） |
|---|---|---|---|
| 超管 | 未提供 | 系统/角色/菜单/字典/参数/OSS/客户端/有赞同步/平板发版 | 全部 |
| 运营 | tester-operator | 款/组件/系列/店铺/门店设备/订单/导购业绩/帖子/板块/轮播图/小程序消息/活动优惠/身份卡 | 运营域 |
| 审核 | tester-auditor | 款/组件/系列/店铺/订单/帖子/操作日志 | 审核域 |
| 上新 | tester-launcher | 款/组件/系列/AI 精修方案/AI 模型流程 | 资产域 |
| 店员 | tester-clerk | 门店设备、订单 | 门店域 |

C 端身份：游客 / 已授权手机号用户 / 会员（门店码绑定）/ 匿名发帖作者。
**后台身份域与 C 端身份域独立**，不得默认一一对应。

## 3. 后台路由（实测可点，29 个）

```
/home
/asset-management/style | /component | /component-series
/store/youzan-store | /store/device | /store/order | /store/salesman-commission
/community/community-post | /community/community-plate
/marketing/banner-activity | /marketing/message | /marketing/youzan-activity
/settings/component-category | /settings/doll-template | /settings/background
/settings/account | /settings/id-card-setting
/advanced/youzan-sync | /advanced/ai-refine-plan | /advanced/ai-model-flow
/advanced/app-version | /advanced/operation-log
/system/role | /system/menu | /system/dict | /system/config | /system/oss | /system/client
```

## 4. 关键业务对象与状态

| 对象 | 状态/要点 |
|---|---|
| 组件 | AI 处理中 → AI 处理失败 → 待精修 → 待审核 → 待上架/已上架 → 下架；可重新生成 |
| 款 | 图已生成 / 已精修 n/m / 已绑商品 / 已上架 n/m / 已就绪 |
| 订单 | 待付款 → 待发货 → 待收货 → 已完成；自提：备货中 → 请取货 → 已取货；可取消/退款 |
| 退款 | 申请 → 处理中 → 已退款 / 退款失败；可重新退款（按原单号） |
| 身份卡 | 生成 → 审核 → 展示；娃娃名 ≤12 字（生成侧），性格 3 个 |
| 设备 | 待激活 → 在线/离线；绑定门店；平板 App 版本可发版/下线 |
| 轮播图 | 草稿/启用；platform=store/mini_program；生效时间段；sort_order 拖动排序 |

## 5. 已知易错交互点（来自真实缺陷，详见 `historical-bug-pattern-library.json`）

1. 列表搜索/筛选后行操作无响应，需刷新（REG-24/34）。
2. 抽屉关闭后整页失效、遮罩残留（REG-25/26）。
3. 同一字段多入口长度限制不一致（REG-04/20/27/31）。
4. 长文本溢出/截断/遮挡（REG-03/12/17/19）。
5. 删除后无法重建/重拉（REG-29）。
6. 拖拽排序无效（REG-28）。
7. 匿名态可见性错误（REG-07/10/32）。
8. 消息时间漂移 8 小时（REG-13）。
9. 图片上传无尺寸规范导致展示不全（REG-21）。
10. 地址解析（直辖市/重复市名）（REG-23）。

## 6. 执行约束（硬红线）

- 生产环境：禁止删除/修改真实用户数据、真实订单、真实支付/退款、真实社区内容。
- 写操作仅限自建、带唯一前缀的测试数据，结束后清理并登记残留。
- 并发 ≤ 5，写操作间隔 ≥ 300ms；禁止压测与循环轰炸。
- 凭据只在本机使用，报告内脱敏，不入库。
