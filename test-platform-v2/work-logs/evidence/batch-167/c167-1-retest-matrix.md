# C167-1 写操作数据准备与选择器稳定性复测 — 执行矩阵

> 日期：2026-08-13 · 执行器：Codex · 状态：选择器稳定性已完成；写操作待授权环境确认

## 1. 选择器稳定性（已完成）
- 基线：`specs/production-p0-modules.spec.ts`（手工选择器）3 轮，www.camel1.tv + 登录态。
- 结果：8/10 通过、2/10 稳定失败；3 轮结果完全一致（无抖动）。
- 失败根因：P0-UI-001 首页 断言 `REGISTER`、P0-UI-006 我的 断言 `Login` —— 登录态下头部已变为 `11025728 / Silver Diamond`，旧断言假定匿名态。
- 修复建议：两条断言改为「匿名（REGISTER/Login）或已登录（userId/Silver Diamond）」双态兼容。
- 证据：`selector-stability-rounds.json` + round1-3 截图/error-context。

## 2. LLM 生成用例选择器稳定性（待网络恢复）
- 用例 #11415（/my 登录态，此前生产 pass）×3
- 用例 #11206（赛事详情「篮球」启发式选择器，预期稳定失败）×3
- 目的：区分「选择器抖动」与「数据/页面状态不匹配」。

## 3. 写操作数据准备（待授权）
清单 `write-op-inventory.json`（项目内 776 条相关用例）：
- login_register 260 / recharge_payment 310 / withdraw 75 / collect_like_comment 83 / bet_predict 6 / other 42

建议分级执行：
| 级别 | 操作 | 环境 | 风险 |
|------|------|------|------|
| T0 安全 | 未登录拦截、页面渲染、收藏/点赞/评论/Follow（可撤销） | 生产 | 低 |
| T1 金融 | 充值/提现/下注（需金额上限与资金授权） | 生产 | 中-高 |
| T2 全量 | 全部写操作 | Test5（camelive-g3-test5.elelive.cn，需 VPN） | 低（测试环境） |

## 4. 当前阻塞
- 本机到外部网络连接被重置（www.camel1.tv / Railway / Vercel 均 000），远程复测暂停；本地分析已完成。
