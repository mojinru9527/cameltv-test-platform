# Camel1.tv 线上站点探索报告与测试方案

> 探索人视角：资深测试工程师（黑盒 + 灰盒）
> 探索方式：Playwright 自动化浏览器（Chromium）全站遍历 + 网络请求抓包 + DOM 结构分析 + 视觉模型截图复核
> 探索日期：2026-08-14
> 站点入口：https://www.camel1.tv/（camel1.tv / camel1.to / camel2.live / camellofutbol.com 多镜像域名）

---

## 0. 执行摘要

- **站点定位**：Camel Live（骆驼TV）国际版 —— 免费足球赛事直播/回放 + 实时比分 + 赛程 + 数据统计 + 新闻资讯 + 赛事预测（免费预测/Pro Picks）的综合体育门户。与工作区内 96 页原型需求的"骆驼TV 用户端"为同一产品线的 WEB 形态。
- **技术栈**：Next.js（App Router, SSR/ISR）+ React + MUI；后端 API 域 `api.cameltv.live`（微服务架构，已见 account-service 等）；CDN `livecdn.cameltv.live` + CloudFront；埋点 神策（sensors.cameltv.live）+ Google Analytics 4 + GTM。
- **覆盖范围**：9 种语言（en/ar/es/id/pt-BR/pt-PT/tr/bn/hi），sitemap 2545 个 URL；首页抓取 641 个链接。
- **业务模块**（13 大域）：首页/导航、赛事直播与回放、赛程与比分、联赛/球队/球员数据、新闻资讯、赛事预测、搜索、用户中心（登录/银钻/商城/收藏/装扮）、FAQ 与反馈、静态合规页、多语言、镜像防封、广告系统。
- **已发现高风险问题**：① 赌博广告弹窗（BC.GAME 等）误挂"REGISTER"入口附近/页面右侧常驻，存在合规与安全风险；② 广告联盟 popunder 会新开标签页跳转广告落地页（bestfungamestoday.com 等成人/博彩页）；③ 页面存在 `https://undefined/...` 加密 iframe（疑似前端配置缺陷）；④ `/head-to-head`、`/q` 裸路径 404；⑤ 未登录时预测/收藏等核心操作被登录弹窗拦截，注册链路依赖第三方广告弹窗，用户体验与转化路径异常。
- **测试建议总纲**：按 13 个业务域 + 广告专项展开功能测试；接口测试以 `api.cameltv.live` 微服务为主线（匿名登录→数据查询→预测/收藏/反馈等写操作），配合埋点验证；接口自动化用 Pytest/requests 或 Postman+Newman 双通道；UI 自动化用 Playwright + POM，重点攻克广告弹窗干扰（拦截广告域、处理 popup、多标签页管理）。

---

## 1. 探索方法与证据

### 1.1 方法

| 手段 | 说明 |
|------|------|
| 全站路由遍历 | 从首页提取全部 641 个站内链接 → 分类（football/team/player/league/news/h2h/replay/功能页）→ 逐一访问记录状态码/标题/结构 |
| 核心路由批量访问 | `/` `/q/news` `/my` `/my/faq` `/my/feedback` `/match-replay` `/hotmatch` `/worldcup-2026` `/free-football-live-streaming` `/winter-window` `/league/...` `/about-us` `/contact-us` `/terms` 等 18 条 |
| 交互探索 | REGISTER 点击、预测按钮点击、Login 弹窗切换（EMAIL/PHONE）、反馈表单、搜索（`/search#q=xxx&f=home`）、语言切换、移动端视口 390×844 |
| 网络抓包 | 记录全部 XHR/Fetch/WebSocket 请求 + 响应体（API 返回 JSON 结构、广告联盟请求） |
| 广告行为观察 | 监听 popup 新窗口与主框架跳转；确认广告弹窗 URL、落地页、触发时机 |
| 视觉复核 | GLM-4V 视觉模型对首页/注册弹窗截图复核（当前会话模型不支持图片输入，使用外部视觉模型） |

### 1.2 已留存证据（探索过程产物）

- 全站路由报告：`04-routes-report.json`（18 条核心路由状态/标题/区块/API/广告）
- 详情页报告：`05-detail-report.json`（比赛详情/球队/搜索/新闻）
- 交互报告：`06-interact-report.json`（注册/预测/反馈/h2h/球员）
- 登录报告：`10-login-report.json`（登录弹窗、Google iframe、sitemap 全文 2545 URL）
- 广告报告：`12-ads-report.json`（广告联盟请求、popunder、落地页）
- 首页截图：`01-home-viewport.png`、`01-home-full.png`（已由视觉模型复核）
- sitemap：`sitemap.xml`（2545 个 URL 全文）

