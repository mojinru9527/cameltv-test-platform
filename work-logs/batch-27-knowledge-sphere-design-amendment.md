# Batch 27 — Design Amendment
> **Date**: 2026-07-22 | **v1.1 Trigger**: 用户对 v1.0 设计方案的三个关注点反馈
> **v1.2 Trigger**: 用户对 v1.1 设计的三个歧义点澄清
> **v1.3 Trigger**: QA v1.2 审查发现 + 用户确认优化方向（configures/附件/全局导航/降级）
> **影响范围**: PRD / Dev / PM / Design 四份工件

---

## 修订总览

| # | 关注点 | 严重级 | 影响范围 | 修订内容 |
|---|--------|--------|---------|---------|
| # | 关注点 | 严重级 | 影响范围 | 修订内容 |
|---|--------|--------|---------|---------|
| 🔴 | 增量版本导入 (v2+ 只取差异) | **核心逻辑变更** | 数据模型 + 导入流程 + API | ReleaseBundle 版本链、VersionDiffer 引擎、增量模块提取 |
| 🟠 | 保留页面截图 (交互在图片上) | **数据完整性** | 数据模型 + 导入流程 + UI | RequirementModule.screenshot_urls + 全景视图缩略图 |
| 🟢 | 测试用例图谱关联 | **图谱扩展** | 关系模型 + auto-build + UI | tested_by 关系 + 用例叶子节点 + 三色区分 |

### v1.2 修订项

| # | 关注点 | 严重级 | 影响范围 | 修订内容 |
|---|--------|--------|---------|---------|
| 🔵 | 页面交互跳转链路 | **数据模型 + 用例扩展** | RequirementModule + 图谱关系 + AI 用例生成 | page_interactions JSON + navigates_to 关系 + 导航测试用例 |
| 🟡 | 说明附件稀疏性 | **设计修正** | 数据模型注释 + 导入流程 | 附件 node_type 可选，缺失不报错 |
| ⚪ | 知识中心分类重组 | **内容组织** | 知识中心架构 | 项目知识=业务知识, 平台研发=研发资料 |

### v1.3 修订项 🆕

| # | 关注点 | 严重级 | 影响范围 | 修订内容 |
|---|--------|--------|---------|---------|
| 🟣 | interaction 枚举补全 + 全局导航 | **数据模型增强** | RequirementModule + ReleaseBundle | dynamic_filter 类型 + global_navigation 字段 + >80% 自动分类 |
| 🟤 | configures 跨系统配置链路 | **图谱关系新增** | KnowledgeRelation | configures 关系 + 后台配置变更测试用例 |
| 🟦 | 附件内容结构化 | **导入流程增强** | 导入流程 + KnowledgeEntity | AttachmentContentExtractor + business_rule 实体 |
| ⬛ | 交互提取四层降级 | **鲁棒性增强** | 提取策略 | DOM → AI → CV → 标注 UI |

---

## 🔴 修订 1: 增量版本导入

### 问题

v1.0 设计假设每个版本独立导入。用户明确指出：**v2+ 提交时不需要采集之前版本的重复内容，功能拆分也不需要考虑旧有已完成的功能。只需保留单次版本需要更新的内容。**

但有一个重要条件：**如果本次更新涉及旧有模块，旧有模块的功能需要作为上下文考虑进去。**

### 解决方案

#### 数据模型变更

**ReleaseBundle 新增字段**:
```python
parent_bundle_id: int | None   # 父版本 ReleaseBundle ID，形成版本链
diff_summary: str              # JSON，记录与父版本的差异摘要
```

**RequirementModule 新增字段**:
```python
parent_module_id: int | None   # 同模块在父版本中的 ID，形成跨版本演化链
source_version: str            # 该节点首次引入的版本号
```

#### 新增核心组件: `VersionDiffer`

```
Phase A — 规则引擎:
  - 文件夹名对比 → 识别同名模块 (modified/unchanged)
  - 父版本有/当前无 → deleted
  - 当前有/父版本无 → new
  - 页面名逐项对比 → 新增/删除/同名

Phase B — AI 辅助 (规则无法覆盖时):
  - OCR 内容相似度分析
  - 模块重命名检测 (如 "资讯模块" → "资讯管理")
  - 输出置信度
```

#### 导入流程变更

```
v1 (基线):
  全量导入 → 提取所有模块/页面 → 全部 change_type="new"

v2+ (增量):
  选择父版本 → 版本 Diff → 人工审核 → 仅提取变更模块 → 仅对变更模块拆分+生成用例

模块分类处理:
  new:          全量提取 + 拆分 + 用例生成
  modified:     提取变更页面 + 拆分变更功能点 + 用例生成 (考虑父模块上下文)
  deleted:      标记为删除，不生成用例
  unchanged:    跳过 (不提取、不拆分、不生成用例)
```

