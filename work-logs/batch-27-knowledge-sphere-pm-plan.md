# Batch 27 — PM Plan
> **PM (🟨)** | Date: 2026-07-22 | Updated: 2026-07-22 (v1.3 — 含 configures/附件/全局导航/降级)
> **工时基准**: 原 v1.0 估算 × 1.55（累计 +55%：v1.1 +30% / v1.2 +10% / v1.3 +15%）

## 规格摘要
**原始需求**: 蓝湖文档结构 → 测试平台「项目球」知识图谱 + Wiki 基线方案  
**目标时间**: 5 个 Milestone 分阶段交付（v1.3 新增 M5）

---

## 开发任务

### Phase 1: 数据模型设计（M1：基础设施）

#### [ ] Task 1.1: RequirementModule 模型
**描述**: 新建模块树表，支持模块→页面→功能点层级  
**关键字段**: name, node_type, platform, lanhu_page_id, change_type  
**v1.1 新增**: parent_module_id, source_version, screenshot_urls, has_visual_only_content  
**v1.2 新增**: page_interactions (Text/JSON)  
**涉及文件**:
- `test-platform-v2/backend/app/models/requirement.py` — 新增 RequirementModule
- `test-platform-v2/backend/alembic/versions/` — 迁移脚本

#### [ ] Task 1.2: ReleaseBundle 模型
**描述**: 发布包模型，聚合用户端版本 + 运营后台版本 + 附件 + 版本链  
**关键字段**: client_version, admin_version, status  
**v1.1 新增**: parent_bundle_id, diff_summary  
**v1.3 新增**: global_navigation (Text/JSON)  
**涉及文件**:
- `test-platform-v2/backend/app/models/knowledge.py` — 新增 ReleaseBundle

#### [ ] Task 1.3: ModuleAdminLink 模型
**描述**: 用户端模块↔运营后台模块关联表  
**涉及文件**:
- `test-platform-v2/backend/app/models/knowledge.py` — 新增 ModuleAdminLink

#### [ ] Task 1.4: 现有表扩展
**描述**: RequirementDocument (+platform, +doc_type), KnowledgeSource (+module_id)  
**涉及文件**:
- `test-platform-v2/backend/app/models/requirement.py`
- `test-platform-v2/backend/app/models/knowledge.py`

#### [ ] Task 1.5: 知识图谱实体/关系类型规划
**描述**: 定义所有新增 entity_type 和 relation_type（字符串扩展，无需 DDL）  
**实体类型**: release_bundle, platform, client_module, admin_module, page, changelog_entry, attachment, business_rule 🆕 v1.3  
**关系类型**: belongs_to_version, has_platform, has_module, has_page, links_to_admin, evolves_from, described_by, tested_by 🆕 v1.1, navigates_to 🆕 v1.2, configures 🆕 v1.3

---

### Phase 2: 核心服务（M2：业务逻辑）

#### [ ] Task 2.1: VersionDiffer 引擎 (v1.1)
**描述**: 版本差异分析器，Phase A 规则引擎 + Phase B AI 辅助  
**核心方法**: diff(current_doc, parent_bundle) → VersionDiffResult  
**预估**: 约 300 行  
**涉及文件**:
- `test-platform-v2/backend/app/services/knowledge/version_differ.py`

#### [ ] Task 2.2: ModuleExtractor 模块树提取
**描述**: 从蓝湖证据包提取层级结构（文件夹→模块→页面）  
**预估**: 约 250 行  
**涉及文件**:
- `test-platform-v2/backend/app/services/knowledge/module_extractor.py`

#### [ ] Task 2.3: TestCaseLinker 用例关联器 (v1.1)
**描述**: 自动匹配测试用例到模块/页面  
**策略**: 精确匹配 → 功能点匹配 → API 匹配 → 手动  
**预估**: 约 200 行  
**涉及文件**:
- `test-platform-v2/backend/app/services/knowledge/test_case_linker.py`

#### [ ] Task 2.4: NavigatesToExtractor 交互提取器 (v1.2/v1.3)
**描述**: 四层降级提取页面交互跳转关系  
**降级链**: 蓝湖 HTML DOM 抓取 → AI 多模态 → CV 启发式检测 → 标注 UI  
**预估**: 约 250 行（v1.3 增加 CV fallback）  
**涉及文件**:
- `test-platform-v2/backend/app/services/knowledge/navigates_to_extractor.py`