> 证据文件位于探索临时目录 `%TEMP%\cameltv-out\`，报告正文结论均已交叉验证。

---

## 2. 站点整体架构

### 2.1 域名体系

| 域名 | 用途 |
|------|------|
| www.camel1.tv | 主站（本次探索目标） |
| api.cameltv.live | 后端 API 网关（微服务，path 前缀即服务名） |
| livecdn.cameltv.live | 静态资源 CDN（广告素材、图片） |
| sensors.cameltv.live | 神策埋点上报 |
| camel1.to / camel2.live / camellofutbol.com | 镜像/备用域名（防封锁，"Never Lose Access Again" 机制，`/match-replay/{id}` 实为镜像列表页） |
| ukankingwithea.com / andallthemise.org / eflewandatnig.org / moonlighthathel.org / bestfungamestoday.com | 第三方广告联盟（popunder/落地页） |
| take-look.com | 广告跳转目标之一（官方广告位配置的跳转链接） |

### 2.2 技术栈

- **前端**：Next.js App Router（`_next/static/chunks/main-app-*`），SSR 为主（首屏数据直接内联，API 调用少），MUI 组件库（MuiModal 等），Tailwind。
- **后端**：微服务架构，服务名通过 URL 前缀区分：`account-service`（登录/匿名登录/客户端配置/广告位配置）等。响应统一结构：`{"traceId","timestamp","status","data"}` 或 `{"code","msg","detail","success"}`。
- **第三方**：Google Analytics 4（G-P7XLQG47VJ）+ GTM、神策埋点、Google 登录（accounts.google.com/gsi）、Apple 登录（appleid.cdn-apple.com）、Google Play（APP 下载 com.camelrn）。
- **APP**：Android `com.camelrn`（Google Play），iOS App Store；页头有 APP 下载二维码。

### 2.3 关键 API（已抓包确认）

| 接口 | 方法 | 作用 |
|------|------|------|
| `POST /account-service/login/anonymous/web?appCode=D04B29D6B957CD44DC5F9894189380B8` | POST | 匿名登录，返回 key/value（会话凭证），所有页面打开即调用 |
| `GET /account-service/ee/client/general` | GET | 客户端通用配置（返回 IP、region 等） |
| `POST /account-service/ee/ads/activity/get` | POST | 广告位配置下发（INDEX Banner/SidebarDown 等位次、素材 URL、跳转链接、权重、轮播方式） |
| `POST sensors.cameltv.live/sa.gif?project=production` | POST | 神策埋点 |
| `POST google-analytics.com/g/collect` | POST | GA4 埋点 |

> 页面主体数据（比赛列表/比分/球队/球员/新闻/联赛积分）由 SSR 直接渲染进 HTML，未走 XHR——接口测试需重点关注：登录鉴权、广告配置、以及**交互型接口**（预测提交、收藏、反馈提交、搜索建议等，需登录态触发，本次未登录未捕获完整请求体，需在测试环境补抓）。

---

## 3. 业务模块梳理（核心交付）

### 3.1 模块全景图

```
                        ┌────────────────────────────────────────────┐
                        │              Camel Live (www.camel1.tv)     │
                        └────────────────────────────────────────────┘
                                        │
        ┌───────────────┬───────────────┼───────────────┬───────────────┐
        │               │               │               │               │
   ┌────▼────┐    ┌─────▼─────┐   ┌─────▼──────┐   ┌────▼──────┐  ┌─────▼──────┐
   │ M1 首页  │    │ M2 赛事中心│   │ M3 深度数据 │   │ M4 内容生态│  │ M5 用户中心│
   │ 与导航   │    │ (直播/比分)│   │ (联赛/球队/│   │ (新闻/预测)│  │ (账号/资产)│
   └────┬────┘    │ 赛程/回放) │   │  球员)     │   └────┬──────┘  └─────┬──────┘
        │         └─────┬─────┘   └─────┬──────┘        │              │
        │               │               │               │              │
        │      ┌────────▼────┐    ┌──────▼──────┐  ┌─────▼──────┐  ┌────▼──────┐
        │      │ M6 搜索     │    │ M7 预测竞猜 │  │ M8 广告系统│  │ M9 反馈/FAQ│
        │      └─────────────┘    └─────────────┘  └────────────┘  └────┬──────┘
        │                                                               │
   ┌────▼──────┐  ┌───────────┐  ┌───────────┐  ┌────────────┐  ┌──────▼─────┐
   │ M10 多语言 │  │ M11 镜像防封│  │ M12 静态页│  │ M13 埋点统计│  │  M14 商务/APP│
   │ (9语种)   │  │ (备用域名) │  │ (合规页)  │  │ (GA/神策)  │  │  引导下载   │
   └───────────┘  └───────────┘  └───────────┘  └────────────┘  └────────────┘
