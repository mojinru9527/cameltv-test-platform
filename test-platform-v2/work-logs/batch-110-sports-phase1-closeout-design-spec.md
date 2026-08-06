# Batch 110 — Design Spec（体育平台第一期收口）

> **Design (🎨)** | Date: 2026-08-06 | Status: Review

## 0. 技术体系确认

本期以「脚本工具 + 平台既有数据链路 + 文档」为主，**无新前端页面/新 API 路由**（反向回填口径）：

- 数据链路复用平台既有 API：需求/用例/知识中心/RAG/Wiki（wiki.py）/接口用例（apitest + 直连库回填）/发布包。
- 生产执行沿用 batch-102/103 已验证模式：生产 API（sportsadmin + X-Project-Id=1）+ 直连生产库同步
  （凭证经 `TP_ADMIN_PASSWORD` / `TP_DATABASE_URL` 注入，不回显入库）。
- 生产配置变更：`WIKI_ENABLED=true`、`WIKI_DIFF_ENABLED=true`、`WIKI_AUTO_INGEST_ENABLED=true`
  （Railway 环境变量；安全默认 OFF 不动，batch-109 模式由用户配置或登记 C 条件）。

## 1. 脚本接口设计（新增/扩展）

### 1.1 `scripts/sports/walkthrough-sports-production.mjs`（扩展）

```text
PROD_BASE_URL=https://www.camel1.tv MAX_PAGES=40 CAPTURE_XHR=true
  → 自动发现全路由（首页导航/链接递归 2 层 + 显式路由模式）
  → 每页: DOM 文本/链接/按钮/标题 + 截图（1440x900）
  → XHR 捕获: page.on('request'/'response') → 同源 api.cameltv.live 请求/响应 JSON
  → 输出: production-pages.json / screenshots/*.png / xhr-samples.json
```

### 1.2 `scripts/sports/capture-xhr-samples.mjs`（新增）

```text
node scripts/sports/capture-xhr-samples.mjs --base https://www.camel1.tv --pages home,news,my,search,match-replay,worldcup
  → 访问指定路由并触发翻页/筛选/搜索等交互，捕获 XHR（request post_data + response json）
  → 去重/清洗（排除信标/广告域；仅保留 api.cameltv.live 同源）
  → 输出 evidence/batch-110/xhr-samples.json（≥20 接口，含 method/url/body/response/页面归属）
```

### 1.3 `scripts/sports/generate-interface-cases.py`（扩展 TARGETS）

```text
TARGETS 由 xhr-samples.json 提炼（≥20）：每个含 service/path/real{method,url,body,response_sample,source}。
生成: schema 有字段 → generate_cases_from_endpoint；schema 空 → generate_cases_from_real_sample。
断言: envelope/code/data 结构 + 关键字段非空 + 列表长度边界（响应结构做断言，C103-3）。
落库: 直连生产库 INSERT test_case（api_method/api_endpoint/api_headers/api_body/api_assertions/
      case_design_method/positive_negative/test_data_note），证据写 interface-cases-summary.json。
```

### 1.4 `scripts/sports/execute-interface-cases.py`（新增）

```text
读取接口用例（api_endpoint 前缀过滤）→ 按真实样本参数组包 → 生产 API 实跑
→ 响应结构断言（envelope/data/records 长度/关键字段）→ 回填 last_response_json/last_run_status
→ 输出 execution-summary.json（通过/失败/断言明细）
```

### 1.5 `scripts/sports/mark-p0-cases.py`（新增）

```text
按功能域/模块 + 关键用户路径清单（登录注册/首页/赛事详情/直播间/资讯/搜索/我的/充值支付/回放/世界杯）
将对应功能用例 priority 更新为 P0（直连生产库 UPDATE test_case SET priority='P0' WHERE ...）
→ 输出 p0-cases-summary.json（P0 清单，供 UI 自动化映射）
```

### 1.6 `scripts/sports/build-wiki-baseline.py`（新增，C102-3 直建能力的落地）

