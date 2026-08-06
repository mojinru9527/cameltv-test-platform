# Batch 102 — Design Spec（体育平台功能模块梳理）

> **Design (🎨)** | Date: 2026-08-06 | Status: Review

## 1. 需求数据流（复用平台现有能力，无新接口）

```text
upload(multipart md)
  → POST /requirements/upload            # title=文档标题, file=蓝湖导出的 md
  → POST /requirements/{id}/extract      # AI 提取模块/功能点
  → GET  /requirements/{id}/extraction   # 拉取提取结果
  → POST /requirements/{id}/extraction/confirm   # action=confirm, modules=[提取结果]
  → POST /requirements/{id}/generate     # {use_extraction: true} → 功能用例
  → GET  /requirements/{id}/cases        # 用例清单
  → POST /requirements/{id}/import       # {indices:[...], create_plan:true}
```

## 2. 功能用例域结构（`/test-cases/domains`）

| 域 | 模块（示例，最终以提取结果+生产勘察为准） |
----|------|
| 体育平台-用户端 | 首页/赛事详情/直播间/我的/UGC/资讯/搜索/PC 端 等 |
| 体育平台-运营后台 | 财务/赛事预测/UGC/内容管理/商城/广告/装扮/消息/用户/系统 等 |
| 体育平台-公共 | 登录注册/权限/通用组件（跨端） |

用例字段：title / case_type=manual / priority / domain / module / preconditions / steps(JSON 数组字符串) / expected_result / client_scope(["app","pc","web"])。

## 3. 知识中心结构（`/knowledge`）

- `capture`（灵感捕获）或 `sources`：以「体育平台-功能逻辑」为知识源，内容 = 功能地图章节（模块作用/运营后台使用/konfi 关联）。
- `graph/extract`：实体 = 功能模块/页面/后台操作/konfi 配置；关系 = `uses` / `managed_by` / `configured_by` / `links_to`。
- 检索入口 `/knowledge/search`，供后续用例生成与评审引用。

## 4. 模块关联（`/requirement-modules`）

- 模块树：bundle 以「体育平台功能地图」为发布包，模块 = 用户端/运营后台功能模块。
- 全局导航：`classify-global-nav` 识别用户端主导航（首页/赛事/直播/我的…）。
- 跨系统关联：`admin-links` 建立 用户端模块 ↔ 运营后台管理页 ↔ konfi 配置项 的映射（如：用户端「直播间」→ 运营后台「赛事视频流/推流主播」→ konfi 推流配置）。
- 配置关联：`suggest-configures` / `confirm-configures` 记录 konfi 配置项与功能模块的关系。

## 5. 功能地图文档结构（`docs/体育平台-功能模块地图.md`）

每模块一节：需求页来源（蓝湖页名）→ 生产页面模块（www.camel1.tv 实际入口）→ 平台用例域/模块 → 运营后台管理页 → konfi 配置关联 → 状态（已对照/待补）。

## 6. 脚本接口（`scripts/sports/import-sports-requirements.py`）

```text
--backend-url http://127.0.0.1:8048/api/v1 | https://test-platform.up.railway.app/api/v1
--username sportsadmin --password <env TP_ADMIN_PASSWORD>
--docs-dir 产品需求/
--steps upload|extract|generate|import|knowledge|modules|all
--dry-run
```

每次执行输出证据 JSON 到 `test-platform-v2/work-logs/evidence/batch-102/`。

## 7. 平台使用障碍登记

过程中发现的「使用少/有障碍」项（如批量操作缺失、导出格式限制、AI 提取质量、导航入口深等）统一登记 `docs/改进任务backlog.md`「Batch 102」节，标注影响与建议迭代项。