```

### 3.2 模块明细（功能、页面路由、关联关系）

#### M1 首页与导航（Home & Navigation）— P0
- **路由**：`/`（含 9 语种前缀版本）
- **功能**：顶部导航（Logo、搜索框 `Matches Team Competitions News`、APP 下载二维码、REGISTER 按钮）；内容区 = 热门比赛（Live Matches）、我的收藏（Favorites）、赛事筛选（Competitions）、今日赛程（Today，按联赛分组、时间排序、NS/FT 状态）、比赛回放（Match Replays）、世界杯专题入口、新闻流（All News，10 个分类 tab：FIFA World Cup / Match Preview / Transfer Market / Premier League / Champions League / In-depth Article / Prediction / Other Match News / Today In History / Winter Transfer）、免费直播引流页、页脚（语言切换、About/Contact/Terms、RSS、社媒）。
- **关联**：→M2（点击比赛卡进详情）、→M3（联赛/球队链接）、→M4（新闻）、→M6（搜索）、→M5（REGISTER）、→M8（Banner 广告位）、→M14（APP 下载）、→M11（"Never Lose Access Again" 镜像入口）。
- **作用**：全站流量分发枢纽 + SEO 承接页（title/description 均为长尾 SEO 文案）。

#### M2 赛事中心：直播、比分、赛程、回放（Match Center）— P0
- **路由**：比赛详情 `/football/{slug}/{id}`；热门比赛 `/hotmatch`；进行中 `/match/progressing`；回放列表 `/match-replay`；回放详情 `/match-replay/{id}`（注意：**实际渲染为镜像列表页，疑似路由缺陷**）；免费直播联赛页 `/free-football-live-streaming` 及 `/free-football-live-streaming/{联赛名}`（含 Watch Live 入口）。
- **功能**：比赛详情页含 5 大 tab —— **预测（Prediction）**、**赛况（Stats：H2H/近期战绩/当前赛季数据）**、**指数（Odds：1X2/亚盘/角球/进球）**、**赛程（Schedule）**、阵容/事件（进球/换人/黄牌/伤停补时，比赛进行中实时滚动）；直播流（页面内有视频播放器位，直播流需点击触发；未登录可看，预测需登录）；回放列表按日期+对阵展示，含"Watch Full Match Replay"。
- **关联**：→M3（球队/联赛跳转）、→M7（预测）、→M5（登录拦截）、→M8（直播页广告）、→M6（搜索）。
- **作用**：产品核心价值 —— 免费观赛。

#### M3 深度数据：联赛、球队、球员（Deep Data）— P1
- **路由**：联赛 `/league/{联赛名}`（积分榜/赛程/新闻/球队榜/球员榜）、重定向页 `/r/league/{联赛名}`；球队 `/team/{队名}/{id}`（积分/近期战绩/阵容/基本信息/球员统计/新闻）；球员 `/player/{姓名}/{id}`（身价/合同/国籍/年龄/位置/转会史/赛季统计/比赛记录/新闻）；对阵 `/head-to-head/{日期}-{主队}-vs-{客队}`。
- **关联**：→M2（跳转比赛）、→M4（球队/球员相关新闻）、→M6（搜索直达）。
- **作用**：SEO 内容厚度 + 观赛辅助决策。

#### M4 内容生态：新闻资讯 + 赛事预测内容（Content）— P1
- **路由**：新闻列表 `/q/news`、新闻详情 `/news/detail/{slug}?entry_way=news&u={base64}`；预测内容页 `/tips`（Pro Picks / Match Preview / Bet Guide，含"FIRST PICK LOSES? FULL REFUND"活动）；专题页 `/worldcup-2026`（赛程/积分/对阵图/新闻/FAQ）、`/winter-window`（转会窗专题）。
- **功能**：新闻 10 分类、浏览量展示（如 397/13004）、TOP 标记、时间显示；tips 页含预测/博彩引导内容（合规风险点）。
- **关联**：→M2（预测文章关联比赛）、→M7（预测产品）、→M1（首页新闻流）。
- **作用**：流量与留存内容，SEO 主力。

#### M5 用户中心：账号、银钻、商城、收藏、装扮、设置（User Center）— P0
- **路由**：`/my`（未登录展示 Login 引导 + 菜单）、`/my/faq`、`/my/feedback`；登录/注册弹窗（全局）。
- **功能**：登录（EMAIL / PHONE NUMBER 双 tab + Google + Apple + Forgot password）；注册；个人中心菜单 —— **Silver Diamond 银钻**（余额展示、Free Silver Diamond 领取入口）、**Camel Mall 商城**、**My Favorites 收藏**、**My Outfits 装扮**、**FAQ & Feedback**、**Settings 设置**、**Business Cooperation 商务合作**（camelsportstv@gmail.com）、**User Feedback 反馈**（camellivefeedback@gmail.com）、**Join Our Telegram**。
- **反馈表单**：Issue Type（Lag/Page Optimization/Unable to Connect/Data Error/Account-Related/Other）、内容 500 字上限、联系方式可选、截图附件（file 上传）。
- **关联**：→M2（预测/收藏需登录）、→M8（登录弹窗可能被广告弹窗干扰）、→M9（FAQ/反馈）、→M14（商务邮箱）。
- **作用**：用户资产与留存闭环（银钻激励体系，对应原型 v2.1 虚拟经济）。

#### M6 搜索（Search）— P1
- **路由**：`/search#q={关键词}&f=home`（f=home/match/team/player/news 分类 tab）。
- **功能**：ALL/MATCH/TEAM/PLAYER/NEWS 五种结果分类；搜索框位于顶部导航，占位"Matches Team Competitions News"。
- **关联**：→M2/M3/M4（结果跳转）。
- **作用**：全站信息检索。