#### 关键设计决策

| 决策 | 理由 |
|------|------|
| Diff 结果需人工审核 | AI 在模块重命名/合并场景下可能误判 |
| 未变更模块不生成用例 | 旧版本已有用例，无需重复；回归测试从父版本用例筛选 |
| 修改模块保留 parent_module_id | 前端可展示完整模块面貌（父版本 + 本版本变更） |
| v1 基线必须完整 | 增量导入正确性完全依赖基线的完整性 |

---

## 🟠 修订 2: 保留页面截图

### 问题

用户明确指出：**"有一些交互是在图片上显示的"**。v1.0 设计侧重 OCR 文本提取，没有把蓝湖证据包采集的截图关联到模块/页面。

### 解决方案

#### 数据模型变更

**RequirementModule 新增字段**:
```python
screenshot_urls: str             # JSON 数组，存储截图 URL 列表
has_visual_only_content: bool    # 是否含仅截图可见的交互
```

#### 导入流程增强

证据包导入时自动从 `LanhuEvidencePage` 将截图 URL 关联到对应 `RequirementModule`：

```
LanhuEvidencePage.screenshot_url → RequirementModule.screenshot_urls
                                   (通过 lanhu_page_id 匹配)
```

#### UI 展示

- 版本全景视图：模块卡片 hover 时展示缩略图
- 页面详情：截图轮播查看器
- `has_visual_only_content=True` 的页面显示 "📸 含视觉交互" 标记

---

## 🟢 修订 3: 测试用例图谱关联

### 问题

用户明确指出：**"功能用例、接口用例、自动化用例要在图谱上去和对应的模块去关联，因为这些也是属于对应模块的数据。"**

### 解决方案

#### 关系模型

利用现有 `KnowledgeRelation` 表（`relation_type` 是字符串，无需 DDL），新增关系类型：

```
Module/Page ──tested_by──→ TestCase
```

用例按类型在项目球中显示为模块/页面的叶子节点：

```
Module: 资讯
  ├── Page: 资讯列表
  │     ├── 🟢 TC-ZX-001 (功能用例)
  │     ├── 🔵 TC-API-ZX-010 (接口用例)
  │     └── 🟠 TC-AUTO-ZX-101 (自动化用例)
  └── Page: 资讯详情
        └── 🟢 TC-ZX-005 (功能用例)
```

#### 视觉区分

| 用例类型 | 颜色 | 图标 |
|---------|------|------|
| 功能用例 (functional) | 绿色 #10b981 | ClipboardCheck |
| 接口用例 (api) | 蓝色 #3b82f6 | Server |
| 自动化用例 (automation) | 橙色 #f97316 | Play |

#### 自动关联策略

```python
优先级1: 精确匹配 — 用例名称含模块名
优先级2: 功能点匹配 — 用例的 function_point 属于该模块
优先级3: API 匹配 — 接口用例的 endpoint 关联到模块页面
优先级4: 手动关联 — 用户拖拽建立关联
```

#### auto-build 增强

在 `POST /api/v1/knowledge/graph/auto-build` 流程中追加 Step 5：
1. 对每个新增/修改的模块/页面
2. 查询已有用例（模块名+功能点匹配）
3. 查询新生成用例（本版本刚由 AI 生成）
4. 建立 `tested_by` 关系
5. 用例节点挂在对应页面下

---

## 对实施路线的影响

| 阶段 | 原计划 | 修订后 |
|------|--------|--------|
| M1: 数据模型 | 3 表 + 2 字段扩展 | 3 表 + **5 字段扩展** (新增 parent_bundle_id, diff_summary, parent_module_id, source_version, screenshot_urls, has_visual_only_content) |
| M2: 图谱视图 | 层级图谱 | 层级图谱 + **用例叶子节点** |
| M3: Wiki 同步 | 基线同步 | 基线同步 (不变) |
| M4: 演化追踪 | 模块时间线 | 模块时间线 + **parent_module_id 链追溯** |

新增独立组件：
- `VersionDiffer` 服务 (约 300 行)
- `TestCaseLinker` 服务 (约 200 行)
- 版本 Diff 审核 UI (约 400 行)

**工时影响**：原估算增加约 30%（主要是 VersionDiffer 引擎和 Diff 审核 UI）

---

## v1.2 修订详情 (2026-07-22)

### 触发背景

用户在审核 v1.1 修订后提出三个歧义澄清：

1. **说明附件不是每个版本都有**——仅少数大模块（广告位系统、银钻系统、UGC 功能概述、付费活动、骆驼币及绿钻）有附件，其他模块没有。需要 AI 整合完整版本需求（用户端+运营端），附件为可选。