#### [ ] Task 2.5: GlobalNavClassifier 全局导航分类器 🆕 v1.3
**描述**: 统计页面交互出现率，>80% 阈值自动归类全局导航  
**产出**: ReleaseBundle.global_navigation JSON  
**预估**: 约 100 行  
**涉及文件**:
- `test-platform-v2/backend/app/services/knowledge/global_nav_classifier.py`

#### [ ] Task 2.6: ConfiguresLinker 配置链路关联器 🆕 v1.3
**描述**: 从 dynamic_filter 交互中提取 admin_config_source，建议 configures 关系  
**预估**: 约 120 行  
**涉及文件**:
- `test-platform-v2/backend/app/services/knowledge/configures_linker.py`

#### [ ] Task 2.7: AttachmentContentExtractor 附件内容提取器 🆕 v1.3
**描述**: 下载附件 (.docx/.pdf) → OCR/文本提取 → AI 分析功能点和业务规则  
**产出**: description 增强 + business_rule KnowledgeEntity  
**预估**: 约 200 行  
**涉及文件**:
- `test-platform-v2/backend/app/services/knowledge/attachment_extractor.py`

#### [ ] Task 2.8: Wiki 同步服务
**描述**: 蓝湖结构→Wiki 目录树映射 + 差异对比  
**预估**: 约 200 行  
**涉及文件**:
- `test-platform-v2/backend/app/services/wiki/sync_service.py`

---

### Phase 3: API 层（M3：接口）

#### [ ] Task 3.1: 发布包 CRUD API
**路由**: `/api/v1/release-bundles`  
**端点**: GET list / POST / GET {id} / PUT / DELETE / POST {id}/diff / POST {id}/diff/confirm / POST {id}/links  
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/release_bundle.py`
- `test-platform-v2/backend/app/schemas/release_bundle.py`

#### [ ] Task 3.2: 模块树 API
**路由**: `/api/v1/requirement-modules`  
**端点**: GET list / GET {id}/tree / GET {id}/timeline / GET {id}/screenshots / GET {id}/test-cases / POST {id}/link-test-cases / GET {id}/interactions 🆕 v1.2 / POST {id}/interactions 🆕 v1.2  
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/requirement_module.py`

#### [ ] Task 3.3: 知识图谱层级 API
**路由**: `/api/v1/knowledge/graph`  
**端点**: GET hierarchy / POST auto-build / GET node/{id}/expand / POST evolve  
**查询参数**: show_test_cases 🆕 v1.1, show_navigations 🆕 v1.2, show_configures 🆕 v1.3  
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/knowledge.py` — 扩展路由

#### [ ] Task 3.4: Wiki 基线同步 API
**路由**: `/api/v1/wiki`  
**端点**: POST sync-from-release-bundle / GET release-bundle-structure/{id}  
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/wiki.py`

---

### Phase 4: 前端（M4：UI）

#### [ ] Task 4.1: 版本全景页面
**路由**: `/requirement/panorama`  
**布局**: 左侧版本列表 + 右侧三列（APP/PC/WEB）+ 运营后台关联 + 截图 hover 预览 🆕 v1.1  
**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/` — VersionPanorama

#### [ ] Task 4.2: 版本 Diff 审核 UI (v1.1)
**描述**: 展示 VersionDiffResult，支持逐模块确认/修正/驳回  
**预估**: 约 400 行  
**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/DiffReviewPanel.tsx`

#### [ ] Task 4.3: 知识图谱「项目球」视图
**描述**: 层级图谱（项目→版本→平台→模块→页面→用例叶子节点 🆕 v1.1）  
**图谱边**: 层级边（实线）+ 跨端关联（橙色虚线）+ navigates_to（灰色虚线 🆕 v1.2）+ configures（紫色虚线 🆕 v1.3）+ 全局导航（浅蓝虚线 🆕 v1.3）  
**切换控件**: 显示/隐藏 页面跳转边 | 显示/隐藏 配置链路 | 显示/隐藏 测试用例  
**涉及文件**:
- `test-platform-v2/frontend/src/pages/knowledge/components/GraphTab.tsx`