#### M7 赛事预测（Prediction）— P0
- **路由**：比赛详情内嵌（Predict Home Win / Draw / Away Win + 赔率）+ `/prediction/more`（Predict More Matches）。
- **功能**：预测三选（主胜/平/客胜）、实时赔率（如 1.18/13.00/7.00）、预测历史（Prediction History）、预测排行榜/Pro Picks。
- **关联**：→M5（未登录弹登录框"Log in to Camel to watch the game for free"）、→M2（比赛）、→M4（预测文章引流）。
- **作用**：核心互动玩法（对应原型"预测比赛/Picks/银钻预测"）。

#### M8 广告系统（Ads）— P1（高风险）
- **官方广告位**：`POST /account-service/ee/ads/activity/get` 下发配置 —— 位次含 INDEX Banner（轮播，权重 displayWeight，素材 livecdn 图片，跳转站内新闻或外链 take-look.com）、SidebarDown 等；displayMethod=round（轮播）/material。
- **第三方广告联盟**：页面上常驻 iframe/图片广告（BC.GAME 博彩广告："20 FREE SPINS DAILY / RECEIVE UP TO 360% DEPOSIT BONUS"）；`andallthemise.org/popunder.gif` 触发 popunder 新窗口（**本次探索中实测弹出了 bestfungamestoday.com 成人博彩落地页**）；多个加密 URL 广告请求（ukankingwithea.com、eflewandatnig.org 等返回 HTML）。
- **触发时机**：页面加载后不定时（约 15s 内出现过 1 次 popup）；点击页面某些区域可能触发。
- **关联**：全站页面（Banner）、直播页、登录弹窗区域。
- **作用**：主要营收；**但赌博广告 + popunder 弹窗 = 合规与安全高风险，必须专项测试**。

#### M9 FAQ 与反馈（FAQ & Feedback）— P2
- **路由**：`/my/faq`（FAQ 列表 + Load More + Feedback 入口）、`/my/feedback`（反馈表单）。
- **功能**：FAQ 10+ 条（举报/网站维护/聊天安全/多设备/商务合作等）；反馈表单 + 附件。
- **关联**：→M5、→M14（联系邮箱）。
- **作用**：客服分流与用户之声。

#### M10 多语言（i18n）— P1
- **路由**：`/` `/en` `/ar` `/hi` `/bn` `/id` `/es` `/pt-BR` `/pt-PT` `/tr`（9 语种），页脚语言切换入口；部分语言有独立 SEO title（如 `/ar` 阿拉伯语、`/tr` 土耳其语）。
- **注意**：robots.txt 禁止了 `/hi/league`、`/hi/team`、`/hi/player`、`/bn/league` 等（印地语/孟加拉语部分页面不收录）。
- **关联**：全站。
- **作用**：全球化获客。

#### M11 镜像与防封（Mirror/Anti-block）— P2
- **路由**：`/match-replay/{id}` 实为 **CamelLive Mirror List**（camel1.to / camel2.live / camel1.tv / camellofutbol.com，Online 状态标记）；全站多处 "Never Lose Access Again!" / "Bookmark this page" 提示（官方链接页入口）。
- **作用**：域名被封后的逃生通道。

#### M12 静态合规页（Static/Compliance）— P2
- **路由**：`/about-us`（产品介绍 + 免责声明）、`/contact-us`（Tel: +60 147201370、Email: camelsportstv@gmail.com）、`/terms`（Privacy Policy 全文）、`/rss.xml`（RSS 输出）。
- **作用**：合规 + SEO + 联系渠道。

#### M13 埋点统计（Analytics）— P2
- 神策（sensors.cameltv.live/sa.gif）+ GA4 + GTM；页面级 page_view/engagement 事件。
- **作用**：用户行为分析。

#### M14 商务合作与 APP 引导（Business/APP）— P2
- 商务合作邮箱（camelsportstv@gmail.com）、Telegram 群、APP 下载（Google Play com.camelrn / App Store）、页头 APP 二维码。
- **关联**：→M5（商务合作入口）、→M1（APP 引导）。

### 3.3 核心业务链路（跨模块）

