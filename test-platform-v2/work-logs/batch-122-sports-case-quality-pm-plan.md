# Batch 122 — PM Plan（体育用例重构）

> **PM (🟨)** | Date: 2026-08-08

## 规格摘要
**原始需求**: PRD Batch 122 — 用例按 功能/接口 分离、按 4 入口 + konfi/运营后台 拆域；全模块深度用例（状态机/异常/用户闭环/关联模块）；来源可溯。
**目标时间**: 结构 1 切片 + 核心模块 1 切片 + 全模块 3 切片 + 后台/konfi 1 切片 + 接口结构 1 切片 + 导入/QA/Leader 1 切片。
**交付物**: `docs/体育平台-用例结构规范.md`；`scripts/sports/` 结构校验+导入脚本；`work-logs/evidence/batch-122/cases/*.json` 深度用例；`work-logs/kanbans/DEV-batch-122-sports-case-quality.md`。

## 开发任务

### [ ] Task 1: 用例结构规范 + 校验脚本
**描述**: 定义域/模块/标签规范并落文档；实现结构校验脚本（幂等、可重复执行），把现有用例按规范归类（新增规范域，不动旧数据）。
**验收标准**:
- `docs/体育平台-用例结构规范.md` 定义：域=体育-用户端-功能/体育-运营后台-功能/体育-接口测试；模块路径 `入口/一级/二级`（入口=安卓iOS/PC-web/移动端-web/运营后台/konfi）；tags=功能|接口、优先级、闭环/关联标记。
- `scripts/sports/validate-case-structure.py` 对用例 JSON 做结构校验（模块路径合法性、必填字段、单步用例拦截），退出码 0/1。
**涉及文件**: `docs/体育平台-用例结构规范.md`、`scripts/sports/validate-case-structure.py`
**参考**: PRD §2/§5

### [ ] Task 2: 核心模块深度用例（赛事详情/预测Pick/预测记录）
**描述**: 以 `axure_extract_test/预测.html`、`picks.html`、`赛况/数据/指数/阵容/资料/赛程*.html` + 生产 `camel1.tv/football/{home}-vs-{away}/{id}` 为输入，为 赛事详情 全部 Tab 与 预测/Pick/预测记录 生成深度用例，覆盖 PRD §4 验收逐条（无预测/预测已截止/比赛进行中已截止/「?」帮助/参与状态/预测历史/预测更多比赛/下注成功/结算/奖励发放/三选项全下注/赔率变更/余额不足/达上限）。
**验收标准**: 赛事详情+预测Pick+预测记录 三模块各有 ≥1 主流程闭环 + 全状态/异常用例；预测链路「参与→开奖→结算→奖励→银钻流水」有跨模块用例；PC-web 与移动端（安卓iOS/移动端-web）分别成集。
**涉及文件**: `work-logs/evidence/batch-122/cases/*.json`

### [ ] Task 3: 用户端全模块深度用例（20+ 模块）
**描述**: 按 首页/搜索/资讯/联赛/球队/球员/排行榜/直播/聊天弹幕/个人中心/钱包财务/商城/装扮/活动/银钻任务/UGC/回放/世界杯/FAQ/启动登录权限 逐个模块，用原型 HTML「功能点|说明」+ 生产页面复核生成深度用例。
**验收标准**: 每个模块覆盖 正常流程/空态/无数据源/异常/权限（PC-web/移动端）+ ≥1 条关联模块用例；单步「查看XX」类不再出现。
**涉及文件**: `work-logs/evidence/batch-122/cases/*.json`

### [ ] Task 4: 运营后台 + konfi 深度用例
**描述**: 用 `axure_extract_61930a83`（70+ 后台页）+ `admin-walkthrough/nav.json`（15 模块全菜单）+ `konfi-inventory-sports.json` 生成 运营后台 14 模块与 konfi 配置组深度用例（含 赛事预测后台：预测列表/用户参与/奖励发放/风控设置/用户统计/每日统计）。
**验收标准**: 每个后台菜单页有 新增/编辑/查询/删除/状态流转/权限 用例；konfi 每配置组有 配置读取/下发/异常 用例；与用户端同功能（如 赛事预测）有 admin↔client 关联用例。
**涉及文件**: `work-logs/evidence/batch-122/cases/*.json`

### [ ] Task 5: 接口用例结构拆分 + 核心接口深补
**描述**: 把接口用例归入 `体育-接口测试` 域并按模块路径归类；对 预测(bet/done/cancel/queryOddsSummaryByMatchId) 与 赛事详情(analysis/lineup/team_stats/time/detail_live) 等核心接口，用 batch-110 真实样本补真实请求体/响应字段断言/正负向。
**验收标准**: 核心接口用例不再 body={}、断言含响应字段；接口用例可按模块过滤。
**涉及文件**: `work-logs/evidence/batch-122/cases/api/*.json`

### [ ] Task 6: 用例导入 + 结构落地 + 功能地图 v3
**描述**: 实现 `scripts/sports/import-case-batch.py`（幂等导入新增规范域用例到平台 DB，保留旧数据）；更新 `docs/体育平台-功能模块地图.md` 为 v3（含用例结构矩阵）。
**验收标准**: 导入后按 domain/入口过滤可查；导入脚本可重复执行不产生重复；功能地图 v3 与用例结构一致。
**涉及文件**: `scripts/sports/import-case-batch.py`、`docs/体育平台-功能模块地图.md`

## 质量要求
- [x] 用例 JSON 通过 `validate-case-structure.py`（结构+必填+深度拦截）
- [ ] 导入脚本幂等（二次执行不重复）
- [ ] 每个核心模块 状态机/异常/闭环 覆盖清单（case-quality-checklist）随切片产出
- [ ] 无调试残留；脚本无 print（运行日志除外）
- [ ] 后端 pytest（受影响模块）、ruff F821、前端 typecheck/build 按变更范围执行
