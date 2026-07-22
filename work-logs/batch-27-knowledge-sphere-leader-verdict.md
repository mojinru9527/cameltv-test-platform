# Batch 27 — Leader Verdict
> **Leader (🎯)** | Date: 2026-07-22 | Decision: APPROVED（设计通过，可进入实现阶段）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 产品方案 | 9/10 | PRD 4 个用户故事覆盖完整，非目标清晰，版本全景+项目球+Wiki基线+演化追踪四线并进 |
| 技术设计 | 8/10 | 数据模型最小侵入，3新表+2字段扩展。API 设计独立路由前缀。兼容性满分 |
| 可实现性 | 7/10 | 模块树自动提取是核心挑战，但 `lanhu_evidence_page` 表已有 folder/page_path/page_url 字段支撑 |
| 风险 | 中 | 自动提取准确率依赖 AI 质量，需人工审核兜底 |

## QA 阻塞项处理

| 阻塞 | 处理结果 |
|------|---------|
| B1: lanhu_evidence_page 层级信息不足 | **已解除**。表有 `folder`(文件夹名)、`page_path`(页面路径)、`page_url`(含 parentId) 三字段支撑层级提取 |

## 关键决策（已批准）

1. **「项目球」作为图谱新视图，不替代现有扁平图谱**：两个视图并存（Tab 切换），用户按需选择。扁平图谱适合技术视角（API/字段/缺陷），层级图谱适合业务视角（版本/模块/页面）。

2. **新增 3 表 + 2 字段扩展，零破坏性变更**：
   - `requirement_module`（模块树）
   - `release_bundle`（发布包）
   - `module_admin_link`（跨端关联）
   - `requirement_document.platform` + `requirement_document.doc_type`（扩展字段）

3. **entity_type/relation_type 字符串扩展，无需 DDL**：利用现有 `KnowledgeEntity.entity_type` 和 `KnowledgeRelation.relation_type` 的字符串类型特性，新增 7 种实体类型 + 7 种关系类型，零迁移成本。

4. **蓝湖→Wiki 同步采用"导入时自动触发 + 手动补充"的混合模式**：自动提取覆盖率预期 70%+，剩余由人工补充。

## 抽检通过

- ✅ [PRD §4](work-logs/batch-27-knowledge-sphere-prd-summary.md) — 4 个用户故事含 Given/When/Then 验收标准
- ✅ [PM §Task 1.1-1.3](work-logs/batch-27-knowledge-sphere-pm-plan.md) — 数据模型设计任务拆分到文件粒度
- ✅ [Design §1.1](work-logs/batch-27-knowledge-sphere-design-spec.md) — 版本全景视图 ASCII 布局清晰，三列平台卡片 + 运营后台关联
- ✅ [Dev §1](work-logs/batch-27-knowledge-sphere-dev-design.md) — 数据模型含完整 SQLAlchemy 定义 + entity_key 规范
- ✅ [Dev §3.1](work-logs/batch-27-knowledge-sphere-dev-design.md) — 项目球层级关系图含完整 ASCII 树
- ✅ [Dev §5](work-logs/batch-27-knowledge-sphere-dev-design.md) — 兼容性保证 + Feature Flag 设计

## 判决

**APPROVED** — 设计方案通过，可进入实现阶段。

实现时需优先处理的 P2 建议（来自 QA）：
- D1: entity_key 格式含版本号（避免同名模块跨版本冲突）
- D2: 权限码复用现有体系

## 下一批次 Leader 条件（C 编号）

实现阶段（Batch 28+）必须满足：
- **C1**: 模块树自动提取准确率 ≥70%（以人工抽检 20 个页面为样本）
- **C2**: 图谱层级视图在 200 节点下渲染时间 <3s
- **C3**: `release_bundle` 创建流程端到端可用（从蓝湖证据包导入→自动建模块树→手动关联运营后台→发布包生成）
- **C4**: Wiki 基线同步：导入后自动生成的 Wiki 页面数与蓝湖实际页面数之比 ≥70%

## 实现建议

1. **M1 优先（数据模型 + 版本全景）**：先建表 + API，让版本全景视图可手动创建和使用。自动提取放 M2。
2. **模块树提取分两阶段**：
   - Phase A: 规则引擎（利用 folder/page_path/order_index）→ 处理结构清晰的数据
   - Phase B: AI 辅助（DeepSeek 分析页面名称和 OCR 内容）→ 处理规则无法覆盖的边缘情况
3. **图谱层级视图用 vis-network hierarchical layout**，已在设计中验证可行
4. **Feature Flag 渐进启用**：`project_sphere_enabled` 默认 OFF → 内部验证 → 全量开启