1. **观赛链路**：首页/搜索 → 比赛详情 → 直播播放（未登录可看）→ 实时比分/事件 → 预测（登录）→ 赛果/回放
2. **账号链路**：REGISTER → 注册弹窗（邮箱/手机/Google/Apple）→ 登录 → /my（银钻/收藏/装扮/设置）
3. **内容链路**：首页新闻流 → 新闻详情 → 关联预测/比赛 → tips 转化
4. **商业化链路**：Banner/广告位 → 站内专题或第三方落地页（take-look.com / 博彩页）；popunder → 广告联盟落地页
5. **防封链路**：主域异常 → 镜像列表页 → 备用域名

---

## 4. 已发现问题清单（探索中实测）

| # | 严重度 | 模块 | 问题描述 |
|---|--------|------|----------|
| 1 | **高** | M8 | 赌博广告（BC.GAME "20 FREE SPINS / 360% DEPOSIT BONUS"）常驻页面/弹窗，与 REGISTER 按钮同屏，合规风险 |
| 2 | **高** | M8 | popunder 广告自动弹出新标签页并跳转成人/博彩落地页（bestfungamestoday.com），影响体验且属高风险广告行为 |
| 3 | 中 | M2 | `/match-replay/{id}` 详情路由实际渲染"镜像列表页"，回放详情功能疑似被错误路由替代或回放页被移除后未清理 |
| 4 | 中 | M2 | `/head-to-head`、`/q` 裸路径 404（sitemap/首页有链接指向 `/head-to-head/...` 但无列表页） |
| 5 | 中 | M6 | 搜索为 hash 路由（`/search#q=...&f=...`），无独立 URL，深链接/SEO 不友好，且搜索页结果依赖 JS 渲染 |
| 6 | 中 | 全站 | 页面存在 `https://undefined/{加密串}` iframe（宽高 0，动态拼接域名时取到 undefined，疑似前端缺陷或隐蔽广告载体） |
| 7 | 低 | M5 | 顶部 REGISTER 按钮点击在部分场景无响应（被广告层遮挡/需精确点击），点击后有时弹出的是广告而非注册表单 |
| 8 | 低 | M7 | `/tips` 页 "No data available"（预测内容为空态处理粗糙） |
| 9 | 低 | M2 | `/match/progressing` 在无进行中比赛时仅显示 "No data available"，无友好空态 |
| 10 | 低 | M1 | 移动端视口（390px）未发现 APP 下载引导条（原型需求有"引导下载APP"功能），待确认 |

---

## 5. 测试策略

### 5.1 测试范围与优先级总览

| 优先级 | 模块 | 说明 |
|--------|------|------|
| P0（每版本必测） | M1 首页、M2 赛事中心（直播/比分/回放）、M5 用户中心（登录/注册/我的）、M7 预测、M8 广告系统 | 核心用户路径 + 营收 + 合规 |
| P1（自动化优先） | M3 深度数据、M4 新闻/tips、M6 搜索、M10 多语言 | 主要功能 |
| P2（时间允许） | M9 FAQ/反馈、M11 镜像、M12 静态页、M13 埋点、M14 商务/APP | 辅助功能 |

### 5.2 功能测试方案

#### 5.2.1 测试设计方法
- 等价类/边界值：表单（反馈内容 0/1/500/501 字、联系方式格式）、搜索关键词（空/1 字/超长 50 上限/SQL 注入/XSS）、预测金额/选择状态、分页 Load More。
- 场景法：观赛全流程、注册→登录→预测→查看预测历史、反馈提交→成功/失败。
- 状态迁移：比赛状态（NS→1H→HT→2H→FT→取消/延期）、登录态（未登录/登录/过期）、网络（弱网/断网→重试）。
- 兼容性：9 语言切换文案完整性；桌面 1920/1440/1024 + 移动 390×844；Chrome/Edge/Firefox/Safari。
- 广告专项（探索性）：弹窗触发时机、关闭入口、跳转目标、被广告遮挡后功能可用性、广告素材缺失降级。

#### 5.2.2 各模块功能测试要点（节选）

| 模块 | 关键用例（功能） |
|------|------------------|
| M1 首页 | 各区块加载成功/部分失败/全失败；比赛状态正确；时间排序；Banner 轮播与跳转；空态；首屏 ≤3s |
| M2 赛事详情 | 比分实时更新（<5s）；事件（进球/红黄牌/换人）正确；Stats/Odds/Schedule tab 切换；Odds 1X2/亚盘数值正确；直播流播放/切换线路；未开始/进行中/已结束状态展示；回放列表日期筛选 |
| M3 深度数据 | 积分榜胜平负与积分计算、排序（积分→净胜球→进球）；球队近期战绩；球员资料/转会史字段完整性；H2H 最近 10 场统计正确性 |
| M4 新闻/tips | 分类 tab 过滤；浏览量展示；TOP 标记；详情富文本渲染；tips 空态；专题页赛程/对阵图/FAQ |
| M5 账号 | 注册（邮箱/手机号/Google/Apple）；验证码；登录错误提示；忘记密码；未登录点击预测弹登录框；登录后 /my 菜单齐全；银钻余额展示；反馈表单各 Issue Type |
| M7 预测 | 三选预测、赔率展示、未登录拦截、预测历史、截止时间、重复预测、预测后状态 |
| M8 广告 | 见 5.2.3 广告专项 |
| M10 多语言 | 9 语种首页/详情页文案完整、日期/数字格式、RTL（阿拉伯语）布局、语言切换后 URL 前缀正确 |

