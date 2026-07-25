# Batch 45 — PM Plan
> **PM (🟨)** | Date: 2026-07-26

## 规格摘要

**原始需求**: 处理 C-CONDITIONS.md 中 23 个 Open 条件里可执行的非 blocked 项，优先关闭 batch-18 遗留 P2/P3 项，其次 ThemeLab/CSS 对齐和 UX 走查。

**目标时间**: 本 batch (3-4 slices, 每 slice 30-60 min)

**排除**：
- Docker blocked: C43-1, C43-2, C44-C1, C44-C4
- Human reviewer: C31-2
- Physical device: CP-C1, CP-C2
- C22-C2/C3 (P1 Playground): 完整实现工作量过大，本 batch 仅做代码级可行性评估
- TPv2-B19-C2: npm install 成功后纳入

## 开发任务

### Slice 1: batch-18 遗留代码修复 (30 min)

#### [ ] Task 1.1: lanhu_mcp_enabled 导入开关 (batch-18-C11, P3)
**描述**: 蓝湖证据导入 API 在 `lanhu_mcp_enabled=False` 时返回 503
**验收标准**:
- `POST /api/v1/wiki/lanhu-evidence/import` 在 `LANHU_MCP_ENABLED=False` 时返回 503 + `{"detail": "蓝湖 MCP 未启用"}`
- 现有测试 `test_wiki_api.py` 继续通过
**涉及文件**: `backend/app/api/v1/wiki.py` — 添加 Depends guard
**参考**: PRD US-1, config.py:137 `lanhu_mcp_enabled`

#### [ ] Task 1.2: WikiDiffItem 补 left/right ref+scope (batch-18-C9, P2)
**描述**: WikiDiffItem 已有 left_value/right_value 但缺 left_ref/right_ref/left_scope/right_scope。补 4 个字段以支持独立差异上下文查询。
**验收标准**:
- WikiDiffItem 模型新增 4 个 Text 列
- Alembic 迁移脚本可正常 upgrade/downgrade
- Wiki diff API 响应 schema 包含新字段
**涉及文件**: `backend/app/models/wiki.py` (+4 columns), `backend/app/schemas/wiki.py` (schema update), Alembic 迁移, `backend/app/services/wiki/diff_classifier.py` (populate new fields)
**参考**: PRD US-2, wiki.py:122-143 WikiDiffItem

#### [ ] Task 1.3: WikiReviewItem 持久化表 (batch-18-C6, P2)
**描述**: 审查结果 (review_items, contradictions) 写入 wiki_review_item 表，替代纯 JSON 存储，支持审计追溯。
**验收标准**:
- 新建 `wiki_review_item` 表 (task_id, item_id, reviewer, decision, reason, created_at)
- 新建 `wiki_review_contradiction` 表 (task_id, item_a_id, item_b_id, description, resolution)
- Alembic 迁移可 upgrade/downgrade
- 审查 API 写入新表
**涉及文件**: `backend/app/models/wiki.py` (+2 models), Alembic 迁移, `backend/app/api/v1/wiki.py` (review endpoints), `backend/app/schemas/wiki.py`
**参考**: PRD US-3

### Slice 2: ThemeLab CSS 对齐 + Liquid Glass morph (25 min)

#### [ ] Task 2.1: theme-lab.css 深层组件 token 对齐 (C24-C1, P2)
**描述**: 审查 theme-lab.css 中 dropdown/dialog/tooltip 组件样式，将硬编码颜色替换为 CSS 变量引用。当前已大量使用 `var(--*)` token，但有部分主题特定色值可替换。
**验收标准**:
- 检查 theme-lab.css 全部 5 主题的组件样式段中的硬编码颜色
- 替换为语义 token 引用（如 `var(--muted)` 替代 `#96a4b2`）
- 无视觉破坏性变更
**涉及文件**: `frontend/src/theme-lab/theme-lab.css`
**参考**: PRD US-7

#### [ ] Task 2.2: MainLayout 集成 .lg-morph-bg (C24-C2, P2)
**描述**: 在 MainLayout 根容器或 header 添加 `.lg-morph-bg` class，当 liquid-glass 主题激活时触发 morphing 背景动画。当前 header 已有 `glass-card` class 但无 morphing 效果。
**验收标准**:
- `.lg-morph-bg` CSS class 定义在 theme-lab.css（渐变背景 + animation）
- MainLayout header 或 body wrapper 条件性应用该 class（仅在 liquid-glass 主题）
- 动画不干扰页面交互
**涉及文件**: `frontend/src/layouts/MainLayout.tsx`, `frontend/src/theme-lab/theme-lab.css`
**参考**: PRD US-8