#### [ ] Task 4.4: 页面跳转关系图 UI 🆕 v1.2/v1.3
**描述**: 版本全景中点击页面节点 → 展示跳转关系图（outgoing/incoming + 交互类型标记）  
**包含**: 全局导航标识（浅蓝标记）+ dynamic_filter 标识（紫色标记）  
**预估**: 约 200 行  
**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/PageInteractionPanel.tsx`

#### [ ] Task 4.5: 交互标注 UI 🆕 v1.3
**描述**: 截图上框选热区 → 下拉选择目标页面 → 选择交互类型 → 保存到 page_interactions  
**适用**: 自动提取全部降级失败时的兜底方案  
**预估**: 约 200 行  
**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/InteractionAnnotator.tsx`

#### [ ] Task 4.6: 模块演化时间线
**描述**: 垂直时间线 + 变更差异高亮 + parent_module_id 链追溯 🆕 v1.1  
**涉及文件**:
- `test-platform-v2/frontend/src/pages/knowledge/components/ModuleTimeline.tsx`

#### [ ] Task 4.7: 知识中心分类布局更新 🆕 v1.2
**描述**: 「项目知识」Tab 只展示 project_knowledge + 项目选择器（未来多项目）  
**「平台研发」Tab**: 展示 Agent Team 日志、PRD、架构设计  
**涉及文件**:
- `test-platform-v2/frontend/src/pages/knowledge/` — Tab 过滤逻辑

#### [ ] Task 4.8: 配置链路面板 🆕 v1.3
**描述**: 模块详情中展示 configures 关系，列出该模块受哪些后台配置项控制  
**预估**: 约 100 行  
**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/ConfiguresPanel.tsx`

---

### Phase 5: 存量治理 + 集成 🆕 v1.3（M5）

#### [ ] Task 5.1: 知识中心存量数据 domain 迁移
**描述**: 自动分类规则 + 人工抽检 + CSV 快照回滚  
**规则**: 来源=Agent Team → platform_development；来源=蓝湖导入 → project_knowledge  
**抽检**: 每类 20 条  
**涉及文件**:
- 迁移脚本（一次性）

#### [ ] Task 5.2: AI 交互识别 POC 验证 🆕 v1.3
**描述**: M1 前验证蓝湖 DOM 抓取 + DeepSeek 多模态的可行性  
**样本**: 5 个页面截图，手工标注 ground truth  
**门槛**: 准确率 ≥50% 继续用 AI；<50% 降级为 CV + 手动为主  
**涉及文件**:
- POC 脚本（不提交到仓库）

---

## 质量要求
- [ ] 数据模型兼容现有 `RequirementDocument` 和 `KnowledgeEntity` 表
- [ ] 新 API 需完整的 Request/Response Schema 设计
- [ ] 前端组件设计需包含 Loading/Empty/Error 三态
- [ ] 图谱支持 ≥200 节点 + navigates_to/configures 边时的性能
- [ ] 无破坏性变更——现有功能全部保留
- [ ] Feature Flag 渐进启用（project_sphere_enabled / module_tree_enabled / wiki_sync_baseline_enabled）
- [ ] v1 基线导入后强制人工逐项审核（C2: 基线完整性）

## 新增组件汇总

| 组件 | 版本 | 类型 | 预估行数 |
|------|------|------|---------|
| VersionDiffer | v1.1 | Backend Service | ~300 |
| TestCaseLinker | v1.1 | Backend Service | ~200 |
| DiffReviewPanel | v1.1 | Frontend UI | ~400 |
| NavigatesToExtractor | v1.2/v1.3 | Backend Service | ~250 |
| PageInteractionPanel | v1.2 | Frontend UI | ~200 |
| GlobalNavClassifier | v1.3 | Backend Service | ~100 |
| ConfiguresLinker | v1.3 | Backend Service | ~120 |
| AttachmentContentExtractor | v1.3 | Backend Service | ~200 |
| InteractionAnnotator | v1.3 | Frontend UI | ~200 |
| ConfiguresPanel | v1.3 | Frontend UI | ~100 |
| **总计** | | | **~2070** |
