# Batch 37 — PM Plan

> **PM (🟨)** | Date: 2026-07-23

## 规格摘要

**原始需求**: 对测试平台 v2 进行全方位审查、修复和优化，涵盖：全面质量审查、Agent Team 逻辑审查、知识中心数据源修正与展示优化、功能验收与操作文档、平台初版资深视角验证、模块联动设计、隐藏未完成模块、全局字体放大

**目标时间**: 8 个切片分 3 轮推进

---

## 开发任务

### 🔍 Slice 1: 测试平台全面代码/功能/UI 审查

**描述**: 对 `test-platform-v2/` 进行三合一审查，产出审查报告
**验收标准**:
- 代码层：覆盖后端 `app/` 和前端 `src/`，检出重复代码、性能隐患、安全问题、异常处理缺陷
- 功能层：逐模块验证功能完整性，对照 CLAUDE.md 中的模块成熟度表
- UI 层：检查视觉一致性、响应式、交互体验
- 所有发现标注 P0–P3 级别和文件:行号锚点

**涉及文件**:
- `test-platform-v2/backend/app/` — 全量后端代码
- `test-platform-v2/frontend/src/` — 全量前端代码
- `test-platform-v2/CLAUDE.md` — 功能模块成熟度参考

**参考**: PRD §US-1

---

### 🔍 Slice 2: Agent Team 代码逻辑审查

**描述**: 审查 Agent Team 流水线的技能文件和脚本，定位反复出现的逻辑漏洞根因
**验收标准**:
- 逐文件审查 `DEPARTMENTS.md`、SKILL.md、各脚本文件
- 每个漏洞标注根因（为什么之前的修复没覆盖）
- 提出具体的修复建议

**涉及文件**:
- `.claude/skills/cameltv-agent-team/SKILL.md` — 流水线定义
- `.claude/skills/cameltv-agent-team/DEPARTMENTS.md` — 部门模板
- `scripts/git/start-agent-team-task.ps1` — 工作树创建
- `scripts/git/verify-ai-worktree.ps1` — 工作树验证
- `scripts/git/audit-ai-pr.ps1` — PR 审计
- `scripts/git/confirm-agent-team-completion.ps1` — 完成确认

**参考**: PRD §US-2

---

### 🔍 Slice 3: 知识中心功能验收 + 操作文档

**描述**: 使用用户提供的需求文档链接和生产地址，验收知识中心功能并编写使用文档
**验收标准**:
- 逐模块验收知识中心（项目知识/平台研发/检索/AI 审核台/图谱/实体/迭代/Wiki/Skills/项目球）
- 写出操作文档：每个模块的功能说明、使用场景、操作步骤、举例说明
- 举例基于真实 CamelTv 体育平台数据

**涉及文件**:
- `test-platform-v2/frontend/src/pages/knowledge/` — 知识中心前端
- `test-platform-v2/backend/app/services/knowledge/` — 知识中心后端服务
- 蓝湖用户端需求文档 — 功能验收参考
- 蓝湖运营后台需求文档 — 功能验收参考
- `https://www.camel1.tv/` — 生产环境参考

**参考**: PRD §US-4

---

### 🔍 Slice 4: 平台初版资深视角验证

**描述**: 以资深测试工程师 + 项目管理视角重度使用平台所有模块，判断初版符合度
**验收标准**:
- 涵盖：知识中心、需求文档、用例服务、接口测试、UI 自动化 + 其他模块
- 每个模块：功能完整性 × 需求符合度 × 缺失遗漏
- 产出功能符合度矩阵 + 缺失/遗漏清单 + 延伸开发建议

**涉及文件**:
- `test-platform-v2/` — 全平台
- `test-platform-v2/docs/CamelTv测试平台-完整PRD.md` — 原始 PRD 对照
- 蓝湖用户端需求文档 — 对照验证
- 蓝湖运营后台需求文档 — 对照验证

**参考**: PRD §US-5

---

### 💻 Slice 5: 知识中心数据源修正 + 弹窗尺寸优化