2. **之前说的"图片"本质是交互跳转关系**——蓝湖原型中可点击区域（搜索图标→搜索页、资讯卡片→详情页、底部导航Tab→各页面）构成页面跳转链路。这些交互关系需要在：(a) 需求提取时保留 (b) 知识图谱中展示 (c) AI 测试用例生成时覆盖。

3. **知识中心「项目知识」内容归属错误**——当前混合了平台研发内容。应拆分为：项目知识（体育平台业务知识）和平台研发（Agent Team 开发资料）。

---

### 🔵 修订 4: 页面交互跳转链路

#### 问题

蓝湖原型中的交互跳转关系在文本导出时完全丢失。用户举了具体例子：
- 资讯列表页：点击搜索→搜索页、点击分类→分类筛选页、点击资讯→详情页
- 底部导航栏：首页↔我的↔预测 Tab 切换

这些跳转关系也是需求的一部分，对测试（尤其是导航流程测试）至关重要。

#### 数据模型变更

**RequirementModule 新增字段**:
```python
page_interactions: str   # JSON 数组 (node_type="page" 时有效)
# 例:
# [{"trigger": "点击搜索图标", "target_page": "搜索页",
#   "interaction_type": "navigation", "source_element": "顶部搜索栏"}]
```

**KnowledgeRelation 新增类型**:
```
navigates_to: Page → Page (弱关联，虚线边)
```

#### 提取策略

```
优先级 1 — 蓝湖 HTML DOM 抓取: 解析原型中的 page-link/hotspot 元数据（Axure HTML DOM）
优先级 2 — AI 多模态分析: DeepSeek 分析蓝湖页面截图 → 识别交互元素 + 推断目标页面
优先级 3 — 手动补充: 用户在版本全景视图中拖拽建立
```

#### 图谱可视化

- `navigates_to` 边：虚线 + 浅灰色 + 方向箭头
- hover 显示 trigger 文本
- 默认隐藏（图谱中可切换显示），避免视觉过密

#### AI 测试用例扩展

```
原有用例生成 prompt 增强：
"该页面存在以下交互跳转关系：...
请针对交互链路生成导航测试用例：
- 跳转目标是否正确
- 返回是否正常
- 边界（空搜索词点击搜索、Tab 切换状态保持等）"
```

新增测试用例类型：**导航链路完整性测试**（遍历所有 `navigates_to` 边）

#### 对实施路线的影响

| 组件 | 增量 |
|------|------|
| `RequirementModule.page_interactions` 字段 | 1 个 Text 字段 |
| `NavigatesToExtractor` 服务 | 约 150 行 |
| 导航用例生成 prompt 模板 | 约 80 行 |
| 图谱 navigates_to 边渲染 | 约 100 行 |
| 页面跳转图 UI | 约 200 行 |
| **工时影响** | **+10%** |

---

### 🟡 修订 5: 说明附件稀疏性

#### 问题

v1.1 设计中 `node_type="attachment"` 的模块似乎被隐含假设为每个版本都有。实际情况是仅少数模块有说明附件。

#### 修正

- 导入逻辑：附件模块不存在时不报错、不阻塞
- 版本全景视图：有附件的模块显示附件入口，没有则留空
- 完整版本需求 = 用户端模块 + 运营后台模块 + 可用的说明附件（可选）
- 无需代码变更，仅修正设计假设

---

### ⚪ 修订 6: 知识中心内容分类重组

#### 问题

当前「项目知识」Tab 混合了：
- 体育平台业务知识（需求、模块、用例）
- 测试平台研发资料（Agent Team 日志、PRD 文档）

#### 修正

| Tab | 内容 | knowledge_domain |
|-----|------|-----------------|
| 项目知识 | 体育平台业务知识 | `project_knowledge` |
| 平台研发 | 测试平台自身研发资料 | `platform_development` |
| 检索 | 跨域搜索 | 不限 |

#### 多业务平台扩展

```
项目知识
  ├── 体育平台 (project_id=1)
  ├── 直播平台 (project_id=2)  ← 未来
  └── 社区平台 (project_id=3)  ← 未来
```

通过项目选择器切换，按 `project_id` 隔离。

#### 实施

- 存量数据：审查 `knowledge_domain` 字段，修正归属
- 增量数据：Agent Team 日志 → `platform_development`；业务知识导入 → `project_knowledge`
- 前端：两个 Tab 按 `knowledge_domain` 过滤
- **无 DDL 变更、无 API 变更**

---

## 🟣 修订 7: interaction 枚举补全 + 全局导航 (v1.3)

### 问题