### Slice 3: UX 走查 + 文档 (25 min)

#### [ ] Task 3.1: 固定高度布局验证 (C25v2-C2, P2)
**描述**: 检查用例管理页面（TestCase 相关页面）的固定高度布局在 desktop/tablet 分辨率下的表现。代码级审查 CSS 布局属性。
**验收标准**:
- 审查 TestCase 相关页面组件的 height/max-height/overflow 属性
- 确认使用 `calc()` 或 flex 自适应而非固定 px
- 记录发现的问题和建议
**涉及文件**: `frontend/src/pages/testcase/` 及子组件
**参考**: PRD US-9

#### [ ] Task 3.2: 知识中心弹窗 Design 走查 (C26KB-C1, P2)
**描述**: 审查知识中心弹窗组件的尺寸是否符合设计规范，确保长内容不被截断。
**验收标准**:
- 审查 Knowledge 相关 Dialog/Drawer 组件的 max-height, max-width 属性
- 确认内容区域有合适的 overflow 处理
- 记录发现
**涉及文件**: `frontend/src/pages/knowledge/` 及子组件
**参考**: PRD US-10

#### [ ] Task 3.3: 图谱两域数据隔离确认 (C26KB-C2, P2)
**描述**: 代码级确认图谱视图中蓝湖域和平台域的数据隔离机制。
**验收标准**:
- 审查 GraphTab/SphereTab 组件的数据获取和过滤逻辑
- 确认切换域时数据源正确切换、无交叉污染
- 记录结论
**涉及文件**: `frontend/src/pages/knowledge/` GraphTab/SphereTab 组件
**参考**: PRD US-11

#### [ ] Task 3.4: 迁移双向演练 SOP 文档 (batch-18-C7 + C21-P1-5, P1/P2)
**描述**: 为 `20260710_0017_wiki_tables.py` 迁移编写 staging 双向演练文档。
**验收标准**:
- 文档包含: 前置条件 → upgrade → 验证 → downgrade → 验证 → re-upgrade → 验证
- 列出验证 SQL 和预期结果
**涉及文件**: `docs/` 或 `work-logs/` 新文档
**参考**: PRD US-5

#### [ ] Task 3.5: 灰度放量 SOP 文档 (batch-18-C14, P3)
**描述**: 编写分环境灰度放量 SOP 文档。
**验收标准**:
- 文档包含 test→staging→prod 逐级放量流程
- 每级放量条件、回滚触发、观测指标
**涉及文件**: `docs/` 或 `work-logs/` 新文档
**参考**: PRD US-6

### Slice 4: 评估任务 (15 min)

#### [ ] Task 4.1: diff classifier baseline 评估脚本 (batch-18-C8, P2)
**描述**: 编写标注语料评估脚本，可计算 diff classifier 的召回率和误报率。
**验收标准**:
- 脚本接受标注语料 JSON 和 classifier 输出
- 输出 precision, recall, F1
- 提供 sample 标注语料格式
**涉及文件**: `backend/scripts/evaluate_diff_classifier.py` (新建)
**参考**: PRD US-4

#### [ ] Task 4.2: C22 Playground 可行性评估 (C22-C2/C3, P1)
**描述**: 代码级评估端到端编译链路的可行性。审查现有 Playwright 基础设施、测试用例模型、编排器服务，给出实现难度、预计工作量和风险。
**验收标准**:
- 审查 `playwright_executor.py` 现有能力
- 审查 TestCase 模型是否支持 script 生成
- 输出评估报告（可行性/风险/建议工作量）
**涉及文件**: `backend/app/services/playwright_executor.py`, `backend/app/models/test_case.py`, `backend/app/services/` 编排相关
**参考**: PRD §3 (非目标)

## 质量要求
- [x] 后端 test suite (757+) 保持通过
- [ ] Alembic 迁移可 upgrade/downgrade
- [ ] 无 console 报错/告警（前端静态审查）
- [ ] 所有新增/修改 API 端点有对应测试覆盖