```text
输入: 需求文档提取结果（requirements/{id}/extraction modules）+ 发布包
1. 建 ReleaseBundle（若不存在；status=active，client 14.1.0 / admin 8.2.0）
2. 建 RequirementModule 树：platform(APP/PC/WEB/ADMIN) → module → page → function_point
   （name/node_type/platform/parent_module_id/description/sort_order/change_type）
3. 建 ModuleAdminLink（用户端模块 ↔ 运营后台模块 ↔ konfi，relation_type=links_to_admin/configures）
4. POST /wiki/sync/bundle/{id}（create_wiki_pages=true）→ raw sources
5. POST /wiki/ingest-jobs → 编译 WikiPage
6. POST /wiki/pages/{id}/approve（draft→approved）
7. POST /wiki/diff/tasks（RAG vs Wiki；13.0 vs 14.0；14.0 vs 14.1.0 等 ≥3 组）
→ 输出 wiki-baseline-summary.json（raw_sources/pages/diff task/items）
```

### 1.7 `scripts/sports/knowledge-sync.py`（扩展）

```text
新增 SOURCES：4 份需求文档全文摘要/功能地图 v2/接口规范三件（tests/test-case-standards）。
优先走标准 /knowledge/capture（batch-108 修复后）；若仍 409/503 → 按 ingest 语义直连补入并登记。
图谱：按功能地图 v2 新增实体/关系（消息/用户管理/系统管理/支付充值等）。
```

## 2. 用例/知识结构

| 资产 | 结构 | 落点 |
|------|------|------|
| 功能用例 | domain=体育平台-用户端/运营后台；module=功能模块；priority=P0/P1/P2（P0≥30 条） | test_case 表 + 平台用例库 |
| 接口用例 | case_type=api；api_method/api_endpoint/api_body/api_assertions/last_response_json/last_run_status | test_case 表 + 平台「接口数据」Tab |
| RAG 知识源 | source_type=capture；title/content 按功能地图章节 + 需求文档全文 + 接口规范 | knowledge_source/knowledge_chunk |
| 图谱 | entity=模块/页面/后台操作/konfi 配置；relation=managed_by/configures/contains | knowledge_entity/knowledge_relation |
| Wiki 基线 | raw_source（source_type=requirement，immutable_version=bundle:{id}:module:{id}）→ WikiPage → 差异任务 | wiki_raw_source/wiki_page/wiki_diff_task/item |
| 模块树 | RequirementModule（platform→module→page→function_point）+ ModuleAdminLink | requirement_module/module_admin_link |

## 3. 平台障碍登记口径

本期新增障碍候选（登记 SPORT-INT + C110）：

| # | 障碍 | 影响 | 建议 |
|---|------|------|------|
| B6 | 生产 wiki 未启用（WIKI_ENABLED 默认 OFF，Railway 无变量） | 无法走标准 wiki 链路 | Railway 配置启用或登记用户操作 |
| B7 | 需求模块树无直建能力（仍依赖蓝湖证据包） | wiki 基线需脚本直建 | 落地 build-wiki-baseline 后仍建议平台 API 支持（C102-3） |
| B8 | 接口用例批量执行无 UI（单条执行可用） | 批量回填依赖脚本 | 平台「批量执行/结果回填」迭代 |
| B9 | 知识 capture 大文档超时风险（C102-1 未闭环） | 大文档入库慢 | 异步化/分块（C102-1 跟踪） |

## 4. UI 自动化 P0 映射（设计）

| P0 功能用例（域-模块） | UI spec 检查点（生产只读） |
|------------------------|------------------------------|
| 用户端-首页-直播列表加载 | 首页 Live Matches 区块渲染 + 请求命中 api.cameltv.live + 无控制台错误 |
| 用户端-赛事详情-页面元素 | /football/{id} 打开，标题/比分/标签渲染 |
| 用户端-直播间-页面元素 | /football/.../live/ 视频容器存在（不做播放断言，只读） |
| 用户端-资讯-列表与详情 | /q/news 列表 + 详情页标题一致 |
| 用户端-搜索-热门词与结果 | /search 热门词展示 + 搜索跳转 |
| 用户端-我的-页面元素 | /my 登录引导/资产区块渲染 |
| 用户端-回放-列表 | /match-replay 列表渲染 |
| 用户端-世界杯-专题 | /worldcup-2026 Match Center/Schedule 渲染 |

守卫：guardProductionRequests（仅 GET/HEAD + 授权只读会话；POST 信标/广告域如实记录，不静默放行，C101-1 口径）。

## 5. 设计走查与签核

本期无前端 UI 变更；脚本/文档域走查重点为「只读守卫、凭据注入、证据落盘、双 404 约定」。

结论：通过（待 Dev 按切片落地后 QA 复核）。
