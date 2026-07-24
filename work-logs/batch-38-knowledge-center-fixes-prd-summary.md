# Batch 38 — 知识中心交互修复与功能补全 PRD Summary
> **Product (🟦)** | Date: 2026-07-23 | Status: Draft

## 1. 问题陈述

知识中心上线后，用户在实际使用中发现 8 个问题：3 个前端交互缺陷（检索无响应、弹窗变形、按钮状态不更新）、1 个数据归属错误（项目知识/平台研发数据混淆）、3 个功能门禁误关闭（RAG/图谱/蓝湖采集全部返回 503）、1 个审核效率缺陷（缺少批量操作）。这些问题导致知识中心核心链路不可用或操作效率低下。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 检索结果可点击查看 | 0%（无响应） | 100% 有点击弹窗 | 即刻 |
| 弹窗内容正常显示 | 大内容变形 | 任意长度正常渲染 | 即刻 |
| 验证按钮状态反馈 | 无状态变化 | 验证后按钮立即变绿/已验 | 即刻 |
| RAG 向量回填可用 | 503 | 200 OK | 即刻 |
| 知识图谱提取可用 | 503 | 200 OK | 即刻 |
| 蓝湖证据采集可用 | 503 | 200 OK | 即刻 |
| 批量审核效率 | 逐条操作 | 全选+批量通过 | 即刻 |

## 3. 非目标（本次不做）

- **不新增 LLM 调用能力**：启用 RAG/图谱/蓝湖只是打开已有实现的门禁开关，不新增 AI 能力
- **不修改数据模型/Schema**：不涉及 Alembic 迁移
- **不修改后端审核逻辑**：批量审核在前端循环调用现有单条 API，后端无需变更
- **不新增测试用例**：QA 阶段手动验证即可

## 4. 用户故事 + 验收标准

### US-1: 项目知识归属清晰化
As a 测试工程师, I want 项目知识只显示测试项目的需求/用例/接口，平台研发类数据自动归类到平台研发，so that 我能快速区分项目业务知识和平台技术知识。

**验收**：
- Given 知识中心已有数据（Agent Team 批次工件等平台研发产物），When 我打开"平台研发"标签，Then 这些数据出现在平台研发分区中
- Given 知识中心已有数据，When 我打开"项目知识"标签，Then 只显示该项目下的需求、用例、接口等业务知识
- Given 现有数据 knowledge_domain 字段未正确设置，When 执行迁移，Then 平台研发类数据 knowledge_domain='platform'，项目知识类数据 knowledge_domain='project'

### US-2: 检索结果可点击查看
As a 测试工程师, I want 检索结果卡片可点击并弹窗显示完整内容，so that 我能查看搜索到的知识条目详情。

**验收**：
- Given 我在检索框输入关键字并搜索，When 点击任意搜索结果卡片，Then 弹出对话框显示该词条的完整内容（标题、类型、来源、内容正文）
- Given 弹窗已打开，When 我点击关闭或遮罩，Then 弹窗关闭

### US-3: 知识源弹窗适配长内容
As a 测试工程师, I want 知识源详情弹窗在内容很长时仍能正常显示，so that 我不会因为弹窗变形而无法阅读完整内容。

**验收**：
- Given 某个知识源的原始内容/切片内容超过 5000 字，When 我点击查看该知识源，Then 弹窗使用更大的尺寸（如 max-w-7xl）且内容区域可滚动，布局不变形
- Given 弹窗中的 `<pre>` 块包含长 URL/长单词，When 内容超出容器宽度，Then 正确换行不溢出

### US-4: 验证按钮状态反馈
As a 测试工程师, I want 点击"已验证"按钮后按钮状态立即变更，so that 我知道该知识源已被验证无需重复操作。

**验收**：
- Given 知识源列表中某条记录未验证，When 我点击验证按钮，Then 按钮变为绿色已验状态（填充图标），last_verified_at 显示"今天"
- Given 某条记录已验证，When 我再次查看该记录，Then 验证按钮保持已验状态

### US-5: RAG 向量回填可用
As a 测试工程师, I want 检索页的"向量回填"按钮能正常触发回填，so that 存量切片能补齐向量以支持语义搜索。

**验收**：
- Given rag_enabled=True，When 我点击"向量回填"按钮，Then 接口返回 200 并显示回填结果（总数/已嵌入/跳过）
- Given rag_enabled=False，When 我调用 /api/v1/knowledge/reembed，Then 返回 503（不再出现——默认启用）

### US-6: 批量审核按钮
As a 审核人员, I want 在需要人工审核的模块中一键批量审核，so that 我不需要逐条点击提高审核效率。

**验收**：
- Given AI 审核台中有多条待审核（pending）产物，When 我勾选其中若干条，Then 出现"批量采纳"和"批量驳回"按钮
- Given 我勾选了待审核条目，When 我点击"批量采纳"，Then 所有选中条目状态变为 approved
- Given 全选 checkbox，When 我勾选全选，Then 当前页所有可审核条目被选中

### US-7: 知识图谱提取/演化可用
As a 测试工程师, I want 图谱模块的"提取"和"演化"功能可用，so that 我能构建和演化知识图谱。

**验收**：
- Given knowledge_graph_enabled=True，When 我在图谱页面点击"提取"，Then 接口返回 200 并开始实体提取
- Given knowledge_graph_enabled=True，When 我在图谱页面点击"演化"，Then 接口返回 200 并开始图谱演化

### US-8: 蓝湖证据采集可用
As a 测试工程师, I want Wiki 知识库的"导入蓝湖"功能可用，so that 我能从蓝湖原型采集证据包。

**验收**：
- Given lanhu_evidence_enabled=True，When 我输入蓝湖地址点击"开始采集"，Then 接口返回 200 并创建采集任务
- Given lanhu_evidence_enabled=False，When 我调用 /api/v1/lanhu-evidence/jobs，Then 返回 503（不再出现——默认启用）

## 5. 技术考量

### 数据迁移（US-1）
- 现有数据中，`knowledge_domain` 可能为 NULL 或 'project'
- 需要编写迁移脚本：将 `source_type` 属于平台研发类（如 `batch_artifact`、`design_spec` 等）的数据 `knowledge_domain` 改为 'platform'
- `ProjectTab` 当前用 `para_category: 'project'` 过滤，需改为 `knowledge_domain: 'project'`
- `PlatformTab` 当前用 `knowledge_domain: 'platform'` 过滤，保持不变

### 功能门禁（US-5/7/8）
- `rag_enabled`、`knowledge_graph_enabled`、`lanhu_evidence_enabled` 默认 False 是安全保守策略
- 这些功能已完整实现并通过测试，用户需要可用 → 改为默认 True
- 这些门禁的 503 检查在 API 路由层和 Service 层双重存在，只改 config 即可

### 前端改动范围
- `SearchTab.tsx`：添加点击弹窗
- `ProjectTab.tsx`：修改过滤逻辑 + 弹窗尺寸
- `PlatformTab.tsx`：弹窗尺寸 + 验证按钮状态
- `SourceListTab.tsx`：验证按钮即时状态更新
- `ArtifactReviewTab.tsx`：批量审核 UI 已存在，确认全选/反选逻辑正确
- `GraphTab.tsx`：确认 503 错误处理（仅 config 变更后应自动可用）

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 开发 | Dev | 所有 8 个问题修复 + 手动自测 |
| QA | QA | 硬门禁全绿 + 8 个验收条件逐个验证 |
| 上线 | 全体 | 合入 main，知识中心全部功能可用 |