#### 5.2.3 广告系统专项测试（重点）

| 用例方向 | 测试点 |
|----------|--------|
| 展示正确性 | 各广告位（Banner/SidebarDown）素材加载、轮播间隔、权重排序、无素材降级 |
| 跳转正确性 | Banner 点击 → 站内新闻/外链（take-look.com）；外链打开方式（同页/新标签） |
| 弹窗干扰 | popunder 弹出时机与频率；弹出后主页面可正常返回（用户诉求：广告页要能返回来继续探索）；弹窗关闭按钮可用性 |
| 遮挡测试 | 广告层是否遮挡导航/注册/搜索等关键操作；遮挡时键盘操作与精确点击是否可用 |
| 合规检查 | 广告内容是否含赌博/成人/违法信息（本次已发现博彩广告）；区域合规（日本/欧洲等地区政策） |
| 性能影响 | 广告资源加载是否拖慢首屏；广告 iframe 数量与内存 |

### 5.3 接口测试方案

#### 5.3.1 接口清单与分层

**A. 基础链路（匿名，页面打开即调）**
1. `POST /account-service/login/anonymous/web?appCode=...` —— 匿名登录，校验：必传 appCode、返回 key/value、重复调用是否复用会话
2. `GET /account-service/ee/client/general` —— 客户端配置，校验 IP/region 字段
3. `POST /account-service/ee/ads/activity/get` —— 广告配置，校验：位次结构（INDEX Banner/SidebarDown）、素材 URL 可达性、jumpContent 合法性、displayWeight 权重、空配置处理

**B. 数据查询类（SSR 内联，建议通过页面 HTML 校验 + 服务端直连辅助）**
- 比赛列表/比分/赛程/积分榜/球员/新闻：主链路由 SSR 直接渲染，接口测试可（1）校验页面 SSR 内容一致性（2）在测试环境通过 API 文档补测对应查询接口。

**C. 交互写操作类（需登录态，本次未登录未抓到请求体 —— 列入测试环境补抓项）**
- 预测提交/取消、收藏/取消收藏、关注、反馈提交（content/contactWay/附件）、注册（邮箱/手机验证码）、登录（密码/验证码）、找回密码、银钻领取、商城购买、装扮装备。

#### 5.3.2 接口测试用例设计（示例模板）

| 用例编号 | 接口 | 测试点 | 预期 |
|----------|------|--------|------|
| API-AUTH-001 | 匿名登录 | 正常调用 | 200，返回 key/value，格式正确 |
| API-AUTH-002 | 匿名登录 | 缺 appCode / 非法 appCode | 返回错误码，不产生会话 |
| API-AUTH-003 | 匿名登录 | 重复调用 | 会话复用或新建均符合设计（需确认） |
| API-ADS-001 | 广告配置 | 正常返回 | 各广告位结构与素材 URL 合法 |
| API-ADS-002 | 广告配置 | 素材 URL 可达性 | 全部 200，无 404 死链 |
| API-ADS-003 | 广告配置 | 跳转链接合法性 | 站内路径可访问；外链域白名单 |
| API-LOGIN-001 | 邮箱登录 | 正确/错误密码/不存在账号 | 对应错误码与提示 |
| API-LOGIN-002 | 邮箱登录 | 连续失败锁定策略 | 达到阈值后锁定 |
| API-REG-001 | 注册 | 重复注册/弱密码/验证码错误 | 明确错误码 |
| API-PRED-001 | 预测提交 | 未登录 | 401/引导登录 |
| API-PRED-002 | 预测提交 | 比赛已开始/已截止 | 拒绝提交 |
| API-PRED-003 | 预测提交 | 重复预测/改选 | 状态正确流转 |
| API-FB-001 | 反馈提交 | 内容 0/500/501 字 | 边界校验 |
| API-FB-002 | 反馈提交 | 附件类型/大小限制 | 校验通过/拒绝 |
| API-SEARCH-001 | 搜索 | 空/特殊字符/SQL注入 | 无 500，正常空结果 |

> 安全专项：注册/登录接口防暴力破解、验证码频控、token 有效期、接口参数注入、敏感字段（手机号/邮箱）脱敏、HTTPS 传输。

### 5.4 接口自动化方案

**技术选型（推荐）**：
- **Pytest + requests**（主）：轻量、易维护、断言灵活，与现有 `tests/automation/service/` 体系一致。
- **Postman/Newman**（辅）：快速手工调试 + CI 冒烟集合。
- 数据驱动：YAML/JSON 用例表（入参/预期），Pytest `@pytest.mark.parametrize`。