v1.2 的 `interaction_type` 枚举只有 4 种类型，无法覆盖：
- 目标由运营后台配置决定的动态跳转（如"资讯分类Tab"显示什么由后台配置）
- 全局导航（如底部Tab栏在几乎所有页面都存在，不应逐页存储）

### 解决方案

**新增 interaction_type**:
- `dynamic_filter`: 目标内容由运营后台配置决定，非固定页面。增加 `admin_config_source` 字段记录后台配置项
- `global_navigation`: 全局导航项，存储在 ReleaseBundle 而非逐页存储

**自动分类规则**: 同一 (trigger, target_page) 出现在 >80% 页面中 → 自动归类为 global_navigation。

**ReleaseBundle 新增字段**: `global_navigation` (Text/JSON)

---

## 🟤 修订 8: configures 跨系统配置链路 (v1.3)

### 问题

用户端功能的展示内容往往由运营后台配置决定。例如资讯分类Tab、推荐内容、礼物列表等。这种"配置→生效"关系没有被建模，测试时无法评估配置变更的影响面。

### 解决方案

**新增关系类型**: `configures` — client_module → admin_module

**与 links_to_admin 区分**: links_to_admin = 功能对应（模块级）；configures = 配置控制（运行时行为级）

**提取策略**: AI 语义分析 page_interactions 中的 `dynamic_filter` 条目 → 自动建议 configures 关系

**测试扩展**: 生成配置变更影响测试用例（改后台配置→验证用户端展示同步更新）

---

## 🟦 修订 9: 附件内容结构化 (v1.3)

### 问题

说明附件（.docx/.pdf）内部包含功能点和业务规则，但当前只作为二进制挂载。

### 解决方案

**新增组件**: `AttachmentContentExtractor` 服务
- 下载附件 → OCR/文本提取 → AI 分析 → 提取功能点+业务规则
- 功能点注入模块 description/metadata_json
- 业务规则创建 KnowledgeEntity (entity_type="business_rule")

---

## ⬛ 修订 10: 交互提取四层降级 (v1.3)

### 问题

v1.2 的提取策略只有 AI 截图分析 + 蓝湖链接解析两个路径。如果都失败，功能完全空白。

### 解决方案

四层降级策略：
- P1: 蓝湖原型 HTML DOM 抓取（Axure HTML 的 `<a>` / hotspot 标记）
- P2: AI 多模态截图分析
- P3: CV 启发式检测（OpenCV 检测常见 UI 模式 + OCR）
- P4: 手动截图标注 UI（兜底）

---

### 对实施路线的累计影响

| 版本 | 新增组件 | 工时影响 |
|------|---------|---------|
| v1.1 | VersionDiffer + TestCaseLinker + Diff UI | +30% |
| v1.2 | NavigatesToExtractor + 跳转图 UI + 导航用例模板 | +10% |
| v1.3 | GlobalNavClassifier + ConfiguresLinker + AttachmentExtractor + CV Fallback + 标注 UI | +15% |
| **累计** | | **+55%** |

### 最终字段汇总

| 表 | v1.0 字段 | v1.1 新增 | v1.2 新增 | v1.3 新增 | 合计 |
|----|----------|----------|----------|----------|------|
| `RequirementModule` | 10 | 4 (parent_module_id, source_version, screenshot_urls, has_visual_only_content) | 1 (page_interactions) | — | **15** |
| `ReleaseBundle` | 10 | 2 (parent_bundle_id, diff_summary) | — | 1 (global_navigation) | **13** |
| `RequirementDocument` | 现有 | 2 (platform, doc_type) | — | — | **+2** |
| `KnowledgeSource` | 现有 | 1 (module_id) | — | — | **+1** |

### 新增关系类型汇总

| 关系类型 | 版本 | 方向 |
|---------|------|------|
| `belongs_to_version` | v1.0 | Entity → ReleaseBundle |
| `has_platform` | v1.0 | ReleaseBundle → Platform |
| `has_module` | v1.0 | Platform → Module |
| `has_page` | v1.0 | Module → Page |
| `links_to_admin` | v1.0 | client_module → admin_module |
| `evolves_from` | v1.0 | Module(v2) → Module(v1) |
| `described_by` | v1.0 | Module → Attachment |
| `tested_by` | v1.1 | Module/Page → TestCase |
| `navigates_to` | v1.2 | Page → Page |
| `configures` | v1.3 | client_module → admin_module |

## 不修改的部分

以下 v1.0 设计不受此修订影响：
- `ModuleAdminLink` 跨端关联模型 ✅
- 蓝湖→Wiki 同步基线机制 ✅
- 知识图谱 entity_type/relation_type 字符串扩展策略 ✅
- Feature Flag 渐进启用策略 ✅
- 兼容性保证（零破坏性变更）✅