**描述**: 修复知识中心「项目知识」Tab 数据源筛选逻辑，放大详情弹窗
**验收标准**:
- 「项目知识」Tab 只展示 `para_category=project` 的知识源（排除 Agent Team 的 PRD/PM 工件）
- 弹窗从 `max-w-5xl` 增加到 `max-w-7xl`，内容区高度增大
- 切片内容在 1920×1080 分辨率下完整可见

**涉及文件**:
- `test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx` — 弹窗尺寸 + 数据筛选
- `test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx` — 平台研发弹窗（如有同样问题）
- `test-platform-v2/frontend/src/api/knowledge.ts` — API 调用参数检查
- `test-platform-v2/backend/app/api/v1/knowledge.py` — 后端筛选逻辑（如需要）

**参考**: PRD §US-3

---

### 💻 Slice 6: 隐藏未完成模块

**描述**: 将版本测试任务、缺陷管理、测试数据集、集成配置从导航菜单中隐藏
**验收标准**:
- 4 个模块不出现在侧边栏导航菜单
- 已完成模块（工作台/需求管理/用例服务/测试计划/运行中心/API测试/UI自动化/报告中心等）保持可见
- 不删除路由，仅从菜单中隐藏（URL 直接访问仍可用）

**涉及文件**:
- `test-platform-v2/backend/app/seed.py` — 菜单种子数据（可能需要标记 hidden）
- `test-platform-v2/backend/app/api/v1/menu.py` — 菜单 API（`fetchMenus`）
- `test-platform-v2/backend/app/models/menu.py` — 菜单模型（可能需要加 visible 字段）
- `test-platform-v2/frontend/src/layouts/MainLayout.tsx` — 前端菜单渲染

**参考**: PRD §US-7

---

### 💻 Slice 7: 全局字体放大

**描述**: 提升平台全局字体大小，改善可读性
**验收标准**:
- 正文基础字号从 14px 提升到 15px
- 侧边栏菜单项字号提升
- 标题 h1–h4 等比例放大
- 表格内容字号提升
- 不影响布局和响应式
- 用户主观确认可读性改善

**涉及文件**:
- `test-platform-v2/frontend/src/globals.css` — 全局字体基础配置
- `test-platform-v2/frontend/tailwind.config.cjs` — Tailwind 基础字号配置
- `test-platform-v2/frontend/src/components/ui/sidebar.tsx` — 侧边栏字号
- `test-platform-v2/frontend/src/ui-concepts/ui-concepts.css` — 概念展示 CSS
- `test-platform-v2/frontend/src/theme-lab/theme-lab.css` — 主题实验室 CSS

**参考**: PRD §US-8

---

### 📝 Slice 8: 模块联动架构设计

**描述**: 设计需求文档→AI用例生成→接口测试→UI自动化的全链路联动方案（本 Batch 只设计不编码）
**验收标准**:
- 产出联动架构设计文档
- 明确数据流、API 契约、状态管理方案
- 明确接口用例依赖 Swagger 文档上传的前提条件
- 明确 UI 自动化关联已上线功能的范围界定
- 给出后续实现 Slice 拆分建议

**涉及文件**: 本 Slice 只产出设计文档，不修改代码

**参考**: PRD §US-6

---

## 切片执行顺序

```
Round 1: 审查（无代码改动）
  Slice 1 (平台审查) ──┐
  Slice 2 (Agent Team) ─┤ 并行
  Slice 3 (知识验收)  ─┤
  Slice 4 (初版验证)  ─┘

Round 2: 修复（代码改动）
  Slice 5 (知识中心修复) ──┐
  Slice 6 (隐藏模块)     ──┤ 顺序
  Slice 7 (字体放大)     ──┘

Round 3: 设计
  Slice 8 (联动设计)
```

## 质量要求

- [x] 响应式（Desktop + Tablet）— 字体放大需验证
- [ ] OpenAPI 同步 — 菜单 API 变更需同步
- [ ] 单元测试覆盖 — 菜单隐藏逻辑需测试
- [ ] 无障碍（ARIA/键盘）— 弹窗放大后需验证焦点管理
- [ ] 无 console 报错/告警