**工程结构建议**：
```
tests/automation/service/
├── conftest.py            # session 级匿名登录、token 复用
├── config/
│   └── env.yaml           # base_url、appCode、环境切换（test/staging/prod）
├── cases/
│   ├── test_auth.py       # 匿名登录/注册/登录/找回密码
│   ├── test_ads.py        # 广告配置接口
│   ├── test_match.py      # 比赛/比分/赛程（SSR 校验 + 查询接口）
│   ├── test_prediction.py # 预测写操作
│   ├── test_feedback.py   # 反馈提交
│   └── test_search.py     # 搜索
├── data/
│   └── *.json             # 测试数据
└── reports/               # HTML/JSON 报告
```

**关键点**：
1. **会话管理**：conftest 中先调匿名登录拿 key/value，作为公共 header；登录类用例独立账号池。
2. **测试账号**：预置测试账号（邮箱+手机号各一套），注册接口自动化需验证码通道（测试环境走万能码或 mock）。
3. **断言体系**：状态码 + code/status 字段 + data 结构（JSON Schema 校验）+ 关键业务值。
4. **CI 集成**：每日定时回归 + PR 触发；失败自动截图/日志归档（与仓库 CI 门禁对齐）。
5. **环境矩阵**：test/staging/prod 三环境切换，注意 prod 写操作（预测/反馈）用只读或标记数据。

### 5.5 UI 自动化方案

**技术选型**：Playwright（TypeScript 或 Python，建议 TypeScript，与仓库 `tests/automation/ui/` 现状一致）+ Page Object Model + Allure 报告。

**广告弹窗处理策略（本项目的核心难点）**：
1. **网络拦截**：`context.route('**/andallthemise.org/**' / '**/eflewandatnig.org/**' / '**/ukankingwithea.com/**' / '**/bestfungamestoday.com/**' / '**/moonlighthathel.org/**', route.abort())` —— 阻断广告联盟请求，从源头避免 popup。
2. **popup 监听兜底**：`page.on('popup')` 统一关闭广告页并记录（验证广告行为时单独开一条不拦截的用例）。
3. **主框架跳转兜底**：若被整页跳转广告域，`page.goBack()` 返回主站继续执行（与用户探索行为一致）。
4. **定位兜底**：广告遮挡导致点击失败时，用 `force: true` + `elementFromPoint` 校验，或滚动到目标元素。

**工程结构建议**：
```
tests/automation/ui/
├── playwright.config.ts      # 多浏览器/多视口/拦截广告路由全局配置
├── pages/
│   ├── HomePage.ts           # 首页（各区块、Banner）
│   ├── MatchDetailPage.ts    # 比赛详情（Stats/Odds/Schedule/Prediction）
│   ├── AuthModal.ts          # 登录/注册弹窗（EMAIL/PHONE/Google/Apple）
│   ├── UserCenterPage.ts     # /my（银钻/收藏/装扮/设置/反馈）
│   ├── SearchPage.ts         # 搜索
│   ├── LeaguePage.ts / TeamPage.ts / PlayerPage.ts
│   └── NewsPage.ts / TipsPage.ts / FaqPage.ts
├── tests/
│   ├── home.spec.ts
│   ├── match.spec.ts         # 直播/比分/回放
│   ├── auth.spec.ts          # 注册/登录/登出
│   ├── prediction.spec.ts
│   ├── search.spec.ts
│   ├── user-center.spec.ts   # 收藏/反馈/银钻
│   ├── ads.spec.ts           # 广告专项（不拦截，验证弹窗行为与返回）
│   └── i18n.spec.ts          # 9 语言冒烟
├── fixtures/                 # 测试数据（账号、关键词）
└── utils/                    # 广告拦截、日期、截图工具
```

**用例优先级映射（P0 → 自动化优先）**：
1. 首页加载与关键区块可见（M1）
2. 比赛详情：比分/预测/赔率展示 + 未登录预测弹登录（M2/M7）
3. 登录（邮箱+密码）→ /my 菜单齐全 → 收藏一条 → 反馈提交（M5）
4. 搜索："Marseille" → MATCH/TEAM/NEWS 分类结果（M6）
5. 广告专项：验证广告弹窗出现 → 关闭/返回 → 主流程继续（M8）
6. 多语言冒烟：9 语种首页 title 与关键文案（M10）

**稳定性要点**：
- 比赛数据为实时数据，断言用结构存在性而非具体比分；时间用相对断言（今天/未来）。
- 直播流播放断言播放器出现 + 网络请求（hls/m3u8 或视频流请求），不断言播放进度。
- 全量回归建议固定时间窗口（如 UTC 08:00，避开比赛高峰数据变动）；比赛数据敏感用例用筛选条件（如 International Club Friendly）减少变动。

---

## 6. 风险与后续建议

| 风险 | 建议 |
|------|------|
| 赌博/成人广告合规 | 法务评审 + 分区域广告策略验证；测试重点覆盖 |
| 广告弹窗影响自动化稳定性 | 自动化默认拦截广告域，广告专项单独用例 |
| 未登录状态接口覆盖不足 | 测试环境申请测试账号，补齐写操作接口抓包与用例 |
| 比赛数据实时变动导致断言脆弱 | 结构断言 + 时间窗口回归 |
| 镜像域名切换 | 多镜像域名环境矩阵纳入回归（camel1.to/camel2.live 冒烟） |
| `/match-replay/{id}` 路由异常 | 确认为缺陷后跟踪修复并补回归 |

### 6.1 待办后续（已登记，2026-08-14）

| # | 待办项 | 说明 | 状态 |
|---|--------|------|------|
| 1 | 测试环境补抓登录态接口 | 预测提交/收藏/反馈提交的完整请求体，完善接口用例（见最终用例 FINAL-API-008~021） | ⏳ 待执行 |
| 2 | 落地 UI 自动化骨架 | Playwright 工程 + 广告拦截全局配置（见最终用例 §五 AUTO-*） | ⏳ 待执行 |
| 3 | 确认 `/match-replay/{id}` 路由缺陷 | 线上实测详情路由渲染镜像页，确认是否为缺陷并跟踪修复 | ⏳ 待确认 |
| 4 | 赌博广告合规问题 | 线上实测 BC.GAME 博彩广告 + popunder 成人/博彩落地页，需法务评审 | ⏳ 待评审 |
| 5 | 16.0.0 篮球功能线上验证 | 蓝湖 16.0.0 需求（体育项目 TAB/Box Score/交易）上线后按 `体育平台-16.0.0-测试用例.md` 验收 | ⏳ 待 16.0.0 上线 |
| 6 | UGC 功能回归 | UGC 因运营策略线上隐藏，开放后按需求用例回归（最终用例 FINAL-NEWS-008 等） | ⏳ 待开放 |
| 7 | 移动端引导下载 APP 确认 | 原型需求有引导下载，线上移动端未观察到，与产品确认当前版本策略 | ⏳ 待确认 |
| 8 | 体育平台 git 权限（建议#6） | 用于 XMind「diff 抹平 + 脚本自维护」机制；**当前无权限申请入口，外部阻塞挂起**。入口开放后申请只读权限并恢复执行 | ⛔ 挂起（外部阻塞） |

---

## 7. 附录

### 7.1 探索统计

- 访问页面数：18 条核心路由 + 8 类详情页 + 首页全链接分析（641 链接）+ 多语言/移动端
- 捕获 API：5 类核心接口 + 广告联盟 10+ 请求
- 语言版本：9 种（sitemap 统计：en 350 + ar 342 + es 342 + id 342 + pt-BR 341 + pt-PT 341 + tr 341 + bn 73 + hi 73）
- sitemap URL 总数：2545

### 7.2 探索所用关键命令与脚本（可复现）

- Playwright 探索脚本位于 `%TEMP%\cameltv-*.js`（01-首页 / 04-路由批量 / 05-详情 / 06-交互 / 09-技术栈 / 12-广告）
- 视觉复核：GLM-4V（glm-4v-flash）识别截图
- 后续可直接复用脚本接入 CI 或扩展为正式自动化基线

### 7.3 页面路由速查表

| 路由 | 模块 | 说明 |
|------|------|------|
| `/` | M1 | 首页（9 语种前缀） |
| `/football/{slug}/{id}` | M2 | 比赛详情 |
| `/hotmatch` `/match/progressing` | M2 | 热门/进行中比赛 |
| `/match-replay` `/match-replay/{id}` | M2 | 回放列表/（详情=镜像页⚠） |
| `/free-football-live-streaming[/联赛]` | M2 | 免费直播落地页 |
| `/league/{name}` `/r/league/{name}` | M3 | 联赛页/重定向 |
| `/team/{name}/{id}` | M3 | 球队页 |
| `/player/{name}/{id}` | M3 | 球员页 |
| `/head-to-head/{date}-{a}-vs-{b}` | M3 | 对阵页 |
| `/q/news` `/news/detail/{slug}` | M4 | 新闻列表/详情 |
| `/tips` | M4/M7 | 预测内容页 |
| `/worldcup-2026` `/winter-window` | M4 | 专题页 |
| `/search#q=&f=` | M6 | 搜索 |
| `/my` `/my/faq` `/my/feedback` | M5/M9 | 用户中心/FAQ/反馈 |
| `/about-us` `/contact-us` `/terms` `/rss.xml` | M12 | 静态页 |
| `/en /ar /hi /bn /id /es /pt-BR /pt-PT /tr` | M10 | 语言版本 |

---

*报告基于 2026-08-14 线上站点实测。线上环境与配置可能随时变化（广告位、比赛数据、镜像域名），正式测试执行时应以测试/预发环境为准，并建立基线快照。*
